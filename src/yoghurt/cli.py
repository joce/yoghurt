"""Command-line interface for yoghurt."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import textwrap
import time
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path
from string import Formatter
from typing import TYPE_CHECKING, Any, Final, Protocol, TextIO, cast
from urllib.parse import quote

# ``override`` lives in :mod:`typing` from 3.12 and in
# :mod:`typing_extensions` on older interpreters. typing_extensions
# re-exports the stdlib symbol when available, so importing from it on
# every version yields the same runtime object without a conditional that
# type checkers flag as having an unreachable branch.
from typing_extensions import override

from yoghurt import __version__
from yoghurt.client import YahooClient
from yoghurt.commands import COMMANDS, COMMANDS_BY_NAME, CommandSpec, FieldReference
from yoghurt.exceptions import YoghurtError
from yoghurt.params import ParamKind, ParamSpec, coerce_param
from yoghurt.query import QueryError
from yoghurt.query import parse as parse_query

if TYPE_CHECKING:
    from collections.abc import Sequence

    from yoghurt.types import ParamValue

_THREE_DAYS_SECONDS = 3 * 24 * 60 * 60
_HELP_WIDTH = 100
_HELP_MAX_POSITION = 32
_REFERENCE_INDENT = "  "
_REFERENCE_LABEL_WIDTH = _HELP_MAX_POSITION - len(_REFERENCE_INDENT) - 2
_DATE_PAIR_NAMES: Final[dict[str, tuple[str, str]]] = {
    "chart": ("period1", "period2"),
    "timeseries": ("period1", "period2"),
    "calendar-events": ("startDate", "endDate"),
}


class _YahooClientProtocol(Protocol):
    async def get(
        self,
        path: str,
        params: dict[str, ParamValue],
        *,
        use_crumb: bool = True,
        base_url: str | None = None,
    ) -> str: ...

    async def post(
        self,
        path: str,
        params: dict[str, ParamValue],
        json_body: dict[str, Any],
        *,
        use_crumb: bool = True,
        base_url: str | None = None,
    ) -> str: ...

    async def aclose(self) -> None: ...


class _HelpFormatter(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawDescriptionHelpFormatter,
):
    def __init__(self, prog: str) -> None:
        """Initialize a stable-width formatter for LLM-readable help."""

        super().__init__(prog, max_help_position=_HELP_MAX_POSITION, width=_HELP_WIDTH)

    @override
    def _get_help_string(self, action: argparse.Action) -> str:
        help_text = action.help
        if help_text is None:
            help_text = ""
        if action.default is argparse.SUPPRESS or action.default is None:
            return help_text
        if "%(default)" in help_text:
            return help_text
        return f"{help_text} (default: %(default)s)"


def _add_help_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-h",
        "--help",
        action="help",
        default=argparse.SUPPRESS,
        help="Show this help message and exit.",
    )


_VERBOSE_HELP_DOCS: Final[dict[str, str]] = {
    "screener": "QUERY_DSL.md",
    "visualization": "QUERY_DSL.md",
}


class _VerboseHelpAction(argparse.Action):
    """Print standard help, append the configured reference doc, then exit."""

    def __init__(
        self,
        option_strings: list[str],
        dest: str = argparse.SUPPRESS,
        default: object = argparse.SUPPRESS,
        doc_filename: str = "",
        help: str | None = None,  # noqa: A002
    ) -> None:
        """Store the doc filename and register the flag as a nargs=0 switch."""

        super().__init__(
            option_strings=option_strings,
            dest=dest,
            default=default,
            nargs=0,
            help=help,
        )
        self._doc_filename = doc_filename

    @override
    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: Any,
        option_string: str | None = None,
    ) -> None:
        """Print help, dump the doc, exit cleanly."""

        del namespace, values, option_string
        parser.print_help()
        doc_text = (files("yoghurt.docs") / self._doc_filename).read_text(
            encoding="utf-8"
        )
        sys.stdout.write("\n")
        sys.stdout.write(doc_text)
        if not doc_text.endswith("\n"):
            sys.stdout.write("\n")
        parser.exit()


def _add_verbose_help_option(
    parser: argparse.ArgumentParser, command_name: str
) -> None:
    doc_filename = _VERBOSE_HELP_DOCS.get(command_name)
    if doc_filename is None:
        return
    parser.add_argument(
        "--help-verbose",
        action=_VerboseHelpAction,
        doc_filename=doc_filename,
        help="Show this help plus the full reference documentation and exit.",
    )


def _examples_text(examples: tuple[str, ...]) -> str:
    return "\n".join(f"  {example}" for example in examples)


def _reference_text(references: tuple[FieldReference, ...]) -> str:
    lines: list[str] = []
    description_indent = " " * _HELP_MAX_POSITION
    for field in references:
        label = f"{field.name}:"
        if len(label) <= _REFERENCE_LABEL_WIDTH:
            first_prefix = f"{_REFERENCE_INDENT}{label:<{_REFERENCE_LABEL_WIDTH}}  "
            lines.extend(
                textwrap.wrap(
                    field.description,
                    width=_HELP_WIDTH,
                    initial_indent=first_prefix,
                    subsequent_indent=description_indent,
                )
            )
            continue
        lines.append(f"{_REFERENCE_INDENT}{label}")
        lines.extend(
            textwrap.wrap(
                field.description,
                width=_HELP_WIDTH,
                initial_indent=description_indent,
                subsequent_indent=description_indent,
            )
        )
    return "\n".join(lines)


def _epilog_for_command(command: CommandSpec) -> str:
    field_reference = ""
    if command.field_reference:
        field_reference = (
            f"\n\n{command.field_reference_title}:\n"
            f"{_reference_text(command.field_reference)}"
        )
    reference_sections = ""
    if command.reference_sections:
        reference_sections = "".join(
            f"\n\n{section.title}:\n{_reference_text(section.values)}"
            for section in command.reference_sections
        )
    common_modules = ""
    if command.common_modules:
        common_modules = "\n\nCommon --modules values:\n  " + ", ".join(
            command.common_modules
        )
    common_types = ""
    if command.common_types:
        common_types = "\n\nCommon --type values:\n  " + ", ".join(command.common_types)
    notes = ""
    if command.notes:
        notes = "\n\nNotes:\n" + "\n".join(f"  {note}" for note in command.notes)
    return (
        f"Yahoo endpoint:\n  {command.yahoo_url}\n\n"
        f"Examples:\n{_examples_text(command.examples)}"
        f"{reference_sections}"
        f"{field_reference}"
        f"{common_modules}"
        f"{common_types}"
        f"{notes}"
    )


def _add_global_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--version",
        action="version",
        version=f"yoghurt {__version__}",
        help="Show the program version and exit.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging to stderr.",
    )
    parser.add_argument(
        "--no-session-cache",
        action="store_true",
        help="Do not load or save Yahoo cookie/crumb session state.",
    )
    parser.add_argument(
        "--refresh-session",
        action="store_true",
        help="Ignore any cached Yahoo session and establish a fresh one.",
    )
    parser.add_argument(
        "--session-cache",
        type=Path,
        metavar="PATH",
        help="Override the Yahoo session cache path.",
    )


def _default_for_param(param: ParamSpec) -> object:
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


def _add_command_param(parser: argparse.ArgumentParser, param: ParamSpec) -> None:
    if param.positional:
        parser.add_argument(
            param.name,
            metavar=param.metavar,
            help=param.help,
        )
        return
    if param.kind is ParamKind.BOOLEAN:
        const = not param.default if isinstance(param.default, bool) else True
        parser.add_argument(
            param.option,
            dest=param.name,
            required=param.required,
            default=_default_for_param(param),
            action="store_const",
            const=const,
            help=param.help,
        )
        return
    parser.add_argument(
        param.option,
        dest=param.name,
        required=param.required,
        default=_default_for_param(param),
        metavar=param.metavar,
        help=param.help,
    )


def _set_command_parser(parser: argparse.ArgumentParser, command: CommandSpec) -> None:
    for param in command.params:
        _add_command_param(parser, param)
    parser.set_defaults(command_kind="modeled", command_name=command.name)


_PARQUET_COMMANDS: Final[frozenset[str]] = frozenset(
    {"chart", "screener", "visualization"}
)
_PARQUET_COMMANDS_HELP: Final[str] = ", ".join(sorted(_PARQUET_COMMANDS))


def _add_parquet_output_options(parser: argparse.ArgumentParser) -> None:
    """Add ``--format`` and ``--out`` to a Parquet-capable subparser."""

    parser.add_argument(
        "--format",
        dest="output_format",
        choices=("json", "parquet"),
        default="json",
        help=(
            "Output format. Default writes the raw Yahoo JSON body to "
            "stdout. Parquet parses the response into a typed table written "
            "to --out."
        ),
    )
    parser.add_argument(
        "--out",
        dest="out_path",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            "Destination file for the Parquet table. Required when "
            "--format parquet; rejected otherwise."
        ),
    )


def _add_parquet_negative_guards(parser: argparse.ArgumentParser) -> None:
    """Register hidden ``--format`` / ``--out`` placeholders on a non-parquet command.

    These accept the flags so argparse does not bail with the generic
    ``unrecognized arguments`` message; the post-parse check in
    :func:`_enforce_parquet_arg_pairing` then emits a directed error that
    names the commands that DO support Parquet (chart, screener,
    visualization). Help output is suppressed so unrelated commands' help
    pages stay clean.
    """

    parser.add_argument(
        "--format",
        dest="output_format",
        default="json",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--out",
        dest="out_path",
        type=Path,
        default=None,
        help=argparse.SUPPRESS,
    )
    parser.set_defaults(_parquet_unsupported=True)


def build_parser() -> argparse.ArgumentParser:
    """Build yoghurt's adaptive argument parser.

    Returns:
        argparse.ArgumentParser: The configured root parser.
    """

    parser = argparse.ArgumentParser(
        prog="yoghurt",
        description=(
            "Expose Yahoo Finance endpoints to the command line and print raw "
            "JSON response bodies."
        ),
        epilog="Run `yoghurt <endpoint> --help` for endpoint-specific parameters.",
        formatter_class=_HelpFormatter,
        add_help=False,
    )
    _add_help_option(parser)
    _add_global_options(parser)
    subparsers = parser.add_subparsers(
        title="commands",
        metavar="COMMAND",
        dest="subcommand",
    )
    for command in COMMANDS:
        command_parser = subparsers.add_parser(
            command.name,
            help=command.summary,
            description=command.description,
            epilog=_epilog_for_command(command),
            formatter_class=_HelpFormatter,
            add_help=False,
        )
        _add_help_option(command_parser)
        _add_verbose_help_option(command_parser, command.name)
        _set_command_parser(command_parser, command)
        if command.name in _PARQUET_COMMANDS:
            _add_parquet_output_options(command_parser)
        else:
            _add_parquet_negative_guards(command_parser)

        # Slot the DSL screeners in between screener-predefined and
        # screener-discover so help output reads as a single discovery block.
        if command.name == "screener-predefined":
            visualization_parser = subparsers.add_parser(
                "visualization",
                help="Query any Yahoo data-platform entity via a SQL-flavored DSL.",
                description=(
                    "Run a SQL-flavored statement against a Yahoo data-platform "
                    "entity. SELECT returns tabular rows; AGGREGATE returns "
                    "histogram-style groupings across one or many entities. Use "
                    "--query for the DSL or --body-json to send a raw JSON body."
                ),
                epilog=_VISUALIZATION_EPILOG,
                formatter_class=_HelpFormatter,
                add_help=False,
            )
            _add_help_option(visualization_parser)
            _add_verbose_help_option(visualization_parser, "visualization")
            _add_query_command_options(visualization_parser, route="visualization")
            _add_parquet_output_options(visualization_parser)

            screener_parser = subparsers.add_parser(
                "screener",
                help="Query any Yahoo asset class via a SQL-flavored DSL.",
                description=(
                    "Query a Yahoo asset class with a SQL-flavored statement. "
                    "Use --query for the DSL or --body-json to send a raw JSON "
                    "body."
                ),
                epilog=_SCREENER_EPILOG,
                formatter_class=_HelpFormatter,
                add_help=False,
            )
            _add_help_option(screener_parser)
            _add_verbose_help_option(screener_parser, "screener")
            _add_query_command_options(screener_parser, route="screener")
            _add_parquet_output_options(screener_parser)

    raw_parser = subparsers.add_parser(
        "raw",
        help="Send raw parameters to any Yahoo query path.",
        description=(
            "Pass NAME=VALUE query parameters through to any Yahoo Finance "
            "query path. Useful for endpoints yoghurt does not model yet."
        ),
        epilog=(
            "Example:\n"
            "  yoghurt raw /v7/finance/quote --param symbols=AAPL,MSFT "
            "--param formatted=true"
        ),
        formatter_class=_HelpFormatter,
        add_help=False,
    )
    _add_help_option(raw_parser)
    raw_parser.add_argument("path", help="Yahoo query path, such as /v7/finance/quote.")
    raw_parser.add_argument(
        "--param",
        action="append",
        default=[],
        metavar="NAME=VALUE",
        help="Query parameter to pass through. Repeat for multiple parameters.",
    )
    _add_parquet_negative_guards(raw_parser)
    raw_parser.add_argument(
        "--no-crumb",
        action="store_true",
        help="Do not add Yahoo's crumb parameter to the request.",
    )
    raw_parser.set_defaults(command_kind="raw")
    return parser


_VISUALIZATION_EPILOG: Final[str] = """\
Yahoo endpoint:
  https://query1.finance.yahoo.com/v1/finance/visualization

