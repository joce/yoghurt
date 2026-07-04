"""Endpoint parameter metadata and coercion."""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from string import Formatter
from typing import TYPE_CHECKING, Final
from urllib.parse import quote

if TYPE_CHECKING:
    from collections.abc import Mapping

    from yoghurt.commands import CommandSpec
    from yoghurt.types import ParamValue


class ParamKind(str, Enum):
    """Supported CLI parameter kinds."""

    STRING = "string"
    CSV = "csv"
    INTEGER = "integer"
    DATETIME = "datetime"
    DATETIME_MILLISECONDS = "datetime_milliseconds"
    BOOLEAN = "boolean"


@dataclass(frozen=True, slots=True)
class ParamSpec:
    """Describe one endpoint query parameter."""

    name: str
    cli_name: str
    kind: ParamKind
    help: str
    positional: bool = False
    path_param: bool = False
    required: bool = False
    default: ParamValue | None = None
    metavar: str | None = None
    min_items: int | None = None
    max_items: int | None = None
    allowed_values: tuple[str, ...] = ()
    csv_separator: str = ","
    allow_empty_default: bool = False

    @property
    def option(self) -> str:
        """This parameter's long CLI option."""

        if self.positional:
            return self.name
        return f"--{self.cli_name}"


_TRUE_VALUES: Final[frozenset[str]] = frozenset({"1", "true", "t", "yes", "y", "on"})
_FALSE_VALUES: Final[frozenset[str]] = frozenset({"0", "false", "f", "no", "n", "off"})
_MILLISECONDS_TIMESTAMP_DIGITS: Final[int] = 13
_THREE_DAYS_SECONDS: Final[int] = 3 * 24 * 60 * 60
_DATE_PAIR_NAMES: Final[dict[str, tuple[str, str]]] = {
    "chart": ("period1", "period2"),
    "timeseries": ("period1", "period2"),
    "calendar-events": ("startDate", "endDate"),
}


def _allows_omitted_empty_default(spec: ParamSpec) -> bool:
    return (
        spec.allow_empty_default
        and isinstance(spec.default, str)
        and len(spec.default) == 0
    )


def _coerce_string_param(spec: ParamSpec, value: str) -> str:
    stripped = value.strip()
    if not stripped:
        if _allows_omitted_empty_default(spec):
            message = f"{spec.name} cannot be empty"
            raise ValueError(message)
        message = f"{spec.option} cannot be empty"
        raise ValueError(message)
    return stripped


def _coerce_csv_param(spec: ParamSpec, value: str) -> str:
    stripped = value.strip()
    if not stripped:
        message = f"{spec.option} cannot be empty"
        raise ValueError(message)
    items = [item.strip() for item in stripped.split(",")]
    if any(not item for item in items):
        message = f"{spec.option} cannot contain empty comma-separated values"
        raise ValueError(message)
    if spec.min_items is not None and len(items) < spec.min_items:
        message = (
            f"{spec.option} expects at least {spec.min_items} "
            f"comma-separated value; got {len(items)}"
        )
        raise ValueError(message)
    if spec.max_items is not None and len(items) > spec.max_items:
        message = (
            f"{spec.option} accepts at most {spec.max_items} "
            f"comma-separated values; got {len(items)}"
        )
        raise ValueError(message)
    if spec.allowed_values:
        allowed_values = set(spec.allowed_values)
        for item in items:
            if item not in allowed_values:
                allowed_text = ", ".join(spec.allowed_values)
                message = (
                    f"{spec.option} unsupported value {item!r}; "
                    f"expected one of: {allowed_text}"
                )
                raise ValueError(message)
    return spec.csv_separator.join(items)


def parse_boolean(value: str) -> bool:
    """Parse a CLI boolean value.

    Returns:
        bool: Parsed boolean.

    Raises:
        ValueError: If the value is not a recognized boolean spelling.
    """

    normalized = value.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    message = f"expected boolean value, got {value!r}"
    raise ValueError(message)


