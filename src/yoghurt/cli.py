"""Command-line interface for yoghurt."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import textwrap
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, Protocol, TextIO, cast

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
from yoghurt.params import (
    CHART_INTERVALS,
    CHART_RANGES,
    ParamKind,
    ParamSpec,
    build_params,
    build_path,
    default_for_param,
    validate_params,
)
from yoghurt.query import QueryError
from yoghurt.query import parse as parse_query
from yoghurt.skills import AGENT_TARGETS, TargetReport
from yoghurt.skills import install as skills_install
from yoghurt.skills import resolve_roots as skills_resolve_roots
from yoghurt.skills import status as skills_status
from yoghurt.skills import uninstall as skills_uninstall

if TYPE_CHECKING:
    from collections.abc import Sequence

    from yoghurt.types import ParamValue

_HELP_WIDTH = 100
_HELP_MAX_POSITION = 32
_REFERENCE_INDENT = "  "
_REFERENCE_LABEL_WIDTH = _HELP_MAX_POSITION - len(_REFERENCE_INDENT) - 2


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
            default=default_for_param(param),
            action="store_const",
            const=const,
            help=param.help,
        )
        return
    parser.add_argument(
        param.option,
        dest=param.name,
        required=param.required,
        default=default_for_param(param),
        metavar=param.metavar,
        help=param.help,
    )


def _set_command_parser(parser: argparse.ArgumentParser, command: CommandSpec) -> None:
    for param in command.params:
        _add_command_param(parser, param)
    parser.set_defaults(command_kind="modeled", command_name=command.name)


_PARQUET_COMMANDS: Final[frozenset[str]] = frozenset(
    {"chart", "history", "screener", "visualization"}
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


_HISTORY_EPILOG: Final[str] = """Examples:
  yoghurt history AAPL
  yoghurt history AAPL,MSFT --period 1y --interval 1d
  yoghurt history SPY --period 1y --format parquet --out spy.parquet

Notes:
  Prices are corporate-action-adjusted from Yahoo's adjusted close. Volume is
  unchanged. A price row without usable adjusted close is rejected rather than
  returned raw. No heuristic price repair is applied. Use chart for Yahoo's raw
  OHLC, adjusted close, metadata, and events.
