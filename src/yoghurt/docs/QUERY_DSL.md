# Query DSL

`yoghurt screener` and `yoghurt visualization` compile a SQL-flavored statement
into the JSON body that Yahoo's `/v1/finance/screener` and
`/v1/finance/visualization` endpoints expect. Both commands accept either
`--query SQL` (the DSL) or `--body-json JSON_OR_@FILE` (raw payload escape
hatch).

This document is the canonical reference for the DSL grammar and the JSON
shape it produces. The compiler lives in [src/yoghurt/query.py](src/yoghurt/query.py);
the grammar here mirrors what that parser accepts.

## Routes

| Command | Endpoint | Use it for | Response shape |
| --- | --- | --- | --- |
| `screener` | `/v1/finance/screener` | Filter a single Yahoo asset class (`EQUITY`, `ETF`, `MUTUALFUND`, `INDEX`, `BOND`, `CURRENCY`, `COMMODITY`, `FUTURE`, `OPTION`, `WARRANT`, `CRYPTOCURRENCY`). | `finance.result[0].records[]` with **camelCase** keys (`marketCap`, `peRatioLtm`, `fiftyTwoWeekHigh`). |
| `visualization` | `/v1/finance/visualization` | Query data-platform entities (`sp_earnings`, `economic_event`, `splits`, `ipo_info`, `insider_transaction`, `research_reports`, `trade_idea`). Cross-entity queries and aggregations live here. | `finance.result[0].documents[].columns/rows` with **snake_case** or dotted keys (`intradaymarketcap`, `peratio.lasttwelvemonths`, `fiftytwowkhigh`). |

Both routes accept either naming form on **input**. Output reflects the route's
native convention. Yoghurt prints both bodies verbatim.

The typed screener requests unformatted values. The CLI defaults to
unformatted values too; `--formatted` requests Yahoo display wrappers. Pass `--no-records-response` to ask Yahoo for its raw documents
shape instead of records.

## Grammar

```
stmt        := select_stmt | aggregate_stmt

select_stmt := SELECT ('*' | field (',' field)*)
               FROM entity (',' entity)*
               [WHERE expr]
               [ORDER BY field [ASC | DESC]]
               [LIMIT n [OFFSET m]]

aggregate_stmt := AGGREGATE date_hist '(' field ',' string ')'
                  FROM entity (',' entity)*
                  [WHERE expr]
                  [JOIN BY field]
                  [FILL ident]
                  [LIMIT n [OFFSET m]]

expr        := or_expr
or_expr     := and_expr (OR and_expr)*
and_expr    := not_expr (AND not_expr)*
not_expr    := NOT not_expr | predicate | '(' expr ')'

predicate   := field op value
op          := '=' | '==' | '!=' | '>' | '>=' | '<' | '<='
             | IN | NOT IN | BETWEEN

value       := literal
             | '(' literal (',' literal)* ')'    # IN / NOT IN list
             | literal AND literal               # BETWEEN low AND high

literal     := number | 'single-quoted-string' | bareword
```

Keywords are matched case-insensitively (`SELECT`, `select`, `Select` all
parse). Entity names and field names are **case-preserved** when emitted to
Yahoo.

### Statements

| Form | Compiles to |
| --- | --- |
| `SELECT col1, col2 FROM ...` | `includeFields: ["col1", "col2"]` |
| `SELECT * FROM ...` | `includeFields` omitted; Yahoo returns its default columns. |
| `AGGREGATE date_hist(field, '1d') FROM ...` | `aggregation: {operator: "date_hist", operands: [...]}` |

`date_hist` is currently the only supported aggregation function. Anything
else raises `QueryError`.

### Entity routing (FROM)

The compiler picks between `quoteType` and `entityIdType` automatically:

| FROM clause | Body field |
| --- | --- |
| Single bareword, **all uppercase**, **no underscore** (e.g. `EQUITY`, `ETF`, `MUTUALFUND`, `INDEX`, `BOND`, `CURRENCY`, `COMMODITY`, `FUTURE`, `OPTION`, `WARRANT`, `CRYPTOCURRENCY`) | `quoteType: "EQUITY"` |
| Anything else — lowercase, mixed case, underscores, or multiple entities (e.g. `sp_earnings`, `INSIDER_TRANSACTION`, `economic_event, splits, ipo_info`) | `entityIdType: "sp_earnings"` (string) or `["sp_earnings", "splits"]` (list) |

Multi-entity queries are typically used with `AGGREGATE ... JOIN BY` to merge
timelines across calendar entities.

### ORDER BY

Single field only. Yahoo's `sortField`/`sortType` are scalars; multi-field
sorts raise `QueryError`. ORDER BY is **not allowed** with `AGGREGATE`.

