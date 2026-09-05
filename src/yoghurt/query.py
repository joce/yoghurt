"""SQL-flavored query language for the visualization and screener routes.

Compiles a subset of SQL into the JSON body that Yahoo's
``/v1/finance/visualization`` and ``/v1/finance/screener`` endpoints expect.
The grammar covers the operators observed in real Yahoo client traffic plus
the aggregation extensions used by the calendar landing page.

Grammar sketch::

    stmt        := select_stmt | aggregate_stmt
    select_stmt := 'SELECT' ('*' | field (',' field)*)
                   'FROM' entity (',' entity)*
                   ['WHERE' expr]
                   ['ORDER BY' field [ASC|DESC]]
                   ['LIMIT' n ['OFFSET' m]]
    aggregate_stmt := 'AGGREGATE' agg_call
                      'FROM' entity (',' entity)*
                      ['WHERE' expr]
                      ['JOIN BY' field]
                      ['FILL' ident]
                      ['LIMIT' n ['OFFSET' m]]
    agg_call    := 'date_hist' '(' field ',' string ')'
    expr        := or_expr
    or_expr     := and_expr ('OR' and_expr)*
    and_expr    := not_expr ('AND' not_expr)*
    not_expr    := 'NOT' not_expr | predicate | '(' expr ')'
    predicate   := field op value
    op          := '=' | '!=' | '>' | '>=' | '<' | '<=' | 'IN' | 'NOT IN' | 'BETWEEN'
    value       := literal
                 | '(' literal (',' literal)* ')'        # for IN / NOT IN
                 | literal 'AND' literal                  # for BETWEEN
    literal     := number | 'single-quoted-string'

Field identifiers may contain dots (e.g. ``peratio.lasttwelvemonths``).
Entity identifiers are barewords (case-preserved): ``EQUITY``, ``ETF``,
``sp_earnings``, ``INSIDER_TRANSACTION``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Final

_LiteralValue = int | float | str


class QueryError(ValueError):
    """Raised when a query string cannot be parsed."""


class _StmtKind(str, Enum):
    SELECT = "select"
    AGGREGATE = "aggregate"


@dataclass(frozen=True, slots=True)
class Expr:
    """Boolean predicate / aggregation tree node."""

    operator: str
    operands: tuple[Any, ...]

    def to_dict(self) -> dict[str, Any]:
        """Render this expression as the dict shape Yahoo expects.

        Returns:
            dict[str, Any]: ``{operator, operands}`` mirroring Yahoo's wire format.
        """

        rendered_operands: list[Any] = []
        for operand in self.operands:
            if isinstance(operand, Expr):
                rendered_operands.append(operand.to_dict())
            else:
                rendered_operands.append(operand)
        return {"operator": self.operator, "operands": rendered_operands}


@dataclass(frozen=True, slots=True)
class Statement:
    """Parsed query ready to be emitted as a Yahoo POST body."""

    kind: _StmtKind
    entities: tuple[str, ...]
    fields: tuple[str, ...] | None  # ``None`` represents ``SELECT *``.
    where: Expr | None
    sort_field: str | None
    sort_desc: bool | None
    limit: int | None
    offset: int | None
    aggregation: Expr | None
    join_field: str | None
    fill_na: str | None

    def to_body(self) -> dict[str, Any]:
        """Render this statement as the JSON body Yahoo's POST endpoints accept.

        Returns:
            dict[str, Any]: Body for Yahoo's ``/visualization`` or ``/screener``.
        """

        body: dict[str, Any] = {
            "query": self._build_query_block(),
            "topOperator": "AND",
        }
        if self.fields is not None:
            body["includeFields"] = list(self.fields)
        if self.sort_field is not None:
            body["sortField"] = self.sort_field
        if self.sort_desc is not None:
            body["sortType"] = "DESC" if self.sort_desc else "ASC"
        if self.limit is not None:
            body["size"] = self.limit
        if self.offset is not None:
            body["offset"] = self.offset
        self._apply_entity_selector(body)
        if self.aggregation is not None:
            body["aggregation"] = self.aggregation.to_dict()
        if self.join_field is not None:
            body["joinField"] = self.join_field
        if self.fill_na is not None:
            body["fillNA"] = self.fill_na
        return body

    def _build_query_block(self) -> dict[str, Any]:
        if self.where is None:
            return {"operator": "and", "operands": []}
        return self.where.to_dict()

    def _apply_entity_selector(self, body: dict[str, Any]) -> None:
        if self._uses_quote_type():
            body["quoteType"] = self.entities[0]
            return
        if len(self.entities) == 1:
            body["entityIdType"] = self.entities[0]
        else:
            body["entityIdType"] = list(self.entities)

    def _uses_quote_type(self) -> bool:
        if len(self.entities) != 1:
            return False
        only = self.entities[0]
        return only.isupper() and "_" not in only


_KEYWORDS: Final[frozenset[str]] = frozenset(
    {
        "SELECT",
        "FROM",
        "WHERE",
        "AND",
        "OR",
        "NOT",
        "IN",
        "BETWEEN",
        "ORDER",
        "BY",
        "ASC",
        "DESC",
        "LIMIT",
        "OFFSET",
        "AGGREGATE",
        "JOIN",
        "FILL",
    }
)
_PUNCTUATION_CHARS: Final[frozenset[str]] = frozenset({"(", ")", ","})
_OP_FOLLOWERS: Final[frozenset[str]] = frozenset({">=", "<=", "!=", "=="})
_SINGLE_OP_CHARS: Final[frozenset[str]] = frozenset({"<", ">", "="})


@dataclass(frozen=True, slots=True)
class _Token:
    kind: str
    value: str
    position: int


def _tokenize(text: str) -> list[_Token]:
    tokens: list[_Token] = []
    i = 0
    length = len(text)
    while i < length:
        char = text[i]
        if char.isspace():
            i += 1
            continue
        if char in _PUNCTUATION_CHARS:
            tokens.append(_Token(char, char, i))
            i += 1
            continue
        if char == "*":
            tokens.append(_Token("STAR", "*", i))
            i += 1
            continue
        if char == "'":
            token, advanced = _scan_string(text, i)
            tokens.append(token)
            i = advanced
            continue
        if char in "<>!=":
            token, advanced = _scan_operator(text, i)
            tokens.append(token)
            i = advanced
            continue
        if char.isdigit() or (char == "-" and i + 1 < length and text[i + 1].isdigit()):
            number, advanced = _scan_number(text, i)
            tokens.append(_Token("NUMBER", number, i))
            i = advanced
            continue
        if char.isalpha() or char == "_":
            ident, advanced = _scan_identifier(text, i)
            tokens.append(_classify_identifier(ident, i))
            i = advanced
            continue
        message = f"Unexpected character {char!r} at position {i}"
        raise QueryError(message)
    tokens.append(_Token("EOF", "", length))
    return tokens


def _scan_string(text: str, start: int) -> tuple[_Token, int]:
    end = text.find("'", start + 1)
    if end == -1:
        message = f"Unterminated string literal at position {start}"
        raise QueryError(message)
    return _Token("STRING", text[start + 1 : end], start), end + 1


def _scan_operator(text: str, start: int) -> tuple[_Token, int]:
    two = text[start : start + 2]
    if two in _OP_FOLLOWERS:
        return _Token("OP", two, start), start + 2
    char = text[start]
    if char in _SINGLE_OP_CHARS:
        return _Token("OP", char, start), start + 1
    message = f"Unexpected character {char!r} at position {start}"
    raise QueryError(message)


def _scan_number(text: str, start: int) -> tuple[str, int]:
    length = len(text)
    i = start
    if text[i] == "-":
        i += 1
    while i < length and text[i].isdigit():
        i += 1
    if i < length and text[i] == ".":
        i += 1
        while i < length and text[i].isdigit():
            i += 1
    if i < length and text[i] in {"e", "E"}:
        i += 1
        if i < length and text[i] in {"+", "-"}:
            i += 1
        while i < length and text[i].isdigit():
            i += 1
    return text[start:i], i


def _scan_identifier(text: str, start: int) -> tuple[str, int]:
    length = len(text)
    i = start
    while i < length:
        char = text[i]
        if char.isalnum() or char in {"_", "."}:
            i += 1
            continue
        break
    return text[start:i], i


def _classify_identifier(ident: str, position: int) -> _Token:
    upper = ident.upper()
    if upper in _KEYWORDS:
        return _Token(upper, upper, position)
    return _Token("IDENT", ident, position)


def _coerce_number(value: str, position: int) -> int | float:
    try:
        return int(value)
    except ValueError:
        try:
            number = float(value)
        except ValueError:
            message = f"Invalid number at position {position}"
            raise QueryError(message) from None
        if not math.isfinite(number):
            message = f"Number must be finite at position {position}"
            raise QueryError(message) from None
        return number


@dataclass(slots=True)
class _Cursor:
    tokens: list[_Token]
    index: int = 0

    def peek(self, offset: int = 0) -> _Token:
        return self.tokens[self.index + offset]

    def consume(self, kind: str | None = None, value: str | None = None) -> _Token:
        token = self.peek()
        if kind is not None and token.kind != kind:
            message = (
                f"Expected {kind} at position {token.position}, "
                f"got {token.kind} ({token.value!r})"
            )
            raise QueryError(message)
        if value is not None and token.value.upper() != value.upper():
            message = (
                f"Expected {value!r} at position {token.position}, got {token.value!r}"
            )
            raise QueryError(message)
        self.index += 1
        return token

    def match(self, *kinds: str) -> _Token | None:
        token = self.peek()
        if token.kind in kinds:
            self.index += 1
            return token
        return None


def _new_string_list() -> list[str]:
    return []


@dataclass(slots=True)
class _StatementBuilder:
    kind: _StmtKind
    entities: list[str] = field(default_factory=_new_string_list)
    fields: list[str] | None = None
    where: Expr | None = None
    sort_field: str | None = None
    sort_desc: bool | None = None
    limit: int | None = None
    offset: int | None = None
    aggregation: Expr | None = None
    join_field: str | None = None
    fill_na: str | None = None

    def build(self) -> Statement:
        if not self.entities:
            message = "Statement is missing FROM clause"
            raise QueryError(message)
        return Statement(
            kind=self.kind,
            entities=tuple(self.entities),
            fields=tuple(self.fields) if self.fields is not None else None,
            where=self.where,
            sort_field=self.sort_field,
            sort_desc=self.sort_desc,
            limit=self.limit,
            offset=self.offset,
            aggregation=self.aggregation,
            join_field=self.join_field,
            fill_na=self.fill_na,
        )


def parse(text: str) -> Statement:
    """Parse a query string into a :class:`Statement`.

    Args:
        text: SQL-flavored query body.

    Returns:
        Statement: Parsed query ready to be emitted with ``to_body``.

    Raises:
        QueryError: If the query is malformed or uses unsupported syntax.
    """

    cursor = _Cursor(_tokenize(text))
    builder = _start_statement(cursor)
    cursor.consume("FROM")
    _parse_entities(cursor, builder)
    _parse_optional_where(cursor, builder)
    _parse_optional_order_by(cursor, builder)
    _parse_optional_join(cursor, builder)
    _parse_optional_fill(cursor, builder)
    _parse_optional_limit(cursor, builder)
    final = cursor.peek()
    if final.kind != "EOF":
        message = (
            f"Unexpected trailing token {final.value!r} at position {final.position}"
        )
        raise QueryError(message)
    return builder.build()


def _start_statement(cursor: _Cursor) -> _StatementBuilder:
    head = cursor.peek()
    if head.kind == "SELECT":
        builder = _StatementBuilder(kind=_StmtKind.SELECT)
        cursor.consume("SELECT")
        _parse_select_fields(cursor, builder)
        return builder
    if head.kind == "AGGREGATE":
        builder = _StatementBuilder(kind=_StmtKind.AGGREGATE)
        cursor.consume("AGGREGATE")
        builder.aggregation = _parse_aggregation(cursor)
        return builder
    message = (
        f"Expected SELECT or AGGREGATE at position {head.position}, got {head.value!r}"
    )
    raise QueryError(message)


def _parse_optional_where(cursor: _Cursor, builder: _StatementBuilder) -> None:
    if cursor.peek().kind != "WHERE":
        return
    cursor.consume("WHERE")
    builder.where = _parse_or(cursor)


def _parse_optional_order_by(cursor: _Cursor, builder: _StatementBuilder) -> None:
    if cursor.peek().kind != "ORDER":
        return
    if builder.kind is _StmtKind.AGGREGATE:
        message = "ORDER BY is not supported with AGGREGATE"
        raise QueryError(message)
    cursor.consume("ORDER")
    cursor.consume("BY")
    _parse_order_by(cursor, builder)


def _parse_optional_join(cursor: _Cursor, builder: _StatementBuilder) -> None:
    if cursor.peek().kind != "JOIN":
        return
    if builder.kind is not _StmtKind.AGGREGATE:
        message = "JOIN BY is only valid for AGGREGATE statements"
        raise QueryError(message)
    cursor.consume("JOIN")
    cursor.consume("BY")
    builder.join_field = cursor.consume("IDENT").value


def _parse_optional_fill(cursor: _Cursor, builder: _StatementBuilder) -> None:
    if cursor.peek().kind != "FILL":
        return
    if builder.kind is not _StmtKind.AGGREGATE:
        message = "FILL is only valid for AGGREGATE statements"
        raise QueryError(message)
    cursor.consume("FILL")
    builder.fill_na = cursor.consume("IDENT").value


def _parse_optional_limit(cursor: _Cursor, builder: _StatementBuilder) -> None:
    if cursor.peek().kind != "LIMIT":
        return
    cursor.consume("LIMIT")
    builder.limit = _pagination_number(cursor, minimum=1)
    if cursor.peek().kind == "OFFSET":
        cursor.consume("OFFSET")
        builder.offset = _pagination_number(cursor, minimum=0)


def _pagination_number(cursor: _Cursor, *, minimum: int) -> int:
    token = cursor.consume("NUMBER")
    value = _coerce_number(token.value, token.position)
    if not isinstance(value, int) or value < minimum:
        message = f"Expected integer >= {minimum} at position {token.position}"
        raise QueryError(message)
    return value


def _parse_select_fields(cursor: _Cursor, builder: _StatementBuilder) -> None:
    if cursor.match("STAR") is not None:
        builder.fields = None
        return
    fields: list[str] = [cursor.consume("IDENT").value]
    while cursor.match(",") is not None:
        fields.append(cursor.consume("IDENT").value)
    builder.fields = fields


def _parse_aggregation(cursor: _Cursor) -> Expr:
    name = cursor.consume("IDENT").value
    if name != "date_hist":
        message = f"Unsupported aggregation function: {name!r}"
        raise QueryError(message)
    cursor.consume("(")
    field_token = cursor.consume("IDENT")
    cursor.consume(",")
    interval_token = cursor.consume("STRING")
    cursor.consume(")")
    return Expr(
        "date_hist",
        (
            Expr("eq", ("field", field_token.value)),
            Expr("eq", ("interval", interval_token.value)),
        ),
    )


def _parse_entities(cursor: _Cursor, builder: _StatementBuilder) -> None:
    builder.entities.append(cursor.consume("IDENT").value)
    while cursor.match(",") is not None:
        builder.entities.append(cursor.consume("IDENT").value)


def _parse_order_by(cursor: _Cursor, builder: _StatementBuilder) -> None:
    builder.sort_field = cursor.consume("IDENT").value
    if cursor.match(",") is not None:
        message = (
            "Yahoo's sortField/sortType are scalars; "
            "ORDER BY supports only a single field."
        )
        raise QueryError(message)
    direction = cursor.peek()
    if direction.kind == "ASC":
        cursor.consume("ASC")
        builder.sort_desc = False
    elif direction.kind == "DESC":
        cursor.consume("DESC")
        builder.sort_desc = True


def _parse_or(cursor: _Cursor) -> Expr:
    left = _parse_and(cursor)
    while cursor.peek().kind == "OR":
        cursor.consume("OR")
        right = _parse_and(cursor)
        left = _coalesce("or", left, right)
    return left


def _parse_and(cursor: _Cursor) -> Expr:
    left = _parse_not(cursor)
    while cursor.peek().kind == "AND":
        cursor.consume("AND")
        right = _parse_not(cursor)
        left = _coalesce("and", left, right)
    return left


def _parse_not(cursor: _Cursor) -> Expr:
    if cursor.peek().kind == "NOT":
        cursor.consume("NOT")
        inner = _parse_not(cursor)
        return Expr("must_not", (inner,))
    return _parse_atom(cursor)


def _parse_atom(cursor: _Cursor) -> Expr:
    if cursor.peek().kind == "(":
        cursor.consume("(")
        expr = _parse_or(cursor)
        cursor.consume(")")
        return expr
    return _parse_predicate(cursor)


def _parse_predicate(cursor: _Cursor) -> Expr:
    field_name = cursor.consume("IDENT").value
    head = cursor.peek()
    if head.kind == "IN":
        cursor.consume("IN")
        return Expr("or", _parse_in_list(cursor, field_name))
    if head.kind == "NOT":
        cursor.consume("NOT")
        cursor.consume("IN")
        inner = Expr("or", _parse_in_list(cursor, field_name))
        return Expr("must_not", (inner,))
    if head.kind == "BETWEEN":
        cursor.consume("BETWEEN")
        low = _parse_literal(cursor)
        cursor.consume("AND")
        high = _parse_literal(cursor)
        return Expr("btwn", (field_name, low, high))
    if head.kind == "OP":
        op_token = cursor.consume("OP")
        value = _parse_literal(cursor)
        return _build_comparison(field_name, op_token.value, value)
    message = (
        f"Expected operator after field {field_name!r} at position {head.position}, "
        f"got {head.value!r}"
    )
    raise QueryError(message)


def _build_comparison(field_name: str, op: str, value: _LiteralValue) -> Expr:
    if op in {"=", "=="}:
        return Expr("eq", (field_name, value))
    if op == "!=":
        return Expr("must_not", (Expr("eq", (field_name, value)),))
    operator_map = {">": "gt", ">=": "gte", "<": "lt", "<=": "lte"}
    if op in operator_map:
        return Expr(operator_map[op], (field_name, value))
    message = f"Unsupported operator: {op!r}"
    raise QueryError(message)


def _parse_in_list(cursor: _Cursor, field_name: str) -> tuple[Expr, ...]:
    cursor.consume("(")
    values: list[Expr] = [Expr("eq", (field_name, _parse_literal(cursor)))]
    while cursor.match(",") is not None:
        values.append(Expr("eq", (field_name, _parse_literal(cursor))))
    cursor.consume(")")
    return tuple(values)


def _parse_literal(cursor: _Cursor) -> _LiteralValue:
    head = cursor.peek()
    if head.kind == "STRING":
        cursor.consume("STRING")
        return head.value
    if head.kind == "NUMBER":
        cursor.consume("NUMBER")
        return _coerce_number(head.value, head.position)
    if head.kind == "IDENT":
        cursor.consume("IDENT")
        return head.value
    message = (
        f"Expected literal at position {head.position}, "
        f"got {head.kind} ({head.value!r})"
    )
    raise QueryError(message)


def _coalesce(operator: str, left: Expr, right: Expr) -> Expr:
    operands: list[Expr] = []
    for side in (left, right):
        if side.operator == operator:
            operands.extend(side.operands)
        else:
            operands.append(side)
    return Expr(operator, tuple(operands))