"""


def _add_history_parser(subparsers: Any) -> None:  # noqa: ANN401
    """Add the analysis-ready history command after the raw chart command."""

    parser = subparsers.add_parser(
        "history",
        help="Fetch adjusted historical OHLC data for one or more symbols.",
        description=(
            "Corporate-action-adjusted OHLCV rows in a stable long-form table, "
            "suitable for grouping by symbol before analysis."
        ),
        epilog=_HISTORY_EPILOG,
        formatter_class=_HelpFormatter,
        add_help=False,
    )
    _add_help_option(parser)
    parser.add_argument(
        "symbols",
        metavar="SYMBOL[,SYMBOL...]",
        help="One or more comma-separated Yahoo symbols.",
    )
    parser.add_argument(
        "--period",
        choices=CHART_RANGES,
        default=None,
        metavar="PERIOD",
        help=(
            "Relative history window. Supported values: "
            f"{', '.join(CHART_RANGES)}. Defaults to 1mo when dates are omitted; "
            "cannot be combined with --start or --end."
        ),
    )
    parser.add_argument(
        "--start",
        default=None,
        metavar="DATE",
        help="Start as a Unix timestamp, YYYY-MM-DD date, or ISO datetime.",
    )
    parser.add_argument(
        "--end",
        default=None,
        metavar="DATE",
        help="Optional end in the same formats as --start; defaults to now.",
    )
    parser.add_argument(
        "--interval",
        choices=CHART_INTERVALS,
        default="1d",
        metavar="INTERVAL",
        help=f"Bar interval. Supported values: {', '.join(CHART_INTERVALS)}.",
    )
    parser.add_argument(
        "--include-pre-post",
        action="store_true",
        help="Include pre-market and post-market rows when supported.",
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=("json", "parquet"),
        default="json",
        help=(
            "Output adjusted rows as JSON on stdout or write a Parquet table to --out."
        ),
    )
    parser.add_argument(
        "--out",
        dest="out_path",
        type=Path,
        default=None,
        metavar="PATH",
        help="Destination required with --format parquet.",
    )
    parser.set_defaults(command_kind="history", command_name="history")


def build_parser() -> argparse.ArgumentParser:
    """Build yoghurt's adaptive argument parser.

    Returns:
        argparse.ArgumentParser: The configured root parser.
    """

    parser = argparse.ArgumentParser(
        prog="yoghurt",
        description=(
            "Expose Yahoo Finance endpoints to the command line and print raw "
            "JSON response bodies. The history command instead emits an "
            "analysis-ready adjusted table."
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

        if command.name == "chart":
            _add_history_parser(subparsers)

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

    skills_parser = subparsers.add_parser(
        "skills",
        help="Install, remove, or list the yoghurt agent skill.",
        description=(
            "Manage the yoghurt agent skill in agent skill directories. See "
            "`yoghurt skills <subcommand> --help` for each operation."
        ),
        formatter_class=_HelpFormatter,
        add_help=False,
    )
    _add_skills_command_group(skills_parser)
    return parser


def _add_skills_targeting_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--agent",
        dest="agent",
        default=None,
        metavar="NAME[,NAME...]",
        help=(
            f"Comma-separated named agent targets ({', '.join(sorted(AGENT_TARGETS))})."
        ),
    )
    parser.add_argument(
        "--to",
        dest="to",
        type=Path,
        default=None,
        metavar="PATH",
        help="Additional skills root to install into or remove from.",
    )
    parser.add_argument(
        "--project",
        action="store_true",
        help="Use project-level roots (relative to the current directory).",
    )


def _add_skills_command_group(skills_parser: argparse.ArgumentParser) -> None:
    _add_help_option(skills_parser)
    skills_parser.set_defaults(
        command_kind="skills", skills_action=None, skills_parser=skills_parser
    )
    skills_subparsers = skills_parser.add_subparsers(
        title="skills commands",
        metavar="SUBCOMMAND",
        dest="skills_subcommand",
    )

    install_parser = skills_subparsers.add_parser(
        "install",
        help="Install the yoghurt agent skill into agent skill directories.",
        description=(
            "Copy the yoghurt agent skill into the named agent skill "
            "directories, stamping the installed package version. Refuses "
            "to overwrite a directory it does not own."
        ),
        formatter_class=_HelpFormatter,
        add_help=False,
    )
    _add_help_option(install_parser)
    _add_skills_targeting_options(install_parser)
    install_parser.set_defaults(
        command_kind="skills",
        skills_action="install",
        skills_action_parser=install_parser,
    )

    uninstall_parser = skills_subparsers.add_parser(
        "uninstall",
        help="Remove the yoghurt agent skill from agent skill directories.",
        description=(
            "Remove the yoghurt agent skill from the named agent skill "
            "directories. Refuses to remove a directory it does not own."
        ),
        formatter_class=_HelpFormatter,
        add_help=False,
    )
    _add_help_option(uninstall_parser)
    _add_skills_targeting_options(uninstall_parser)
    uninstall_parser.set_defaults(
        command_kind="skills",
        skills_action="uninstall",
        skills_action_parser=uninstall_parser,
    )

    list_parser = skills_subparsers.add_parser(
        "list",
        help="Show where the yoghurt agent skill is installed.",
        description=(
            "Show the yoghurt agent skill's install state across every "
            "named agent, at both user and project scope."
        ),
        formatter_class=_HelpFormatter,
        add_help=False,
    )
    _add_help_option(list_parser)
    list_parser.set_defaults(command_kind="skills", skills_action="list")


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


def _values_from_namespace(
    command: CommandSpec, namespace: argparse.Namespace
) -> dict[str, object]:
    """Extract the present-key values a command's params saw from argparse.

    Returns:
        dict[str, object]: Mapping of param name to raw namespace value,
        containing only the keys that argparse actually set (mirroring
        ``hasattr(namespace, spec.name)`` present-keys semantics).
    """

    return {
        spec.name: getattr(namespace, spec.name)
        for spec in command.params
        if hasattr(namespace, spec.name)
    }


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
        values = _values_from_namespace(command, namespace)
        params = build_params(command, values)
        validate_params(command, params)
        _validate_parquet_request(namespace)
        body = await client.get(
            build_path(command, values),
            params,
            use_crumb=command.use_crumb,
            base_url=command.base_url,
        )
        if _wants_parquet(namespace):
            _emit_chart_parquet(namespace, params, body, stdout)
            return 0
    elif namespace.command_kind == "history":
        await _dispatch_history(namespace, stdout, client)
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


async def _dispatch_history(
    namespace: argparse.Namespace,
    stdout: TextIO,
    client: _YahooClientProtocol,
) -> None:
    """Fetch, adjust, and emit one multi-symbol history table.

    Raises:
        ValueError: If the symbol list or period/date arguments are invalid.
    """

    from yoghurt.history import (  # noqa: PLC0415
        HISTORY_REQUEST_BATCH_SIZE,
        concat_frames,
        frame_from_chart_result,
        request_values,
    )
    from yoghurt.tabular import parse_chart_result  # noqa: PLC0415

    symbols = [part.strip() for part in namespace.symbols.split(",")]
    if any(not symbol for symbol in symbols):
        message = "symbols must be a comma-separated list without empty values"
        raise ValueError(message)
    common_values = request_values(
        period=namespace.period,
        start=namespace.start,
        end=namespace.end,
        interval=namespace.interval,
        include_pre_post=namespace.include_pre_post,
    )
    effective_period = common_values.get("range")
    if effective_period is not None and not isinstance(effective_period, str):
        message = "history period must be a string"
        raise ValueError(message)
    command = COMMANDS_BY_NAME["chart"]
    requests: list[tuple[str, dict[str, ParamValue], str]] = []
    for symbol in symbols:
        values = {**common_values, "symbol": symbol}
        params = build_params(command, values)
        validate_params(command, params)
        requests.append((build_path(command, values), params, symbol))
    bodies: list[str] = []
    for offset in range(0, len(requests), HISTORY_REQUEST_BATCH_SIZE):
        batch = requests[offset : offset + HISTORY_REQUEST_BATCH_SIZE]
        bodies.extend(
            await asyncio.gather(
                *(
                    client.get(
                        path,
                        params,
                        use_crumb=command.use_crumb,
                        base_url=command.base_url,
                    )
                    for path, params, _symbol in batch
                )
            )
        )
    frame = concat_frames(
        [
            frame_from_chart_result(parse_chart_result(body), symbol)
            for body, (_path, _params, symbol) in zip(bodies, requests, strict=True)
        ]
    )
    if _wants_parquet(namespace):
        from yoghurt.parquet_writer import write_history_parquet  # noqa: PLC0415

        descriptor = write_history_parquet(
            frame,
            namespace.out_path,
            symbols=symbols,
            period=effective_period,
            start=namespace.start,
            end=namespace.end,
            interval=namespace.interval,
        )
        stdout.write(json.dumps(descriptor))
        stdout.write("\n")
        return
    body = frame.write_json()
    stdout.write(body)
    if not body.endswith("\n"):
        stdout.write("\n")


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
    :func:`yoghurt.params.build_params`. Reusing it (rather than re-reading
    the raw ``namespace`` attributes) means Parquet metadata records the exact
    epoch-second values sent to Yahoo, regardless of whether the user
    passed an int, a ``YYYY-MM-DD`` date, or an ISO datetime.

    Raises:
        YoghurtError: If range or epoch metadata has an invalid type.
    """

    from yoghurt.parquet_writer import write_chart_parquet  # noqa: PLC0415

    out_path = namespace.out_path
    period1 = _optional_epoch_seconds_param(params, "period1")
    period2 = _optional_epoch_seconds_param(params, "period2")
    range_value = params.get("range")
    if range_value is not None and not isinstance(range_value, str):
        message = "chart range must be a string"
        raise YoghurtError(message)
    descriptor = write_chart_parquet(
        body,
        out_path,
        ticker=namespace.symbol,
        interval=namespace.interval,
        period1=period1,
        period2=period2,
        range=range_value,
    )
    stdout.write(json.dumps(descriptor))
    stdout.write("\n")