Grammar: SELECT cols FROM entities [WHERE expr] [ORDER BY field] [LIMIT n]
         AGGREGATE date_hist(field, 'interval') FROM entities [WHERE expr]
                   [JOIN BY field] [FILL ident] [LIMIT n]
Run `yoghurt visualization --help-verbose` for the full DSL reference.

Examples:
  # Earnings calendar (sub-week, US, exclude OTC)
  yoghurt visualization --query "
    SELECT ticker, companyshortname, startdatetime, intradaymarketcap
    FROM sp_earnings
    WHERE region = 'us'
      AND startdatetime BETWEEN '2026-05-09' AND '2026-05-16'
      AND eventtype IN ('EAD', 'ERA')
    ORDER BY intradaymarketcap DESC
    LIMIT 25"

  # AAPL insider transactions
  yoghurt visualization --query "
    SELECT ticker, transactiondate, shares
    FROM INSIDER_TRANSACTION
    WHERE ticker = 'AAPL'
    ORDER BY transactiondate DESC LIMIT 50"

  # Cross-entity calendar histogram
  yoghurt visualization --query "
    AGGREGATE date_hist(startdatetime, '1d')
    FROM sp_earnings, economic_event, splits, ipo_info
    WHERE startdatetime BETWEEN '2026-05-03' AND '2026-05-09'
    JOIN BY startdatetime FILL pad"

  # Raw JSON body escape hatch
  yoghurt visualization --body-json @body.json