def parse_datetime(value: str) -> int:
    """Parse a Unix timestamp or datetime value for Yahoo query params.

    Returns:
        int: Unix timestamp in seconds.

    Raises:
        ValueError: If the value is not an integer timestamp, YYYY-MM-DD date, or
            ISO datetime.
    """

    stripped = value.strip()
    try:
        return int(stripped)
    except ValueError:
        pass

    try:
        parsed = datetime.fromisoformat(stripped.replace("Z", "+00:00"))
    except ValueError as exc:
        message = (
            f"expected Unix timestamp, YYYY-MM-DD date, or ISO datetime; got {value!r}"
        )
        raise ValueError(message) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    else:
        parsed = parsed.astimezone(timezone.utc)
    return int(parsed.timestamp())


def parse_datetime_milliseconds(value: str) -> int:
    """Parse a Unix timestamp or datetime value into milliseconds.

    Returns:
        int: Unix timestamp in milliseconds.
    """

    stripped = value.strip()
    if stripped.isdecimal() and len(stripped) >= _MILLISECONDS_TIMESTAMP_DIGITS:
        return int(stripped)
    return parse_datetime(value) * 1000


def coerce_param(spec: ParamSpec, value: str) -> ParamValue:
    """Coerce one CLI parameter value according to its endpoint spec.

    Returns:
        ParamValue: Coerced scalar query value.

    Raises:
        ValueError: If the value does not satisfy the parameter spec.
    """

    if spec.kind is ParamKind.STRING:
        return _coerce_string_param(spec, value)
    if spec.kind is ParamKind.CSV:
        return _coerce_csv_param(spec, value)
    if spec.kind is ParamKind.INTEGER:
        try:
            return int(value)
        except ValueError as exc:
            message = f"{spec.option} expects an integer"
            raise ValueError(message) from exc
    if spec.kind is ParamKind.DATETIME:
        try:
            return parse_datetime(value)
        except ValueError as exc:
            message = f"{spec.option} {exc}"
            raise ValueError(message) from exc
    if spec.kind is ParamKind.DATETIME_MILLISECONDS:
        try:
            return parse_datetime_milliseconds(value)
        except ValueError as exc:
            message = f"{spec.option} {exc}"
            raise ValueError(message) from exc
    if spec.kind is ParamKind.BOOLEAN:
        return parse_boolean(value)

    message = f"unsupported parameter kind: {spec.kind}"
    raise ValueError(message)


def default_for_param(param: ParamSpec) -> object:
    """Return the argparse-facing default for one CLI parameter.

    Dynamic defaults (``now``, ``now-3d``) and empty-string "no value"
    defaults resolve to ``argparse.SUPPRESS`` so the argparse namespace omits
    the key entirely when the user does not pass a value, letting
    :func:`build_params` apply the real (possibly time-dependent) default.

    Returns:
        object: The value to pass as an ``argparse`` argument's ``default``.
    """

    if param.default in {"now", "now-3d"}:
        return argparse.SUPPRESS
    if param.default == "today":
        return datetime.now(timezone.utc).date().isoformat()
    if (
        param.allow_empty_default
        and isinstance(param.default, str)
        and len(param.default) == 0
    ):
        return argparse.SUPPRESS
    return param.default


def _dynamic_default_for_param(
    spec: ParamSpec, current_timestamp: int
) -> ParamValue | None:
    multiplier = 1000 if spec.kind is ParamKind.DATETIME_MILLISECONDS else 1
    if spec.default == "now":
        return current_timestamp * multiplier
    if spec.default == "now-3d":
        return (current_timestamp - _THREE_DAYS_SECONDS) * multiplier
    return None


def _date_pair_for_command(command: CommandSpec) -> tuple[ParamSpec, ParamSpec] | None:
    names = _DATE_PAIR_NAMES.get(command.name)
    if names is None:
        return None
    start = next(spec for spec in command.params if spec.name == names[0])
    end = next(spec for spec in command.params if spec.name == names[1])
    return start, end


def _check_date_pair_present(
    date_pair: tuple[ParamSpec, ParamSpec], values: Mapping[str, object]
) -> None:
    start_spec, end_spec = date_pair
    explicit_start = start_spec.name in values
    explicit_end = end_spec.name in values
    if explicit_end and not explicit_start:
        message = f"{end_spec.option} cannot be provided without {start_spec.option}"
        raise ValueError(message)