def _optional_epoch_seconds_param(
    params: dict[str, ParamValue], name: str
) -> int | None:
    """Return ``params[name]`` as an int when present.

    Returns:
        int | None: The integer epoch-second wire value, or ``None``.

    Raises:
        YoghurtError: If a present value is not an integer.
    """

    value = params.get(name)
    if value is None:
        return None
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


def _skills_agents_from_namespace(namespace: argparse.Namespace) -> list[str]:
    """Parse the --agent comma-list, mirroring the --modules CSV contract.

    Returns:
        list[str]: The agent names, or an empty list when --agent was not
        given.

    Raises:
        ValueError: If the list contains empty comma-separated values.
    """

    raw = (getattr(namespace, "agent", "") or "").strip()
    if not raw:
        return []
    items = [item.strip() for item in raw.split(",")]
    if any(not item for item in items):
        message = "--agent cannot contain empty comma-separated values"
        raise ValueError(message)
    return items


def _skills_roots_or_usage_error(
    namespace: argparse.Namespace,
    stderr: TextIO,
) -> list[Path] | None:
    """Resolve --agent/--to into roots, or emit a usage error and return None.

    Returns:
        list[Path] | None: The resolved roots, or ``None`` if a usage error
        was already written to ``stderr`` (caller should return exit code 2).
    """

    action_parser = namespace.skills_action_parser
    to = getattr(namespace, "to", None)
    try:
        agents = _skills_agents_from_namespace(namespace)
        if not agents and to is None:
            _parquet_arg_error(
                action_parser, stderr, "one of --agent or --to is required"
            )
        return skills_resolve_roots(agents, project=namespace.project, to=to)
    except ValueError as exc:
        _parquet_arg_error(action_parser, stderr, str(exc))
    return None  # pragma: no cover - _parquet_arg_error always raises