| SQL | Body |
| --- | --- |
| `ORDER BY ticker` | `sortField: "ticker"` (no `sortType`; server default) |
| `ORDER BY ticker ASC` | `sortField: "ticker"`, `sortType: "ASC"` |
| `ORDER BY ticker DESC` | `sortField: "ticker"`, `sortType: "DESC"` |

### LIMIT and OFFSET

`LIMIT n` → `size: n`. `LIMIT n OFFSET m` → `size: n, offset: m`.

### JOIN BY and FILL

AGGREGATE-only. `JOIN BY field` aligns multi-entity timelines on a shared
column. `FILL pad` (or any bareword) sets `fillNA` for missing values.

```
JOIN BY startdatetime FILL pad
```

becomes

```json
{ "joinField": "startdatetime", "fillNA": "pad" }
```

Both clauses raise `QueryError` if used with a `SELECT` statement.

## Predicates and operators

| SQL | JSON operator | Operands |
| --- | --- | --- |
| `field = value` / `field == value` | `eq` | `[field, value]` |
| `field != value` | `must_not` wrapping `eq` | `[{operator: "eq", ...}]` |
| `field > value` | `gt` | `[field, value]` |
| `field >= value` | `gte` | `[field, value]` |
| `field < value` | `lt` | `[field, value]` |
| `field <= value` | `lte` | `[field, value]` |
| `field BETWEEN low AND high` | `btwn` | `[field, low, high]` |
| `field IN (a, b, c)` | `or` of `eq` | `[{eq:[f,a]}, {eq:[f,b]}, {eq:[f,c]}]` |
| `field NOT IN (a, b)` | `must_not` wrapping `or` | nested as above |
| `NOT expr` | `must_not` | `[expr]` |
| `expr AND expr` | `and` (flattened) | siblings appended |
| `expr OR expr` | `or` (flattened) | siblings appended |
| `(expr)` | grouping; tree structure preserved | — |

Adjacent `AND`/`AND` and `OR`/`OR` nodes flatten into a single operand list.
Parentheses force grouping when you need an OR inside an AND tree.

## Literals

| Form | Examples | Notes |
| --- | --- | --- |
| Integer | `25`, `-7` | Sign attaches to leading minus. |
| Float | `1.5`, `-0.25` | Decimal point. |
| Scientific | `10e9`, `1.5E-3` | Lowercase or uppercase `e`. |
| String | `'us'`, `'2026-05-09'` | **Single quotes only.** Double quotes are not accepted. |
| Bareword | `pad`, `us` | Treated as an IDENT literal — works but quoted strings are canonical for values. |

Dates pass through as strings — quote them.

## Fields

Field identifiers accept dots, so Yahoo's namespaced names round-trip
unchanged:

```
peratio.lasttwelvemonths
trailingPeRatio
intradaymarketcap
```

Discover available fields, types, and quick-pick operators for an entity
with [`yoghurt screener-instrument-fields <entity>`](src/yoghurt/commands.py).

## Body output

Every parsed statement produces a dict with:

| Key | Always present? | Meaning |
| --- | --- | --- |
| `query` | yes | `{operator, operands}` tree. Empty `WHERE` yields `{operator: "and", operands: []}` (match-all). |
| `topOperator` | yes | Always `"AND"`. |
| `includeFields` | only if not `SELECT *` | Ordered list of selected fields. |
| `sortField`, `sortType` | only if `ORDER BY` | Scalar sort. |
| `size`, `offset` | only if `LIMIT` / `OFFSET` | Paging. |
| `quoteType` **or** `entityIdType` | yes | Mutually exclusive — chosen by the FROM routing rule above. |
| `aggregation`, `joinField`, `fillNA` | AGGREGATE only | Wire format for `date_hist`, join field, fill mode. |

`--body-json` skips the compiler entirely. The payload is parsed as JSON
(inline string or `@path/to/file.json`), required to be a JSON object, and
sent verbatim.

## Premium-locked entities

Four data-platform entities return `401` on direct query:

- `analyst_ratings`
- `tradingcentral_event_info`
- `institutional_interest`
- `institutional_holdings`

Their **schemas** are still readable through `screener-instrument-fields`,
and Yahoo's curated saved screens surface narrow slices of each on the free
tier. See [`yoghurt screener-predefined --help`](src/yoghurt/commands.py) for
the preset IDs that expose analyst ratings, institutional flow, and Trading
Central signals.

Asset-class catalogs also mark individual fields with `isPremium=true`.
Filtering on those fields returns `401`.

## Examples

### Earnings calendar (visualization)

