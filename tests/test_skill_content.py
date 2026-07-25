"""Integrity gates for the agent-skill content tree (spec: agent-skills design).

Two families of tests live here:

1. **Structural gates** (frontmatter, tree shape, domain index links,
   relative-link resolution, sharp-edge shape) — content-integrity checks
   that fail on any regression to the tree Task 1 authored.
2. **Snippet pinning** — every fenced ``python`` block in the content tree
   is pinned so a future edit cannot silently drift from working code.
   Three snippets mirror the README quickstart (already behaviorally
   pinned by ``tests/test_readme_examples.py``; here we only assert the
   verbatim mirror). The rest get their own offline, corpus-backed
   behavioral test using the same ``_get_client`` monkeypatch seam
   ``tests/test_readme_examples.py`` establishes.
"""

# The optional pyarrow dep is absent in the base dev env (see
# tests/test_frames.py), so frame.to_arrow()'s return type is Unknown to
# pyright here; the positive-path check below skips at runtime via
# importorskip, matching that file's own suppression.
# pyright: reportUnknownMemberType=false

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

import yoghurt
import yoghurt._core as core
from yoghurt.api import Ticker, screener, visualization

if TYPE_CHECKING:
    from typing import Any

    from yoghurt.types import ParamValue

CONTENT = Path(__file__).parent.parent / "src" / "yoghurt" / "skills" / "content"
DOMAINS = ["analysis", "dataframes", "fundamentals", "market-data", "queries"]
_MAX_DESCRIPTION_LENGTH = 1024

_CORPUS_ROOT = Path(__file__).parent / "fixtures" / "corpus"
_README = Path(__file__).parent.parent / "README.md"


def _frontmatter() -> dict[str, str]:
    text = (CONTENT / "SKILL.md").read_text(encoding="utf-8")
    match = re.match(r"---\n(.*?)\n---\n", text, flags=re.DOTALL)
    assert match, "SKILL.md must open with YAML frontmatter"
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, _, value = line.partition(":")
        if _:
            fields[key.strip()] = value.strip()
    return fields


def test_frontmatter_name_matches_skill_directory_contract() -> None:
    """The standard requires name == installed directory name (yoghurt)."""
    assert _frontmatter()["name"] == "yoghurt"


def test_frontmatter_description_within_standard_limit() -> None:
    """The description must be non-empty and within the standard's limit."""
    description = _frontmatter()["description"]
    assert description
    assert len(description) <= _MAX_DESCRIPTION_LENGTH


def test_content_tree_has_exactly_the_spec_files() -> None:
    """One SKILL.md + README/SHARP-EDGES per domain; nothing else."""
    files = sorted(
        p.relative_to(CONTENT).as_posix() for p in CONTENT.rglob("*") if p.is_file()
    )
    expected = sorted(
        ["SKILL.md"]
        + [f"{d}/README.md" for d in DOMAINS]
        + [f"{d}/SHARP-EDGES.md" for d in DOMAINS]
    )
    assert files == expected


def test_every_domain_is_linked_from_skill_md() -> None:
    """Every domain directory has a link from SKILL.md's domain index."""
    body = (CONTENT / "SKILL.md").read_text(encoding="utf-8")
    for domain in DOMAINS:
        assert f"{domain}/README.md" in body, f"SKILL.md must index {domain}"


@pytest.mark.parametrize(
    "md", sorted(CONTENT.rglob("*.md")), ids=lambda p: p.name + "/" + p.parent.name
)
def test_relative_links_resolve(md: Path) -> None:
    """Every relative link in a content markdown file points to a real file."""
    body = md.read_text(encoding="utf-8")
    for target in re.findall(r"\]\((?!https?://|#)([^)]+?)(?:#[^)]*)?\)", body):
        assert (md.parent / target).exists(), f"{md.name}: dead link {target}"


@pytest.mark.parametrize("domain", DOMAINS)
def test_sharp_edges_entries_follow_the_fixed_shape(domain: str) -> None:
    """Every `## ` entry carries a Severity line and an Evidence line."""
    body = (CONTENT / domain / "SHARP-EDGES.md").read_text(encoding="utf-8")
    entries = re.split(r"\n## ", body)[1:]
    assert entries, f"{domain}: SHARP-EDGES.md has no entries"
    for entry in entries:
        title = entry.splitlines()[0]
        assert re.search(r"\*\*Severity:\*\* (high|medium|low)", entry), (domain, title)
        assert "Evidence:" in entry, (domain, title)