def _install_report_line(report: TargetReport) -> str:
    skill_dir = report.root / "yoghurt"
    if report.action == "refused":
        return f"skipped (not the yoghurt skill): {skill_dir}"
    return f"installed: {skill_dir} (yoghurt {report.detail})"


def _uninstall_report_line(report: TargetReport) -> str:
    skill_dir = report.root / "yoghurt"
    if report.action == "refused":
        return f"skipped (not the yoghurt skill): {skill_dir}"
    if report.action == "removed":
        return f"removed: {skill_dir}"
    return f"absent: {skill_dir}"


def _list_report_line(report: TargetReport) -> str:
    """Format one status() report as an agent/scope/root/state line.

    report.detail carries "agent scope" for an absent target, or
    "agent scope version" for a current/stale one (see yoghurt.skills.status).

    Returns:
        str: The formatted status line for one named target.
    """

    if report.action == "absent":
        return f"{report.detail} {report.root} absent"
    label, _, version = report.detail.rpartition(" ")
    if report.action == "current":
        return f"{label} {report.root} installed {version} (current)"
    return (
        f"{label} {report.root} installed {version} (stale; current is {__version__})"
    )


def _dispatch_skills(
    namespace: argparse.Namespace,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    action = getattr(namespace, "skills_action", None)
    if action is None:
        namespace.skills_parser.print_help(stderr)
        return 2
    if action == "list":
        for report in skills_status():
            stdout.write(_list_report_line(report))
            stdout.write("\n")
        return 0
    roots = _skills_roots_or_usage_error(namespace, stderr)
    if roots is None:
        return 2
    if action == "install":
        reports = skills_install(roots)
        line_for = _install_report_line
    else:
        reports = skills_uninstall(roots)
        line_for = _uninstall_report_line
    for report in reports:
        stdout.write(line_for(report))
        stdout.write("\n")
    return 1 if any(report.action == "refused" for report in reports) else 0


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
    if namespace.command_kind == "skills":
        return _dispatch_skills(namespace, output, error_output)
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