def _param_from_default(spec: ParamSpec, current_timestamp: int) -> ParamValue | None:
    """Return the static or dynamic default for an absent param, if any."""

    dynamic_default = _dynamic_default_for_param(spec, current_timestamp)
    if dynamic_default is not None:
        return dynamic_default
    if (
        spec.allow_empty_default
        and isinstance(spec.default, str)
        and len(spec.default) == 0
    ):
        return ""
    return None


def _param_from_value(spec: ParamSpec, value: object) -> ParamValue | None:
    """Coerce one present-key value into its wire representation.

    Returns:
        ParamValue | None: The coerced wire value, or ``None`` if this
        param contributes nothing to the wire params (an explicit ``None``
        value or a path param).

    Raises:
        TypeError: If the value is not a supported scalar type.
    """

    if value is None or spec.path_param:
        return None
    if isinstance(value, bool | int | float):
        return value
    if not isinstance(value, str):
        message = f"{spec.option} expects a string value, got {type(value).__name__}"
        raise TypeError(message)
    return coerce_param(spec, value)


def build_params(
    command: CommandSpec, values: Mapping[str, object]
) -> dict[str, ParamValue]:
    """Build the wire query params for a command from present-key values.

    A key present in ``values`` (even if its value is ``None``) is treated
    as an explicit user-provided value; a missing key falls back to the
    command's static or dynamic default.

    Returns:
        dict[str, ParamValue]: Coerced query parameters ready to send to
        Yahoo.
    """

    params: dict[str, ParamValue] = {}
    date_pair = _date_pair_for_command(command)
    if date_pair is not None:
        _check_date_pair_present(date_pair, values)
    current_timestamp = int(time.time())
    for spec in command.params:
        if spec.name not in values:
            default_value = _param_from_default(spec, current_timestamp)
            if default_value is not None:
                params[spec.name] = default_value
            continue
        value = _param_from_value(spec, values[spec.name])
        if value is not None:
            params[spec.name] = value
    return params


def validate_params(command: CommandSpec, params: dict[str, ParamValue]) -> None:
    """Validate a built params dict against command-specific rules.

    Raises:
        ValueError: If a date-pair window is reversed or non-numeric, or if
            ``chart``'s ``interval`` is not one of the supported values.
    """

    date_pair = _date_pair_for_command(command)
    if date_pair is not None:
        start_spec, end_spec = date_pair
        if start_spec.name in params and end_spec.name in params:
            start = params[start_spec.name]
            end = params[end_spec.name]
            if not isinstance(start, int) or not isinstance(end, int):
                message = (
                    f"{start_spec.option} and {end_spec.option} must be datetime values"
                )
                raise ValueError(message)
            if end <= start:
                message = f"{end_spec.option} must be greater than {start_spec.option}"
                raise ValueError(message)

    if command.name == "chart":
        interval = params.get("interval")
        allowed_intervals = {"1m", "5m", "15m", "1d", "1wk", "1mo"}
        if interval not in allowed_intervals:
            allowed_text = ", ".join(sorted(allowed_intervals))
            message = (
                f"--interval unsupported value {interval!r}; "
                f"expected one of: {allowed_text}"
            )
            raise ValueError(message)


def build_path(command: CommandSpec, values: Mapping[str, object]) -> str:
    """Build the request path for a command from present-key values.

    Returns:
        str: The command's path template with path params URL-quoted and
        substituted in.

    Raises:
        TypeError: If a path parameter's value is not a string.
    """

    path_values: dict[str, str] = {}
    for _, field_name, _, _ in Formatter().parse(command.path):
        if field_name is None:
            continue
        spec = next(param for param in command.params if param.name == field_name)
        raw_value = values[spec.name]
        if not isinstance(raw_value, str):
            message = (
                f"{spec.option} expects a string value, got {type(raw_value).__name__}"
            )
            raise TypeError(message)
        coerced_value = coerce_param(spec, raw_value)
        path_values[field_name] = quote(str(coerced_value), safe="")
    return command.path.format(**path_values)
