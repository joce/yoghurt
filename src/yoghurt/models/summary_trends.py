"""Typed trend/filing models for the ``quote-summary`` endpoint.

Reconciled against the probe corpus at ``tests/fixtures/corpus/quote-summary/``
(23 valid captures across EQUITY, ETF, MUTUALFUND, CRYPTOCURRENCY, CURRENCY,
FUTURE, INDEX, and OPTION quoteTypes), captured 2026-07-04. Regenerate the
applicability evidence with
``uv run python -m tools.fields_report quote-summary:<module>`` after a
corpus refresh (see ``tools/fields_report.py`` for the generic per-module
stream this evidence is built from). This module covers the six trend/filing
modules of batch c3 (Part 3c plan): ``secFilings``, ``recommendationTrend``,
``upgradeDowngradeHistory``, ``indexTrend``, ``sectorTrend``, and
``industryTrend``. The six statement-history modules of the same batch live
in the sibling :mod:`yoghurt.models.summary_statements` (see that module's
docstring for the file-split rationale).

All captures that carry any of these six modules in this corpus are EQUITY
(the ETF/MUTUALFUND/INDEX/CURRENCY/FUTURE/CRYPTOCURRENCY/OPTION captures
carry none of them). ``recommendationTrend``/``indexTrend``/``sectorTrend``/
``industryTrend`` are universal across all 9 EQUITY captures;
``secFilings``/``upgradeDowngradeHistory`` are narrower (4 and 5 of the 9,
respectively — see the reconciliation notes).

Reconciliation notes:

- ``secFilings.filings[]`` (:class:`SecFiling`) entries carry a genuine
  epoch-vs-string date pair that always agree: ``epochDate`` (midnight-
  UTC-aligned on every one of the 432 corpus entries, verified individually
  — tier 1, typed ``datetime.date``) and ``date`` (a redundant bare ISO
  ``"YYYY-MM-DD"`` string that always matches ``epochDate``'s calendar
  date). Both are kept, as their own wire types, rather than collapsing to
  one: the plan's corpus-wins principle applies even to apparent
  redundancy. ``type`` has 38 distinct observed values across 432 entries
  (SEC form codes: ``"10-K"``, ``"10-Q"``, ``"8-K"``, and so on) — a real
  but very large and evidently open-ended vocabulary, so it stays plain
  ``str`` rather than an enum. Row-level ``maxAge`` is ``1`` on every entry.
- ``SecFiling.exhibits[]`` (:class:`SecFilingExhibit`) entries have a
  universal ``url`` and an optional ``downloadUrl`` (present on 103 of 1330
  exhibits in this corpus, always alongside ``type: "EXCEL"`` — Yahoo's
  Excel-format financial-report exhibits get a redirect-style download
  link that other exhibit types don't).
- ``recommendationTrend.trend[]`` rows (:class:`RecommendationTrendEntry`)
  are bare scalars throughout (no ``Raw*`` wrapper) — ``strongBuy``/
  ``buy``/``hold``/``sell``/``strongSell`` are plain ``int`` counts,
  universal on every one of the 30 corpus rows. ``period`` has only 4
  distinct observed values (``"0m"``, ``"-1m"``, ``"-2m"``, ``"-3m"``) —
  thin evidence, stays plain ``str``.
- ``upgradeDowngradeHistory.history[]`` rows (:class:`UpgradeDowngradeEntry`)
  are likewise all bare scalars, universal and non-null across all 2518
  corpus rows. ``epochGradeDate`` is a genuine epoch, but never midnight-
  aligned (verified against every one of the 2518 values) — tier 3,
  aware-UTC ``datetime.datetime``, unlike ``secFilings``'s calendar-date
  epoch. ``action`` (5 values: ``"down"``, ``"init"``, ``"main"``,
  ``"reit"``, ``"up"``) and ``priceTargetAction`` (7 values, including an
  observed empty string ``""`` — a real value, not a null) are both open
  vocabularies too thin to enumerate, so both stay plain ``str``.
- ``indexTrend``/``sectorTrend``/``industryTrend`` share one identical wire
  shape end to end (module-level ``maxAge``/``symbol``/``estimates[]``,
  and each ``estimates[]`` row's ``period``/``growth``) — the plan's
  one-concept rule applies, so all three modules reuse a single
  :class:`TrendEstimateGroup` model rather than three near-identical
  models. ``symbol`` is the required-but-nullable pattern: universal as a
  key (present on every one of the 27 module payloads across the 9
  captures) but only ever non-null on ``indexTrend`` (always
  ``"SP5"`` in this corpus); ``sectorTrend``/``industryTrend`` send
  ``symbol: null`` and an empty ``estimates: []`` on every single capture
  in this corpus — Yahoo appears to never populate sector/industry growth
  trends here, but the key shape itself is identical to ``indexTrend``'s,
  so the models stay shared rather than splitting into an
  always-empty-shaped sibling. ``TrendEstimate.period`` has 5 distinct
  observed values (``"0q"``, ``"+1q"``, ``"0y"``, ``"+1y"``, ``"LTG"``) —
  thin evidence, stays plain ``str``; ``growth`` is a bare ``float``,
  never a wrapper, whenever an estimate row is present at all.
"""

