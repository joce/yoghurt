"""Internal implementation for analysis-ready market-wide event calendars."""

# Polars' expression stubs intentionally admit Unknown values for general
# expressions. This module constructs only fixed, locally-known columns.
# pyright: reportUnknownMemberType=false

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import TYPE_CHECKING, Final, TypeAlias

import polars as pl

from yoghurt.exceptions import YahooApiError
from yoghurt.frames import Frame
from yoghurt.params import parse_datetime_milliseconds
from yoghurt.types import MARKET_CALENDAR_KINDS, MarketCalendarKind

if TYPE_CHECKING:
    from collections.abc import Mapping

    from polars.datatypes import DataType, DataTypeClass

DateLike: TypeAlias = int | str | date | datetime
_MAX_LIMIT: Final[int] = 100
_DEFAULT_WINDOW_DAYS: Final[int] = 7


@dataclass(frozen=True, slots=True)
class _CalendarSpec:
    entity: str
    source_fields: tuple[str, ...]
    names: Mapping[str, str]
    schema: Mapping[str, DataType | DataTypeClass]
    date_columns: frozenset[str] = frozenset()
    datetime_columns: frozenset[str] = frozenset()


_CALENDARS: Final[dict[MarketCalendarKind, _CalendarSpec]] = {
    "earnings": _CalendarSpec(
        entity="sp_earnings",
        source_fields=(
            "ticker",
            "companyshortname",
            "intradaymarketcap",
            "eventname",
            "startdatetime",
            "startdatetimetype",
            "epsestimate",
            "epsactual",
            "epssurprisepct",
        ),
        names={
            "ticker": "symbol",
            "companyshortname": "company_name",
            "intradaymarketcap": "market_cap",
            "eventname": "event_name",
            "startdatetime": "event_at",
            "startdatetimetype": "timing",
            "epsestimate": "eps_estimate",
            "epsactual": "eps_actual",
            "epssurprisepct": "eps_surprise_percent",
        },
        schema={
            "symbol": pl.String,
            "company_name": pl.String,
            "market_cap": pl.Float64,
            "event_name": pl.String,
            "event_at": pl.Datetime("ms", "UTC"),
            "timing": pl.String,
            "eps_estimate": pl.Float64,
            "eps_actual": pl.Float64,
            "eps_surprise_percent": pl.Float64,
        },
        datetime_columns=frozenset({"event_at"}),
    ),
    "ipo": _CalendarSpec(
        entity="ipo_info",
        source_fields=(
            "ticker",
            "companyshortname",
            "exchange_short_name",
            "filingdate",
            "startdatetime",
            "amendeddate",
            "pricefrom",
            "priceto",
            "offerprice",
            "currencyname",
            "shares",
            "dealtype",
        ),
        names={
            "ticker": "symbol",
            "companyshortname": "company_name",
            "exchange_short_name": "exchange",
            "filingdate": "filing_date",
            "startdatetime": "event_at",
            "amendeddate": "amended_date",
            "pricefrom": "price_from",
            "priceto": "price_to",
            "offerprice": "offer_price",
            "currencyname": "currency",
            "shares": "shares",
            "dealtype": "deal_type",
        },
        schema={
            "symbol": pl.String,
            "company_name": pl.String,
            "exchange": pl.String,
            "filing_date": pl.Date,
            "event_at": pl.Datetime("ms", "UTC"),
            "amended_date": pl.Date,
            "price_from": pl.Float64,
            "price_to": pl.Float64,
            "offer_price": pl.Float64,
            "currency": pl.String,
            "shares": pl.Float64,
            "deal_type": pl.String,
        },
        date_columns=frozenset({"filing_date", "amended_date"}),
        datetime_columns=frozenset({"event_at"}),
    ),
    "economic": _CalendarSpec(
        entity="economic_event",
        source_fields=(
            "econ_release",
            "country_code",
            "startdatetime",
            "period",
            "after_release_actual",
            "consensus_estimate",
            "prior_release_actual",
            "originally_reported_actual",
        ),
        names={
            "econ_release": "event",
            "country_code": "region",
            "startdatetime": "event_at",
            "period": "period",
            "after_release_actual": "actual",
            "consensus_estimate": "expected",
            "prior_release_actual": "prior",
            "originally_reported_actual": "revised",
        },
        schema={
            "event": pl.String,
            "region": pl.String,
            "event_at": pl.Datetime("ms", "UTC"),
            "period": pl.String,
            "actual": pl.String,
            "expected": pl.String,
            "prior": pl.String,
            "revised": pl.String,
        },
        datetime_columns=frozenset({"event_at"}),
    ),
    "splits": _CalendarSpec(
        entity="splits",
        source_fields=(
            "ticker",
            "companyshortname",
            "startdatetime",
            "optionable",
            "old_share_worth",
            "share_worth",
        ),
        names={
            "ticker": "symbol",
            "companyshortname": "company_name",
            "startdatetime": "payable_at",
            "optionable": "optionable",
            "old_share_worth": "old_share_worth",
            "share_worth": "new_share_worth",
        },
        schema={
            "symbol": pl.String,
            "company_name": pl.String,
            "payable_at": pl.Datetime("ms", "UTC"),
            "optionable": pl.Boolean,
            "old_share_worth": pl.Float64,
            "new_share_worth": pl.Float64,
        },
        datetime_columns=frozenset({"payable_at"}),
    ),
}