Known entityIdType values: sp_earnings, economic_event, splits, ipo_info,
  insider_transaction, research_reports, trade_idea. Multi-entity FROM lists
  power AGGREGATE statements.

Field naming:
  visualization returns snake_case / dotted names (intradaymarketcap,
  peratio.lasttwelvemonths); screener returns camelCase (marketCap,
  peRatioLtm). Both routes accept either on input.

Field reference:
  yoghurt screener-instrument-fields <entity>

Premium data:
  Four entities return 401 on direct query (analyst_ratings,
  tradingcentral_event_info, institutional_interest, institutional_holdings).
  See `yoghurt screener-predefined --help` for curated presets that surface
  slices on the free tier."""

_SCREENER_EPILOG: Final[str] = """\
Yahoo endpoint:
  https://query1.finance.yahoo.com/v1/finance/screener

Grammar: SELECT cols FROM quote_type [WHERE expr] [ORDER BY field] [LIMIT n]
Run `yoghurt screener --help-verbose` for the full DSL reference.

Examples:
  # Large-cap technology screen
  yoghurt screener --query "
    SELECT ticker, intradaymarketcap, sector, peratio.lasttwelvemonths
    FROM EQUITY
    WHERE region = 'us'
      AND sector = 'Technology'
      AND intradaymarketcap >= 10e9
      AND peratio.lasttwelvemonths < 30
    ORDER BY intradaymarketcap DESC
    LIMIT 100"

  # Raw JSON body escape hatch
  yoghurt screener --body-json @body.json