from __future__ import annotations

import datetime  # noqa: TC003 - pydantic needs this at runtime to resolve annotations

from yoghurt.models._base import YahooModel


class SecFilingExhibit(YahooModel):
    """One entry in a :class:`SecFiling`'s ``exhibits`` list."""

    download_url: str | None = None
    """
    Yahoo redirect URL for downloading this exhibit.

    Present on 103 of 1330 corpus exhibits, always alongside ``type:
    "EXCEL"`` (Yahoo's Excel-format financial-report exhibits).
    """

    type: str
    """
    Exhibit type or form code (for example ``"10-Q"``, ``"EX-31.1"``,
    ``"EXCEL"``).
    """

    url: str
    """
    URL of the exhibit document.
    """


class SecFiling(YahooModel):
    """One entry in the ``secFilings`` module's ``filings`` list."""

    date: datetime.date
    """
    Calendar date the filing was made, as a bare ISO ``"YYYY-MM-DD"``
    string.

    Always matches ``epoch_date``'s calendar date on every corpus entry
    (verified); a genuine redundant pair kept as their own wire types
    rather than collapsed into one, per the module docstring.
    """

    edgar_url: str
    """
    URL of the filing's Yahoo Finance SEC-filing page.
    """

    epoch_date: datetime.date
    """
    Calendar date the filing was made.

    Wire value is a midnight-UTC-aligned epoch timestamp in seconds
    (verified against every one of the 432 corpus entries); pydantic
    converts it to a UTC calendar date directly (tier 1 of the
    epoch-typing ruling) — a bare epoch, not a ``{raw, fmt}`` wrapper.
    """

    exhibits: list[SecFilingExhibit]
    """
    Documents attached to this filing.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this entry fresh.

    Always ``1`` in this corpus.
    """

    title: str
    """
    Human-readable description of the filing's purpose.
    """

    type: str
    """
    SEC form code for this filing (for example ``"10-K"``, ``"10-Q"``,
    ``"8-K"``).

    38 distinct values observed across 432 corpus entries — a real but
    open-ended vocabulary, so this stays plain ``str``.
    """


class SecFilings(YahooModel):
    """The ``secFilings`` module: SEC filing listings with exhibit links."""

    filings: list[SecFiling]
    """
    SEC filing entries, most recent first.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this module fresh.
    """


class RecommendationTrendEntry(YahooModel):
    """One period's row in the ``recommendationTrend`` module's ``trend`` list."""

    buy: int
    """
    Number of analysts rating this security "buy".
    """

    hold: int
    """
    Number of analysts rating this security "hold".
    """

    period: str
    """
    Relative-month label for this row (observed values: ``"0m"``,
    ``"-1m"``, ``"-2m"``, ``"-3m"``).

    Only four values observed, one of each per capture; not enough
    evidence for a closed vocabulary, so this stays plain ``str``.
    """

    sell: int
    """
    Number of analysts rating this security "sell".
    """

    strong_buy: int
    """
    Number of analysts rating this security "strong buy".
    """

    strong_sell: int
    """
    Number of analysts rating this security "strong sell".
    """