def build_market_calendar_query(
    kind: MarketCalendarKind | str,
    *,
    start_date: DateLike | None,
    end_date: DateLike | None,
    limit: int,
    offset: int,
) -> str:
    """Build the trusted visualization query for one market calendar.

    The public date window is inclusive. Yahoo's query uses a half-open
    interval ending at midnight after ``end_date`` so the entire final
    calendar day is included.

    Returns:
        str: A visualization DSL query using fixed entities and fields.

    Raises:
        ValueError: If the kind, window, limit, or offset is invalid.
    """

    spec = _calendar_spec(kind)
    start, end = _resolve_window(start_date, end_date)
    _validate_page(limit, offset)
    try:
        exclusive_end = end + timedelta(days=1)
    except OverflowError as exc:
        message = "end_date is too large to form an inclusive calendar window"
        raise ValueError(message) from exc
    fields = ", ".join(spec.source_fields)
    return (
        f"SELECT {fields} FROM {spec.entity} "  # ruff:ignore[hardcoded-sql-expression] - fixed local fields and validated scalars
        f"WHERE startdatetime >= '{start.isoformat()}' "
        f"AND startdatetime < '{exclusive_end.isoformat()}' "
        f"ORDER BY startdatetime ASC LIMIT {limit} OFFSET {offset}"
    )


def normalize_market_calendar(kind: MarketCalendarKind | str, frame: Frame) -> Frame:
    """Normalize one visualization Frame to its stable calendar schema.

    Returns:
        Frame: Canonically named and typed rows. Empty input retains every
        declared column.

    Raises:
        YahooApiError: If a populated response omits a requested field.
    """

    spec = _calendar_spec(kind)
    if frame.df.is_empty():
        return Frame(df=pl.DataFrame(schema=spec.schema), fetched_at=frame.fetched_at)
    missing = set(spec.source_fields) - set(frame.df.columns)
    if missing:
        names = ", ".join(sorted(missing))
        message = f"{kind} calendar response omitted requested fields: {names}"
        raise YahooApiError(code="malformed-response", description=message)
    expressions = []
    for source in spec.source_fields:
        target = spec.names[source]
        column = pl.col(source)
        if target in spec.datetime_columns:
            column = column.str.to_datetime(
                time_unit="ms", time_zone="UTC", strict=True
            )
        elif target in spec.date_columns:
            column = column.str.to_datetime(
                time_unit="ms", time_zone="UTC", strict=True
            ).dt.date()
        else:
            column = column.cast(spec.schema[target], strict=True)
        expressions.append(column.alias(target))
    return Frame(df=frame.df.select(expressions), fetched_at=frame.fetched_at)


def _calendar_spec(kind: MarketCalendarKind | str) -> _CalendarSpec:
    try:
        return _CALENDARS[kind]  # pyright: ignore[reportArgumentType]
    except (KeyError, TypeError) as exc:
        expected = ", ".join(MARKET_CALENDAR_KINDS)
        message = f"unsupported market calendar {kind!r}; expected one of: {expected}"
        raise ValueError(message) from exc


def _resolve_window(
    start_value: DateLike | None, end_value: DateLike | None
) -> tuple[date, date]:
    today = datetime.now(timezone.utc).date()
    start = (
        _coerce_date(start_value, "start_date") if start_value is not None else today
    )
    end = (
        _coerce_date(end_value, "end_date")
        if end_value is not None
        else start + timedelta(days=_DEFAULT_WINDOW_DAYS)
    )
    if end < start:
        message = "end_date must be on or after start_date"
        raise ValueError(message)
    return start, end


def _coerce_date(value: object, name: str) -> date:
    if isinstance(value, bool):
        message = f"{name} must be a date, datetime, string, or Unix timestamp"
        raise TypeError(message)
    if isinstance(value, datetime):
        parsed = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
        return parsed.astimezone(timezone.utc).date()
    if isinstance(value, date):
        return value
    if not isinstance(value, int | str):
        message = f"{name} must be a date, datetime, string, or Unix timestamp"
        raise TypeError(message)
    try:
        milliseconds = parse_datetime_milliseconds(str(value))
        return datetime.fromtimestamp(milliseconds / 1000, timezone.utc).date()
    except (OSError, OverflowError, ValueError) as exc:
        message = f"invalid {name}: {value!r}"
        raise ValueError(message) from exc


def _validate_page(limit: object, offset: object) -> None:
    if (
        isinstance(limit, bool)
        or not isinstance(limit, int)
        or not 1 <= limit <= _MAX_LIMIT
    ):
        message = f"limit must be an integer from 1 to {_MAX_LIMIT}"
        raise ValueError(message)
    if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
        message = "offset must be a non-negative integer"
        raise ValueError(message)