```powershell
uv run yoghurt visualization --query "
  SELECT ticker, companyshortname, startdatetime,
         epsestimate, epsactual, epssurprisepct, intradaymarketcap
  FROM sp_earnings
  WHERE region = 'us'
    AND startdatetime BETWEEN '2026-05-09' AND '2026-05-16'
    AND eventtype IN ('EAD', 'ERA')
    AND exchange NOT IN ('PNK','OQB','OQX','OEM','OGM','XXX')
  ORDER BY intradaymarketcap DESC
  LIMIT 25"
```

### Insider transactions for one ticker

```powershell
uv run yoghurt visualization --query "
  SELECT ticker, transactiondate, shares
  FROM INSIDER_TRANSACTION
  WHERE ticker = 'AAPL'
  ORDER BY transactiondate DESC
  LIMIT 50"
```

### Custom equity screen (screener)

```powershell
uv run yoghurt screener --query "
  SELECT ticker, intradaymarketcap, sector, peratio.lasttwelvemonths
  FROM EQUITY
  WHERE region = 'us'
    AND sector = 'Technology'
    AND intradaymarketcap >= 10e9
    AND peratio.lasttwelvemonths < 30
  ORDER BY intradaymarketcap DESC
  LIMIT 100"
```

### Cross-entity calendar histogram (AGGREGATE)

```powershell
uv run yoghurt visualization --query "
  AGGREGATE date_hist(startdatetime, '1d')
  FROM sp_earnings, economic_event, splits, ipo_info
  WHERE startdatetime BETWEEN '2026-05-03' AND '2026-05-09'
  JOIN BY startdatetime
  FILL pad"
```

### Grouped OR inside an AND tree

```powershell
uv run yoghurt visualization --query "
  SELECT ticker
  FROM sp_earnings
  WHERE region = 'us'
    AND (eventtype = 'EAD' OR eventtype = 'ERA')"
```

### Default columns (SELECT *)

```powershell
uv run yoghurt visualization --query "
  SELECT * FROM sp_earnings WHERE region = 'us'"
```

`includeFields` is omitted; Yahoo returns its server-side default column
set.

### Raw JSON body escape hatch

```powershell
uv run yoghurt visualization --body-json @body.json
uv run yoghurt screener --body-json '{"quoteType":"EQUITY","query":{"operator":"and","operands":[]},"includeFields":["symbol"],"size":1,"topOperator":"AND"}'
```

## Discovery workflow

```powershell
# 1. List confirmed entity names (asset classes + event entities).
uv run yoghurt screener-instrument-fields --help

# 2. Inspect fields, types, and quick-pick filter chips for one entity.
uv run yoghurt screener-instrument-fields equity
uv run yoghurt screener-instrument-fields insider_transaction | jq '.finance.result[0].fields | keys[]'

# 3. Build a query against those field names.
uv run yoghurt screener --query "SELECT ticker, marketCap FROM EQUITY WHERE ..."
```

The schema response enumerates each field's `displayName`, `type` (`STRING`,
`NUMBER`, `DATE`, `BOOLEAN`), `category`, `sortable`, `isPremium`,
`deprecated`, and a `labels[]` array of UI quick-pick chips. The chip
`operator` and `operand` values map directly onto the predicates above.

## Errors

The compiler raises `QueryError` (subclass of `ValueError`) for any of:

- Missing `FROM` clause.
- Unsupported aggregation function (anything other than `date_hist`).
- `ORDER BY` with `AGGREGATE`.
- Multi-field `ORDER BY`.
- `JOIN BY` or `FILL` outside `AGGREGATE`.
- Unterminated single-quoted string.
- Unexpected operator, identifier, or trailing token.

Yoghurt surfaces the message as `--query parse error: ...` on stderr and exits
non-zero.

## Known quirks

- **`sp_earnings`** returns a Yahoo `500` from
  `/screener/instrument/sp_earnings/fields`. Use the default column set
  observed on Yahoo's calendar page (`ticker, companyshortname,
  startdatetime, epsestimate, epsactual, epssurprisepct, intradaymarketcap`)
  until the schema endpoint cooperates.
- **`privatecompany`** returns an empty `fields` map; the data is paywalled.
- **`TOP_OPTIONS_IMPLIED_VOLATALITY`** — yes, that's a Yahoo typo. The screener
  preset ID is intentional; do not "fix" it.
- **Empty `WHERE`** produces `query: {operator: "and", operands: []}`, which
  Yahoo reads as match-all.
- **Bareword literals** parse, so `WHERE region = us` works — but `'us'` is
  canonical. Single-quoted strings remove ambiguity with field identifiers.
