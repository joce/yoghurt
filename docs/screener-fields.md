# Screener field name translation

Yahoo's `screener` route accepts a different vocabulary in `SELECT` than it
returns in records. The DSL field names (lowercase, dotted) get translated
to camelCase response keys, often with `Ltm`, `Percent`, or `Yr` suffixes
appended. The `visualization` route does **not** do this; its
`documents[0].columns[].id` list preserves whatever you wrote.

When you write Parquet output from a screener query, the Parquet columns
reflect the **response keys**, not the SELECT clause. This table documents
the mappings discovered by live probing so you can predict the column
names you will get.

The list is not exhaustive — Yahoo accepts a wide and partly undocumented
field vocabulary in `SELECT`. Many filter fields valid in `WHERE` / `ORDER
BY` return HTTP 400 when used in `SELECT`. If a field is not on this list,
run the query once with `--format json` and inspect
`finance.result[0].records[0]` to learn its actual response key.

## Verified mappings

| DSL name (in SELECT)                                  | Response key                       |
|-------------------------------------------------------|------------------------------------|
| `intradaymarketcap`                                   | `marketCap`                        |
| `percentchange`                                       | `regularMarketChangePercent`       |
| `dayvolume`                                           | `regularMarketVolume`              |
| `avgdailyvol3m`                                       | `avgDailyVol3m`                    |
| `eodprice`                                            | `eodPrice`                         |
| `eodvolume`                                           | `eodVolume`                        |
| `intradayprice`                                       | `regularMarketPrice`               |
| `intradaypricechange`                                 | `regularMarketChange`              |
| `fiftytwowkpercentchange`                             | `fiftyTwoWeekChangePercent`        |
| `fiftytwowkhigh`                                      | `fiftyTwoWeekHigh`                 |
| `fiftytwowklow`                                       | `fiftyTwoWeekLow`                  |
| `peratio.lasttwelvemonths`                            | `peRatioLtm`                       |
| `pegratio_5y`                                         | `pegRatio5Yr`                      |
| `quarterlyrevenuegrowth.quarterly`                    | `revenueGrowthPercentYoYQuarterly` |
| `epsgrowth.lasttwelvemonths`                          | `epsGrowthPercentLtm`              |
| `totaldebtequity.lasttwelvemonths`                    | `totalDebtEquityPercentLtm`        |
| `returnonequity.lasttwelvemonths`                     | `returnOnEquityPercentLtm`         |
| `returnonassets.lasttwelvemonths`                     | `returnOnAssetsPercentLtm`         |
| `dividendyield`                                       | `dividendYieldPercent`             |
| `forward_dividend_yield`                              | `forwardDividendYieldPercent`      |
| `totaldebt.lasttwelvemonths`                          | `totalDebtLtm`                     |
| `totalassets.lasttwelvemonths`                        | `totalAssetsLtm`                   |
| `operatingincome.lasttwelvemonths`                    | `operatingIncomeLtm`               |
| `ebitda.lasttwelvemonths`                             | `ebitdaLtm`                        |
| `ebit.lasttwelvemonths`                               | `ebitLtm`                          |
| `ebitdamargin.lasttwelvemonths`                       | `ebitdaMarginPercentLtm`           |
| `capitalexpenditure.lasttwelvemonths`                 | `capitalExpenditureLtm`            |
| `currentratio.lasttwelvemonths`                       | `currentRatioLtm`                  |
| `quickratio.lasttwelvemonths`                         | `quickRatioLtm`                    |
| `totalequity.lasttwelvemonths`                        | `totalEquityLtm`                   |
| `totalcommonsharesoutstanding.lasttwelvemonths`       | `totalCommonSharesOutstandingLtm`  |
| `lastclosemarketcap.lasttwelvemonths`                 | `lastCloseMarketCapLtm`            |
| `lastclosetevebitda.lasttwelvemonths`                 | `lastCloseTevEbitdaLtm`            |
| `lastclosetevebit.lasttwelvemonths`                   | `lastCloseTevEbitLtm`              |
| `lastclosepriceearnings.lasttwelvemonths`             | `lastClosePriceEarningsRatioLtm`   |
| `esg_score`                                           | `esgScore`                         |

## Exact pass-through (no translation)

These fields appear in records under the same name you used in `SELECT`:

`sector`, `industry`, `region`, `exchange`, `beta`

## Always-included response fields

Records may include fields you did **not** ask for. Most common:

- `ticker` — included whether or not you SELECT it.
- `logoUrl` — included on records for which Yahoo has a brand image.

These show up as Parquet columns. If you do not want them, post-process
the Parquet file with polars / pandas to drop them.

## Edge cases

- `cashandequivalents.lasttwelvemonths` is accepted in `SELECT` but Yahoo
  returns no corresponding response field. The Parquet file will not have
  a column for it.
- Most camelCase response keys (e.g. `marketCap`, `trailingPE`,
  `peRatioLtm`) return HTTP 400 when used directly in `SELECT`. You must
  use the lowercase DSL form.

## How to discover more mappings

```powershell
# Print the response keys for a single record
uv run yoghurt screener --query "SELECT ticker, <your_field> FROM EQUITY WHERE region = 'us' LIMIT 1" | jq '.finance.result[0].records[0] | keys'
```

If `<your_field>` is valid, the result includes a key that is its
translated name. If `<your_field>` causes a 400, it is not valid in
`SELECT` — try filter-style variations or check Yahoo's screener UI for
the canonical name.