class RecommendationTrend(YahooModel):
    """The ``recommendationTrend`` module: analyst buy/hold/sell counts over time."""

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this module fresh.
    """

    trend: list[RecommendationTrendEntry]
    """
    Trailing monthly analyst-recommendation-count rows, most recent first.
    """


class UpgradeDowngradeEntry(YahooModel):
    """One entry in the ``upgradeDowngradeHistory`` module's ``history`` list."""

    action: str
    """
    Kind of ratings action (observed values: ``"down"``, ``"init"``,
    ``"main"``, ``"reit"``, ``"up"``).

    Five values observed across 2518 corpus entries — a real but thin
    vocabulary, so this stays plain ``str``.
    """

    current_price_target: float
    """
    Analyst's price target after this action.
    """

    epoch_grade_date: datetime.datetime
    """
    Date and time this ratings action was recorded.

    Session-anchored timestamp (never midnight-aligned, verified against
    every one of the 2518 corpus entries), typed as aware-UTC
    ``datetime.datetime`` per tier 3 of the epoch-typing ruling — a bare
    epoch, not a ``{raw, fmt}`` wrapper, and distinct from
    ``secFilings.filings[].epochDate``'s calendar-date alignment.
    """

    firm: str
    """
    Name of the analyst firm issuing this action.
    """

    from_grade: str
    """
    Rating grade prior to this action (for example ``"Outperform"``); an
    empty string when this is an initiating action with no prior grade.
    """

    price_target_action: str
    """
    Kind of price-target change (observed values: ``""``, ``"Adjusts"``,
    ``"Announces"``, ``"Lowers"``, ``"Maintains"``, ``"Raises"``,
    ``"Removes"``).

    The empty string is a real observed value (no price-target action
    accompanied this ratings action), not a null; seven values observed
    across 2518 corpus entries is thin evidence for a closed vocabulary,
    so this stays plain ``str``.
    """

    prior_price_target: float
    """
    Analyst's price target before this action (``0.0`` when there was no
    prior target).
    """

    to_grade: str
    """
    Rating grade assigned by this action (for example ``"Buy"``,
    ``"Hold"``, ``"Neutral"``).
    """


class UpgradeDowngradeHistory(YahooModel):
    """The ``upgradeDowngradeHistory`` module: analyst rating/price-target actions."""

    history: list[UpgradeDowngradeEntry]
    """
    Analyst ratings-action entries, most recent first.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this module fresh.
    """


class TrendEstimate(YahooModel):
    """One period's row in a :class:`TrendEstimateGroup`'s ``estimates`` list."""

    growth: float
    """
    Projected growth rate for this period.

    A bare ``float`` on every observed row, never a ``{raw, fmt}`` wrapper.
    """

    period: str
    """
    Relative period label for this row (observed values: ``"0q"``,
    ``"+1q"``, ``"0y"``, ``"+1y"``, ``"LTG"``).

    Five values observed, one of each per capture; not enough evidence for
    a closed vocabulary, so this stays plain ``str``.
    """


class TrendEstimateGroup(YahooModel):
    """The shared shape of the ``indexTrend``/``sectorTrend``/``industryTrend`` modules.

    All three modules share this exact wire shape end to end, per the
    plan's one-concept rule; see the module docstring for why
    ``sectorTrend``/``industryTrend`` still reuse it despite being
    always-empty in this corpus.
    """

    estimates: list[TrendEstimate]
    """
    Forward growth-rate estimates for this trend's benchmark, one per
    tracked period.

    Always empty on ``sectorTrend``/``industryTrend`` in this corpus (see
    the module docstring); populated with 5 entries on every ``indexTrend``
    capture.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this module fresh.
    """

    symbol: str | None
    """
    Ticker symbol of the benchmark this trend tracks (for example
    ``"SP5"``).

    Present on every capture in this corpus (``indexTrend``,
    ``sectorTrend``, ``industryTrend`` alike) but only ever non-null on
    ``indexTrend`` (always ``"SP5"``); required-but-nullable per the batch
    c1 precedent.
    """