# ---------------------------------------------------------------------------
# Snippet pinning
#
# Every fenced ``python`` block across SKILL.md + the ten domain files is
# accounted for below: either as a README-mirror assertion or as its own
# offline, corpus-backed behavioral test. Running `grep -c '^```python'`
# across the content tree and summing gives 23 blocks total (2 SKILL.md +
# 7 market-data/README + 2 fundamentals/README + 4 analysis/README +
# 3 queries/README + 3 dataframes/README + 1 fundamentals/SHARP-EDGES +
# 1 queries/SHARP-EDGES). Of these, 3 are byte-identical mirrors of
# README.md's ``## Library`` quickstart (already behaviorally pinned by
# tests/test_readme_examples.py): SKILL.md's `quote()` line,
# market-data/README.md's `chart(...).to_polars()` line, and
# queries/README.md's `screener(...)` block. The remaining 20 are
# domain-original and each gets its own behavioral pin below (one test,
# fundamentals/SHARP-EDGES.md's "wrong way" snippet, is pinned
# verbatim-only -- see its docstring for why it is not executed).
# ---------------------------------------------------------------------------


def _corpus_text(relative_path: str) -> str:
    """Read a corpus fixture body as text.

    Returns:
        str: The raw fixture file contents.
    """

    return (_CORPUS_ROOT / relative_path).read_text(encoding="utf-8")


class _FakeClient:
    """Minimal stand-in for YahooClient that returns a canned body.

    Mirrors ``tests/test_readme_examples.py``'s ``_FakeClient`` exactly: the
    established seam for pinning library-API snippets offline against a
    corpus fixture, reused here for the skill content snippets.
    """

    def __init__(self, body: str) -> None:
        """Store the canned response body."""
        self.body = body

    async def get(
        self,
        path: str,
        params: dict[str, ParamValue],
        *,
        use_crumb: bool = True,
        base_url: str | None = None,
    ) -> str:
        """Return the canned body.

        Returns:
            str: The canned response body.
        """
        del path, params, use_crumb, base_url
        return self.body

    async def post(
        self,
        path: str,
        params: dict[str, ParamValue],
        json_body: dict[str, Any],
        *,
        use_crumb: bool = True,
        base_url: str | None = None,
    ) -> str:
        """Return the canned body.

        Returns:
            str: The canned response body.
        """
        del path, params, json_body, use_crumb, base_url
        return self.body

    async def aclose(self) -> None:
        """No-op close."""


def _install_fake(monkeypatch: pytest.MonkeyPatch, body: str) -> None:
    """Patch the core client seam with a fake that returns ``body``."""

    monkeypatch.setattr(core, "_get_client", lambda: _FakeClient(body))


def _assert_in_content(domain: str | None, filename: str, snippet: str) -> None:
    """Assert ``snippet`` appears verbatim in a content file."""

    path = CONTENT / domain / filename if domain else CONTENT / filename
    body = path.read_text(encoding="utf-8")
    assert snippet in body, f"{path}: expected snippet not found verbatim"


# --- README mirrors (3) -----------------------------------------------------
#
# These three snippets are copied verbatim from README.md's `## Library`
# quickstart, which tests/test_readme_examples.py already pins behaviorally
# (test_readme_chart_quickstart / test_readme_quote_quickstart /
# test_readme_screener_quickstart). Here we only assert the mirror holds:
# the exact text also appears in README.md.

_README_TEXT = _README.read_text(encoding="utf-8")

_README_MIRROR_LINES = {
    "SKILL.md quote": ('quote = yoghurt.Ticker("AAPL").quote()', None, "SKILL.md"),
    "market-data chart": (
        'bars = yoghurt.Ticker("AAPL").chart(interval="1d").to_polars()',
        "market-data",
        "README.md",
    ),
}


@pytest.mark.parametrize(
    ("line", "domain", "filename"),
    _README_MIRROR_LINES.values(),
    ids=_README_MIRROR_LINES.keys(),
)
def test_readme_mirror_snippet_matches_content(
    line: str, domain: str | None, filename: str
) -> None:
    """Each README-mirror line appears verbatim in both README.md and content."""

    assert line in _README_TEXT, f"README.md: expected mirrored line not found: {line}"
    _assert_in_content(domain, filename, line)