Known quoteType values: EQUITY, ETF, MUTUALFUND, CRYPTOCURRENCY, INDEX,
  FUTURE, OPTION, BOND, CURRENCY, COMMODITY, WARRANT. Entity IDs accepted by
  visualization (e.g. sp_earnings) also work here, but the visualization
  route usually fits event-style entities better.

Field naming:
  screener returns camelCase (marketCap, peRatioLtm, fiftyTwoWeekHigh);
  visualization returns snake_case / dotted (intradaymarketcap,
  peratio.lasttwelvemonths, fiftytwowkhigh). Both routes accept either on
  input.

Field reference:
  yoghurt screener-instrument-fields <quote-type>     # e.g. equity, etf

Premium data:
  Many quoteTypes include isPremium=true fields that 401 when filtered.
  Premium-data entities (analyst_ratings, tradingcentral_event_info,
  institutional_interest, institutional_holdings) are reachable on the free
  tier only through curated `screener-predefined` presets."""


def _add_query_command_options(parser: argparse.ArgumentParser, *, route: str) -> None:
    body_group = parser.add_mutually_exclusive_group(required=True)
    body_group.add_argument(
        "--query",
        metavar="SQL",
        help=(
            "SQL-flavored query string. See examples for grammar. "
            "Mutually exclusive with --body-json."
        ),
    )
    body_group.add_argument(
        "--body-json",
        dest="body_json",
        metavar="JSON_OR_@FILE",
        help=(
            "Raw JSON body for Yahoo's POST endpoint. Pass inline JSON or "
            "@path/to/body.json. Mutually exclusive with --query."
        ),
    )
    parser.add_argument(
        "--lang",
        default="en-US",
        metavar="LANG",
        help="Yahoo response language.",
    )
    parser.add_argument(
        "--region",
        default="US",
        metavar="REGION",
        help="Yahoo response region.",
    )
    if route == "screener":
        # Yahoo's screener route accepts formatted=False just fine; the
        # cleanest response (plain scalar cells) comes from formatted=False
        # and useRecordsResponse=True. Default to that and let users opt back
        # in to the {raw, fmt, longFmt} struct shape if they need it.
        parser.add_argument(
            "--formatted",
            action="store_true",
            default=False,
            help="Request Yahoo formatted values.",
        )
        parser.add_argument(
            "--no-records-response",
            dest="useRecordsResponse",
            action="store_const",
            const=False,
            default=True,
            help="Do not request Yahoo's records-style screener response shape.",
        )
    parser.set_defaults(command_kind="query", query_route=route)


def _configure_logging(*, verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(level=level, format="%(levelname)s:%(name)s:%(message)s")


def _params_for_command(
    command: CommandSpec, namespace: argparse.Namespace
) -> dict[str, ParamValue]:
    params: dict[str, ParamValue] = {}
    date_pair = _date_pair_for_command(command)
    if date_pair is not None:
        start_spec, end_spec = date_pair
        explicit_start = hasattr(namespace, start_spec.name)
        explicit_end = hasattr(namespace, end_spec.name)
        if explicit_end and not explicit_start:
            message = (
                f"{end_spec.option} cannot be provided without {start_spec.option}"
            )
            raise ValueError(message)
    current_timestamp = int(time.time())
    for spec in command.params:
        if not hasattr(namespace, spec.name):
            dynamic_default = _dynamic_default_for_param(spec, current_timestamp)
            if dynamic_default is not None:
                params[spec.name] = dynamic_default
                continue
            if (
                spec.allow_empty_default
                and isinstance(spec.default, str)
                and len(spec.default) == 0
            ):
                params[spec.name] = ""
            continue
        value = getattr(namespace, spec.name)
        if value is None:
            continue
        if spec.path_param:
            continue
        if isinstance(value, bool | int | float):
            params[spec.name] = value
            continue
        params[spec.name] = coerce_param(spec, value)
    return params


def _date_pair_for_command(command: CommandSpec) -> tuple[ParamSpec, ParamSpec] | None:
    names = _DATE_PAIR_NAMES.get(command.name)
    if names is None:
        return None
    start = next(spec for spec in command.params if spec.name == names[0])
    end = next(spec for spec in command.params if spec.name == names[1])
    return start, end


def _validate_command_params(
    command: CommandSpec, params: dict[str, ParamValue]
) -> None:
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


def _path_for_command(command: CommandSpec, namespace: argparse.Namespace) -> str:
    path_values: dict[str, str] = {}
    for _, field_name, _, _ in Formatter().parse(command.path):
        if field_name is None:
            continue
        spec = next(param for param in command.params if param.name == field_name)
        raw_value = getattr(namespace, spec.name)
        coerced_value = coerce_param(spec, raw_value)
        path_values[field_name] = quote(str(coerced_value), safe="")
    return command.path.format(**path_values)


def _params_for_raw(raw_params: Sequence[str]) -> dict[str, ParamValue]:
    params: dict[str, ParamValue] = {}
    for raw_param in raw_params:
        name, separator, value = raw_param.partition("=")
        if not separator or not name:
            message = f"--param expects NAME=VALUE, got {raw_param!r}"
            raise ValueError(message)
        params[name] = value
    return params


_QUERY_ROUTE_PATHS: Final[dict[str, str]] = {
    "visualization": "/v1/finance/visualization",
    "screener": "/v1/finance/screener",
}


def _resolve_query_body(namespace: argparse.Namespace) -> dict[str, Any]:
    if getattr(namespace, "query", None) is not None:
        try:
            statement = parse_query(namespace.query)
        except QueryError as exc:
            message = f"--query parse error: {exc}"
            raise ValueError(message) from exc
        return statement.to_body()
    raw = namespace.body_json
    if raw.startswith("@"):
        path = Path(raw[1:])
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            message = f"--body-json file could not be read: {exc}"
            raise ValueError(message) from exc
    else:
        text = raw
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError as exc:
        message = f"--body-json is not valid JSON: {exc}"
        raise ValueError(message) from exc
    if not isinstance(loaded, dict):
        message = "--body-json must be a JSON object"
        raise ValueError(message)  # noqa: TRY004 - surfaced as a user error
    return cast("dict[str, Any]", loaded)


def _params_for_query_command(namespace: argparse.Namespace) -> dict[str, ParamValue]:
    params: dict[str, ParamValue] = {
        "lang": namespace.lang,
        "region": namespace.region,
    }
    if namespace.query_route == "screener":
        params["formatted"] = namespace.formatted
        params["useRecordsResponse"] = namespace.useRecordsResponse
    return params


async def _dispatch_command(
    namespace: argparse.Namespace,
    stdout: TextIO,
    client: _YahooClientProtocol,
) -> int:
    if namespace.command_kind == "modeled":
        command = COMMANDS_BY_NAME[namespace.command_name]
        params = _params_for_command(command, namespace)
        _validate_command_params(command, params)
        _validate_parquet_request(namespace)
        body = await client.get(
            _path_for_command(command, namespace),
            params,
            use_crumb=command.use_crumb,
            base_url=command.base_url,
        )
        if _wants_parquet(namespace):
            _emit_chart_parquet(namespace, params, body, stdout)
            return 0
    elif namespace.command_kind == "raw":
        body = await client.get(
            namespace.path,
            _params_for_raw(namespace.param),
            use_crumb=not namespace.no_crumb,
        )
    elif namespace.command_kind == "query":
        _validate_parquet_request(namespace)
        request_body = _resolve_query_body(namespace)
        wire_params = _params_for_query_command(namespace)
        body = await client.post(
            _QUERY_ROUTE_PATHS[namespace.query_route],
            wire_params,
            request_body,
        )
        if _wants_parquet(namespace):
            _emit_tabular_parquet(namespace, body, wire_params, stdout)
            return 0
    else:
        return 2
    stdout.write(body)
    if body and not body.endswith("\n"):
        stdout.write("\n")
    return 0


async def _run_async(
    namespace: argparse.Namespace,
    stdout: TextIO,
    client: _YahooClientProtocol,
) -> int:
    try:
        return await _dispatch_command(namespace, stdout, client)
    finally:
        await client.aclose()


def _wants_parquet(namespace: argparse.Namespace) -> bool:
    return getattr(namespace, "output_format", "json") == "parquet"


def _enforce_parquet_arg_pairing(
    parser: argparse.ArgumentParser,
    namespace: argparse.Namespace,
    stderr: TextIO,
) -> None:
    """Reject ``--format`` / ``--out`` / ``--formatted`` combos at parse time.

    Failures emit an argparse-style usage error to ``stderr`` and exit 2.
    Runtime-only conditions (AGGREGATE rejection) are handled later in
    :func:`_validate_parquet_request`.
    """

    output_format = getattr(namespace, "output_format", "json")
    out_path = getattr(namespace, "out_path", None)
    unsupported = getattr(namespace, "_parquet_unsupported", False)
    if unsupported and (output_format == "parquet" or out_path is not None):
        _parquet_arg_error(
            parser,
            stderr,
            f"--format parquet / --out are only supported for {_PARQUET_COMMANDS_HELP}",
        )
    if output_format == "parquet" and out_path is None:
        _parquet_arg_error(parser, stderr, "--format parquet requires --out PATH")
    if output_format != "parquet" and out_path is not None:
        _parquet_arg_error(parser, stderr, "--out is only valid with --format parquet")
    if output_format == "parquet" and getattr(namespace, "formatted", False):
        _parquet_arg_error(
            parser,
            stderr,
            "--format parquet requires scalar cells; "
            "drop --formatted or switch to --format json",
        )


def _parquet_arg_error(
    parser: argparse.ArgumentParser, stderr: TextIO, message: str
) -> None:
    """Emit an argparse-style usage error to ``stderr`` and exit 2.

    Mirrors :meth:`argparse.ArgumentParser.error` but writes to the caller-
    supplied stream so tests can capture the message via the same channel
    they capture all other CLI errors.

    Raises:
        SystemExit: Always, with code 2.
    """

    parser.print_usage(stderr)
    stderr.write(f"{parser.prog}: error: {message}\n")
    raise SystemExit(2)


def _validate_parquet_request(namespace: argparse.Namespace) -> None:
    """Reject Parquet requests that fail runtime-only checks.

    Parse-time pairing is handled in :func:`_enforce_parquet_arg_pairing`.
    Here we cover AGGREGATE rejection — which requires parsing the DSL
    ``--query`` or peeking at the ``--body-json`` payload.

    Raises:
        YoghurtError: If the user asked for Parquet against an AGGREGATE
            request (via ``--query`` or ``--body-json``).
    """

    if not _wants_parquet(namespace):
        return
    if getattr(namespace, "command_kind", None) != "query":
        return
    query = getattr(namespace, "query", None)
    if query is not None:
        try:
            statement = parse_query(query)
        except QueryError as exc:
            message = f"--query parse error: {exc}"
            raise YoghurtError(message) from exc
        if statement.kind.value == "aggregate":
            raise YoghurtError(_AGGREGATE_PARQUET_REJECTION)
        return
    body_json = getattr(namespace, "body_json", None)
    if body_json is not None and _body_json_is_aggregate(body_json):
        raise YoghurtError(_AGGREGATE_PARQUET_REJECTION)


_AGGREGATE_PARQUET_REJECTION: Final[str] = (
    "--format parquet not supported for AGGREGATE queries; use --format json"
)


def _body_json_is_aggregate(body_json: str) -> bool:
    """Return ``True`` if a ``--body-json`` payload describes an aggregation.

    The brief flags any body whose top-level keys indicate an aggregate
    request — Yahoo's ``/visualization`` endpoint takes the aggregation
    instruction in a top-level ``aggregation`` key.

    Returns:
        bool: ``True`` when the JSON payload is parseable and contains a
        top-level ``aggregation`` object.

    Raises:
        YoghurtError: If the ``@file`` form points at an unreadable path
            or the JSON cannot be parsed. (Surfacing those errors here
            keeps the parquet validator and the later body resolver
            symmetric.)
    """

    raw = body_json
    if raw.startswith("@"):
        path = Path(raw[1:])
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            message = f"--body-json file could not be read: {exc}"
            raise YoghurtError(message) from exc
    else:
        text = raw
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError as exc:
        message = f"--body-json is not valid JSON: {exc}"
        raise YoghurtError(message) from exc
    return isinstance(loaded, dict) and "aggregation" in loaded


def _emit_chart_parquet(
    namespace: argparse.Namespace,
    params: dict[str, ParamValue],
    body: str,
    stdout: TextIO,
) -> None:
    """Write the chart response to Parquet and emit the descriptor line.

    ``params`` is the already-coerced wire-params dict produced by
    :func:`_params_for_command`. Reusing it (rather than re-reading the raw
    ``namespace`` attributes) means Parquet metadata records the exact
    epoch-second values sent to Yahoo, regardless of whether the user
    passed an int, a ``YYYY-MM-DD`` date, or an ISO datetime.
    """

    from yoghurt.parquet_writer import write_chart_parquet  # noqa: PLC0415

    out_path = namespace.out_path
    period1 = _epoch_seconds_param(params, "period1")
    period2 = _epoch_seconds_param(params, "period2")
    descriptor = write_chart_parquet(
        body,
        out_path,
        ticker=namespace.symbol,
        interval=namespace.interval,
        period1=period1,
        period2=period2,
    )
    stdout.write(json.dumps(descriptor))
    stdout.write("\n")


def _epoch_seconds_param(params: dict[str, ParamValue], name: str) -> int:
    """Return ``params[name]`` as an int, raising if it is not numeric.

    Returns:
        int: The integer epoch-second wire value.

    Raises:
        YoghurtError: If the value is missing or not an integer.
    """

    value = params.get(name)
    if isinstance(value, bool) or not isinstance(value, int):
        message = f"chart {name} must be an integer second"
        raise YoghurtError(message)
    return value


def _emit_tabular_parquet(
    namespace: argparse.Namespace,
    body: str,
    wire_params: dict[str, ParamValue],
    stdout: TextIO,
) -> None:
    """Write a screener/visualization response to Parquet and emit the descriptor."""

    from yoghurt.parquet_writer import write_tabular_parquet  # noqa: PLC0415

    query = getattr(namespace, "query", None)
    descriptor = write_tabular_parquet(
        body,
        namespace.out_path,
        command=namespace.query_route,
        route=namespace.query_route,
        query=query,
        wire_params=dict(wire_params),
    )
    stdout.write(json.dumps(descriptor))
    stdout.write("\n")


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    client: _YahooClientProtocol | None = None,
) -> int:
    """Run the yoghurt CLI.

    Returns:
        int: Process-style exit code.
    """

    parser = build_parser()
    output = stdout or sys.stdout
    if stdout is None:
        reconfigure = getattr(output, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")
    error_output = stderr or sys.stderr
    namespace = parser.parse_args(argv)
    if not hasattr(namespace, "command_kind"):
        parser.print_help(error_output)
        return 2
    _enforce_parquet_arg_pairing(parser, namespace, error_output)

    _configure_logging(verbose=namespace.verbose)
    active_client = client or YahooClient(
        use_session_cache=not namespace.no_session_cache,
        refresh_session=namespace.refresh_session,
        session_cache_path=namespace.session_cache,
    )
    try:
        return asyncio.run(_run_async(namespace, output, active_client))
    except (ValueError, YoghurtError) as exc:
        error_output.write(f"yoghurt: error: {exc}\n")
        return 1