def test_queries_screener_snippet_mirrors_readme_verbatim() -> None:
    """queries/README.md's screener example is the full README query, verbatim."""

    query_snippet = (
        "tech = yoghurt.screener(\n"
        '    "SELECT ticker, intradaymarketcap FROM EQUITY "\n'
        "    \"WHERE region = 'us' AND sector = 'Technology' \"\n"
        '    "ORDER BY intradaymarketcap DESC LIMIT 25"\n'
        ").to_polars()"
    )
    assert query_snippet in _README_TEXT
    _assert_in_content("queries", "README.md", query_snippet)

    # dataframes/README.md's conversion-vocabulary example reuses the same
    # query string (not the same variable name or trailing `.to_polars()`,
    # since it demonstrates all five conversions on `frame`, not just one)
    # -- see test_dataframes_readme_conversion_vocabulary for its own pin.
    query_text_only = (
        '"SELECT ticker, intradaymarketcap FROM EQUITY "\n'
        "    \"WHERE region = 'us' AND sector = 'Technology' \"\n"
        '    "ORDER BY intradaymarketcap DESC LIMIT 25"'
    )
    _assert_in_content("dataframes", "README.md", query_text_only)


# --- Domain-original snippets (20), pinned behaviorally --------------------


def test_market_data_readme_search_and_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """market-data/README.md: broad search and typed instrument lookup."""

    search_snippets = [
        'matches = yoghurt.search("Appel", fuzzy=True, quotes_count=5)',
        (
            "symbols = [\n"
            "    match.symbol for match in matches.quotes "
            "if match.symbol is not None\n"
            "]"
        ),
    ]
    for snippet in search_snippets:
        _assert_in_content("market-data", "README.md", snippet)

    _install_fake(monkeypatch, _corpus_text("search/Appel_fuzzy.json"))
    matches = yoghurt.search("Appel", fuzzy=True, quotes_count=5)
    symbols = [match.symbol for match in matches.quotes if match.symbol is not None]
    assert "AAPL" in symbols

    lookup_snippets = [
        'page = yoghurt.lookup("Apple", type="equity", count=25)',
        "instruments = page.documents",
    ]
    for snippet in lookup_snippets:
        _assert_in_content("market-data", "README.md", snippet)

    _install_fake(monkeypatch, _corpus_text("lookup/type_equity.json"))
    page = yoghurt.lookup("Apple", type="equity", count=25)
    instruments = page.documents
    assert instruments
    assert all(document.quote_type.value == "equity" for document in instruments)


def test_market_data_readme_quote(monkeypatch: pytest.MonkeyPatch) -> None:
    """market-data/README.md: the domain's own ``Ticker(...).quote()`` opener.

    Not a byte-identical README.md mirror (this block imports via
    ``from yoghurt import Ticker`` and omits the ``yoghurt.`` prefix), so it
    is pinned on its own rather than folded into the mirror-line checks.
    """

    snippet = 'quote = Ticker("AAPL").quote()'
    _assert_in_content("market-data", "README.md", snippet)

    _install_fake(monkeypatch, _corpus_text("quote/AAPL_default.json"))
    quote = Ticker("AAPL").quote()
    assert quote.symbol == "AAPL"


def test_market_data_readme_quotes_module_function(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """market-data/README.md: ``yoghurt.quotes([...])`` multi-symbol fetch."""

    snippet = 'records = yoghurt.quotes(["AAPL", "MSFT", "NVDA"])'
    _assert_in_content("market-data", "README.md", snippet)

    _install_fake(monkeypatch, _corpus_text("quote/multi.json"))
    records = yoghurt.quotes(["AAPL", "MSFT", "NVDA"])
    assert len(records) > 0
    assert all(record.symbol for record in records)


def test_market_data_readme_spark(monkeypatch: pytest.MonkeyPatch) -> None:
    """market-data/README.md: ``Ticker(...).spark(range=..., interval=...)``."""

    snippet = 'spark = yoghurt.Ticker("AAPL").spark(range="1d", interval="1m")'
    _assert_in_content("market-data", "README.md", snippet)

    _install_fake(monkeypatch, _corpus_text("spark/AAPL.json"))
    spark = yoghurt.Ticker("AAPL").spark(range="1d", interval="1m")
    assert spark.to_polars().height > 0


def test_market_data_readme_options_chain_then_expiration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """market-data/README.md: discover an expiration from the chain, re-request it."""

    snippets = [
        'chain = yoghurt.Ticker("AAPL").options()',
        "next_expiration = chain.expiration_dates[1]",
        'next_chain = yoghurt.Ticker("AAPL").options(date=next_expiration)',
    ]
    for snippet in snippets:
        _assert_in_content("market-data", "README.md", snippet)

    body = _corpus_text("options/AAPL.json")
    _install_fake(monkeypatch, body)
    chain = yoghurt.Ticker("AAPL").options()
    assert len(chain.expiration_dates) > 1
    next_expiration = chain.expiration_dates[1]

    # Re-installed: the fake always returns the same canned body regardless
    # of the requested date, so this call proves the second request shape
    # (options(date=...)) round-trips through the same model, not that
    # Yahoo would return that specific expiration's contracts.
    _install_fake(monkeypatch, body)
    next_chain = yoghurt.Ticker("AAPL").options(date=next_expiration)
    assert next_chain.quote.symbol == "AAPL"


def test_fundamentals_readme_quote_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    """fundamentals/README.md: ``quote_summary(modules=[...])``."""

    snippet = (
        'summary = Ticker("AAPL").quote_summary('
        'modules=["price", "summaryDetail", "financialsTemplate"])'
    )
    _assert_in_content("fundamentals", "README.md", snippet)

    _install_fake(monkeypatch, _corpus_text("quote-summary/AAPL.json"))
    summary = Ticker("AAPL").quote_summary(
        modules=["price", "summaryDetail", "financialsTemplate"]
    )
    assert summary.price is not None
    assert summary.summary_detail is not None


def test_fundamentals_readme_timeseries(monkeypatch: pytest.MonkeyPatch) -> None:
    """fundamentals/README.md: ``timeseries()`` then ``.fundamentals.to_polars()``.

    Fixture: ``timeseries/AAPL.json`` is the default-args capture (no
    ``--type``), matching the snippet's own no-kwargs call exactly. Per
    AGENTS.md, the default ``type`` list covers earnings-release/analyst-
    rating/economic-event data, not fundamentals types, so the real,
    corpus-backed behavior for this exact call is an empty ``fundamentals``
    frame and a populated ``economic_events`` frame -- asserted below
    instead of a nonexistent nonempty-fundamentals claim.
    """

    snippets = [
        'data = Ticker("AAPL").timeseries()',
        "fundamentals = data.fundamentals.to_polars()",
    ]
    for snippet in snippets:
        _assert_in_content("fundamentals", "README.md", snippet)

    _install_fake(monkeypatch, _corpus_text("timeseries/AAPL.json"))
    data = Ticker("AAPL").timeseries()
    fundamentals = data.fundamentals.to_polars()
    assert fundamentals.height == 0
    assert data.economic_events.to_polars().height > 0


def test_analysis_readme_calendar_events(monkeypatch: pytest.MonkeyPatch) -> None:
    """analysis/README.md: ``calendar_events(modules=[...], start_date=..., ...)``.

    Stand-in fixture: no corpus capture exists for AAPL with this exact
    date window, so this test uses ``calendar-events/MSFT_earnings.json``
    (same ``modules=["earnings"]`` shape, a populated real window) as the
    canned body -- the fake client ignores request args entirely, so the
    behavioral claim under test is "an earnings-populated response
    validates and yields rows," not that this specific window matches.
    """

    snippet = (
        'events = Ticker("AAPL").calendar_events(\n'
        '    modules=["earnings"], start_date="2026-04-29", end_date="2026-04-30"\n'
        ")"
    )
    _assert_in_content("analysis", "README.md", snippet)

    _install_fake(monkeypatch, _corpus_text("calendar-events/MSFT_earnings.json"))
    events = Ticker("AAPL").calendar_events(
        modules=["earnings"], start_date="2026-04-29", end_date="2026-04-30"
    )
    assert events.earnings
    assert len(events.earnings) > 0


def test_analysis_readme_analyst_and_ratings_top(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """analysis/README.md: ``analyst()`` and ``ratings_top()``."""

    _assert_in_content("analysis", "README.md", 'analyst = Ticker("AAPL").analyst()')
    _assert_in_content("analysis", "README.md", 'top = Ticker("AAPL").ratings_top()')

    _install_fake(monkeypatch, _corpus_text("analyst/AAPL.json"))
    analyst = Ticker("AAPL").analyst()
    assert analyst is not None

    _install_fake(monkeypatch, _corpus_text("ratings-top/AAPL.json"))
    top = Ticker("AAPL").ratings_top()
    assert top is not None


def test_analysis_readme_recommendations(monkeypatch: pytest.MonkeyPatch) -> None:
    """analysis/README.md: ``recommendations()``."""

    snippet = 'related = Ticker("AAPL").recommendations()'
    _assert_in_content("analysis", "README.md", snippet)

    _install_fake(monkeypatch, _corpus_text("recommendations-by-symbol/AAPL.json"))
    related = Ticker("AAPL").recommendations()
    assert related.recommended_symbols


def test_analysis_readme_price_insights_and_insights(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """analysis/README.md: ``price_insights()`` and ``insights()``."""

    _assert_in_content(
        "analysis", "README.md", 'insights = Ticker("AAPL").price_insights()'
    )
    _assert_in_content("analysis", "README.md", 'research = Ticker("AAPL").insights()')

    _install_fake(monkeypatch, _corpus_text("price-insights/AAPL.json"))
    insights = Ticker("AAPL").price_insights()
    assert insights is not None

    _install_fake(monkeypatch, _corpus_text("insights/AAPL.json"))
    research = Ticker("AAPL").insights()
    assert research is not None


def test_dataframes_readme_conversion_vocabulary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """dataframes/README.md: the five ``Frame`` conversion methods.

    ``to_pandas()``/``to_arrow()`` need the optional ``pandas`` extra
    (absent from the base dev env, per ``tests/test_frames.py``'s own
    ``importorskip`` pattern, reused here) -- always/skip split matches
    that established convention rather than requiring the extra.
    """

    for snippet in (
        "frame.to_polars()",
        "frame.to_pandas()",
        "frame.to_arrow()",
        "frame.to_dicts()",
        'frame.save_parquet("tech.parquet")',
    ):
        _assert_in_content("dataframes", "README.md", snippet)

    _install_fake(monkeypatch, _corpus_text("screener/equity_us_tech.json"))
    frame = screener(
        "SELECT ticker, intradaymarketcap FROM EQUITY "
        "WHERE region = 'us' AND sector = 'Technology' "
        "ORDER BY intradaymarketcap DESC LIMIT 25"
    )
    assert frame.to_polars().height > 0
    assert frame.to_dicts()

    pytest.importorskip("pyarrow")
    assert frame.to_arrow().num_rows > 0


def test_dataframes_readme_chart_meta(monkeypatch: pytest.MonkeyPatch) -> None:
    """dataframes/README.md: ``Chart``'s ``.to_polars()``/``.meta`` pair."""

    for snippet in (
        'chart = yoghurt.Ticker("AAPL").chart(interval="1d")',
        "bars = chart.to_polars()",
        "meta = chart.meta",
    ):
        _assert_in_content("dataframes", "README.md", snippet)

    _install_fake(monkeypatch, _corpus_text("chart/AAPL.json"))
    chart = yoghurt.Ticker("AAPL").chart(interval="1d")
    bars = chart.to_polars()
    meta = chart.meta
    assert bars.height > 0
    assert meta is not None


def test_dataframes_readme_timeseries_frames(monkeypatch: pytest.MonkeyPatch) -> None:
    """dataframes/README.md: ``Timeseries``'s ``fundamentals``/``analyst_ratings``.

    Fixture: ``timeseries/AAPL_analystRatings.json`` is a surgical single-
    type capture requesting only ``analystRatings`` (see
    ``tests/fixtures/corpus/README.md``), so ``fundamentals`` is correctly
    empty here and ``analyst_ratings`` is the populated frame -- both
    checked explicitly rather than a vacuous ``>= 0``.
    """

    for snippet in (
        'data = yoghurt.Ticker("AAPL").timeseries()',
        "fundamentals_df = data.fundamentals.to_polars()",
        "ratings_df = data.analyst_ratings.to_polars()",
    ):
        _assert_in_content("dataframes", "README.md", snippet)

    _install_fake(monkeypatch, _corpus_text("timeseries/AAPL_analystRatings.json"))
    data = yoghurt.Ticker("AAPL").timeseries()
    fundamentals_df = data.fundamentals.to_polars()
    ratings_df = data.analyst_ratings.to_polars()
    assert fundamentals_df.height == 0
    assert ratings_df.height > 0


def test_queries_readme_visualization_insider_transaction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """queries/README.md: the ``visualization()`` INSIDER_TRANSACTION example."""

    snippet = (
        "insiders = yoghurt.visualization(\n"
        '    "SELECT ticker, transactiondate, shares "\n'
        "    \"FROM INSIDER_TRANSACTION WHERE ticker = 'AAPL' \"\n"
        '    "ORDER BY transactiondate DESC LIMIT 50"\n'
        ").to_polars()"
    )
    _assert_in_content("queries", "README.md", snippet)

    _install_fake(monkeypatch, _corpus_text("visualization/insider_transaction.json"))
    insiders = visualization(
        "SELECT ticker, transactiondate, shares "
        "FROM INSIDER_TRANSACTION WHERE ticker = 'AAPL' "
        "ORDER BY transactiondate DESC LIMIT 50"
    ).to_polars()
    assert insiders.height > 0


def test_queries_readme_visualization_splits(monkeypatch: pytest.MonkeyPatch) -> None:
    """queries/README.md: market-wide stock splits via ``visualization()``.

    Backed by ``visualization/splits.json``, a dedicated corpus fixture
    captured for this task (S1 review finding: no splits fixture existed;
    ``INSIDER_TRANSACTION``/``sp_earnings`` were structurally similar but
    not the same entity). See ``tests/fixtures/corpus/README.md`` for the
    capture note and ``tools/probe.py``'s ``_dsl_cases()`` for the
    permanent probe case.
    """

    snippet = (
        "splits = yoghurt.visualization(\n"
        '    "SELECT ticker, startdatetime FROM splits "\n'
        "    \"WHERE startdatetime BETWEEN '2026-05-09' AND '2026-05-16' LIMIT 25\"\n"
        ").to_polars()"
    )
    _assert_in_content("queries", "README.md", snippet)

    _install_fake(monkeypatch, _corpus_text("visualization/splits.json"))
    splits = visualization(
        "SELECT ticker, startdatetime FROM splits "
        "WHERE startdatetime BETWEEN '2026-05-09' AND '2026-05-16' LIMIT 25"
    ).to_polars()
    assert splits.height > 0
    assert "ticker" in splits.columns
    assert "startdatetime" in splits.columns


def test_queries_sharp_edges_splits_snippet(monkeypatch: pytest.MonkeyPatch) -> None:
    """queries/SHARP-EDGES.md's "right way" splits-by-ticker snippet."""

    snippet = (
        "splits = yoghurt.visualization(\n"
        "    \"SELECT ticker, startdatetime FROM splits WHERE ticker = 'AAPL' \"\n"
        '    "ORDER BY startdatetime DESC LIMIT 10"\n'
        ").to_polars()"
    )
    _assert_in_content("queries", "SHARP-EDGES.md", snippet)

    # Same entity as the README splits example; the ticker-filtered form is
    # pinned against the same dedicated splits fixture (the fake client
    # ignores query text, so behavior under test is "the splits entity
    # response shape flattens to a non-empty ticker/startdatetime frame,"
    # matching this snippet's claim regardless of the WHERE clause).
    _install_fake(monkeypatch, _corpus_text("visualization/splits.json"))
    splits = visualization(
        "SELECT ticker, startdatetime FROM splits WHERE ticker = 'AAPL' "
        "ORDER BY startdatetime DESC LIMIT 10"
    ).to_polars()
    assert splits.height > 0
    assert "ticker" in splits.columns


def test_fundamentals_sharp_edges_sp_earnings_release_events_snippet() -> None:
    """fundamentals/SHARP-EDGES.md's "wrong way" snippet: verbatim-only.

    This snippet demonstrates broken usage (a Yahoo-side malformed-JSON
    failure for ``spEarningsReleaseEvents``) -- it is pinned as text only,
    not executed, since the point is that it *should* raise rather than
    return usable data. ``tests/fixtures/corpus/README.md`` documents the
    permanent malformed-response evidence (``timeseries/AAPL_types_00.json``
    is kept as a non-parsing capture); the ``"malformed-response"``
    ``YahooApiError`` behavior itself is already pinned in
    ``tests/test_api_ticker.py`` and ``tests/test_core_envelope.py``.
    """

    snippet = (
        'Ticker("AAPL").timeseries('
        'type=["spEarningsReleaseEvents", "quarterlyTotalRevenue"])'
    )
    _assert_in_content("fundamentals", "SHARP-EDGES.md", snippet)


def test_skill_md_two_surfaces_chart_snippet(monkeypatch: pytest.MonkeyPatch) -> None:
    """SKILL.md's two-surfaces section: ``Ticker("^GSPC").chart(interval="1d")``."""

    snippet = 'yoghurt.Ticker("^GSPC").chart(interval="1d")'
    _assert_in_content(None, "SKILL.md", snippet)

    _install_fake(monkeypatch, _corpus_text("chart/_GSPC.json"))
    bars = yoghurt.Ticker("^GSPC").chart(interval="1d").to_polars()
    assert bars.height > 0
