"""Typed holder/ownership models for the ``quote-summary`` endpoint.

Reconciled against the probe corpus at ``tests/fixtures/corpus/quote-summary/``
(23 valid captures across EQUITY, ETF, MUTUALFUND, CRYPTOCURRENCY, CURRENCY,
FUTURE, INDEX, and OPTION quoteTypes), captured 2026-07-04. Regenerate the
applicability evidence with
``uv run python -m tools.fields_report quote-summary:<module>`` after a
corpus refresh (see ``tools/fields_report.py`` for the generic per-module
stream this evidence is built from). This module covers seven of the ten
batch c4 modules (Part 3c plan): ``insiderHolders``, ``insiderTransactions``,
``institutionOwnership``, ``fundOwnership``, ``majorDirectHolders``,
``majorHoldersBreakdown``, and ``netSharePurchaseActivity``. The remaining
three (``fundProfile``, ``fundPerformance``, ``topHoldings``) live in the
sibling :mod:`yoghurt.models.summary_funds`, split by cohesion: this file's
seven modules are all EQUITY-only insider/institutional-ownership data,
while the sibling file's three are ETF/MUTUALFUND-only fund internals — two
genuinely disjoint quoteType domains that never co-occur in a single
capture, unlike any prior batch's file split.

All seven modules in this file are observed only on EQUITY captures (9 of
23) in this corpus; ``insiderTransactions`` is narrower still (7 of the 9
EQUITY captures — absent on ``BABA``/``BAC-PL``, non-US-domiciled/preferred
issues with apparently no reportable insider transactions in this window).

Reconciliation notes:

- ``insiderHolders.holders[]`` (:class:`InsiderHolder`) rows carry exactly
  one of three mutually exclusive position fields across this corpus's 9
  EQUITY captures: ``positionDirect``/``positionDirectDate`` (7 of 9
  captures), ``positionIndirect``/``positionIndirectDate`` (``OKLO``,
  ``RY.TO`` only), or ``positionSummary``/``positionSummaryDate`` (``OKLO``
  only, alongside a ``positionIndirect`` row in the same capture) — Yahoo
  reports whichever position type applies to that specific holder/filing,
  not a fixed per-symbol choice. All three pairs are modeled as optional
  ``RawInt``/``RawDate`` fields on the shared row rather than three
  separate row shapes, since every other field (``name``, ``relation``,
  ``url``, ``transactionDescription``, ``latestTransDate``, ``maxAge``) is
  universal across all three variants.
- ``insiderTransactions.transactions[]`` (:class:`InsiderTransaction``)
  rows are universal in every field except ``value`` (a ``{raw, fmt,
  longFmt}`` wrapper, present on 412 of 581 corpus entries — absent, not
  ``{}``, when Yahoo has no dollar value to report for a transaction, for
  example a same-day gift with no disclosed price). ``ownership`` has only
  three observed values (``"D"`` direct, ``"I"`` indirect, ``"D/I"`` mixed)
  — a real but thin vocabulary, so it stays plain ``str``.
  ``transactionText``/``moneyText``/``filerUrl`` are frequently empty
  strings (a real value, not a null) rather than absent.
- ``institutionOwnership``/``fundOwnership`` share an identical wire shape
  (:class:`OwnershipEntry`) — module-level ``maxAge`` plus an
  ``ownershipList[]`` of institution/fund position rows — verified
  field-for-field across every one of the 9 EQUITY captures that carry
  either; the only difference is which organizations Yahoo classifies into
  each list. Every ``OwnershipEntry`` field is universal and populated
  (``pctChange``/``pctHeld`` as ``RawFloat``, ``position``/``value`` as
  ``RawInt``, ``reportDate`` as ``RawDate``, all verified never ``{}`` in
  this corpus).
- ``majorDirectHolders.holders`` is an empty list on every one of the 9
  EQUITY captures that carry this module — a corpus-wide always-empty
  placeholder, not a per-symbol gap (unlike ``insiderHolders``, which is
  frequently populated). Modeled as an empty-only placeholder
  (:class:`MajorDirectHolder`), mirroring
  ``ExecutiveTeamMember``'s precedent in
  :mod:`yoghurt.models.summary_identity` for a field never observed
  populated.
- ``majorHoldersBreakdown`` is bare scalars throughout (no ``Raw*``
  wrapper), universal and non-null across all 9 EQUITY captures.
- ``netSharePurchaseActivity`` narrows for non-US-domiciled EQUITY
  captures: ``buyPercentInsiderShares``, ``netPercentInsiderShares``,
  ``sellInfoShares``, and ``sellPercentInsiderShares`` are present only on
  the corpus's three US-listed captures (``AAPL``, ``MSFT``, ``OKLO``) —
  absent, not null, on the other six (``0700.HK``, ``7203.T``, ``BABA``,
  ``BAC-PL``, ``RY.TO``, ``SHEL.L``). ``period`` has only ever been
  observed as ``"6m"`` (one value across all 9 captures) — thin evidence,
  stays plain ``str``, per the batch c2/c3 precedent for similarly small
  observed vocabularies.
"""

from __future__ import annotations

from yoghurt.models._base import RawDate, RawFloat, RawInt, YahooModel


class InsiderHolder(YahooModel):
    """One entry in the ``insiderHolders`` module's ``holders`` list.

    Carries exactly one of ``position_direct``/``position_indirect``/
    ``position_summary`` (each paired with its own ``*_date``) per row; see
    the module docstring for why all three stay optional fields on one
    shared row shape rather than three separate row models.
    """

    latest_trans_date: RawDate
    """
    Date of this insider's most recent reported transaction.

    Wire value is a ``{raw, fmt}`` wrapper on every corpus entry
    (universal); see :mod:`yoghurt.models._base`.

    Observed on: EQUITY summaries.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this entry fresh.

    Always ``1`` in this corpus.

    Observed on: EQUITY summaries.
    """

    name: str
    """
    Insider's full name, typically upper-case (for example ``"COOK TIMOTHY D"``).

    Observed on: EQUITY summaries.
    """

    position_direct: RawInt | None = None
    """
    Number of shares this insider holds directly.

    Wire value is a ``{raw, fmt, longFmt}`` wrapper when present. Mutually
    exclusive with ``position_indirect``/``position_summary`` on any given
    row; see the module docstring.

    Observed on: EQUITY summaries.
    """

    position_direct_date: RawDate | None = None
    """
    Date ``position_direct`` was last updated.

    Wire value is a ``{raw, fmt}`` wrapper when present, alongside
    ``position_direct``.

    Observed on: EQUITY summaries.
    """

    position_indirect: RawInt | None = None
    """
    Number of shares this insider holds indirectly (for example through a
    trust or entity).

    Wire value is a ``{raw, fmt, longFmt}`` wrapper when present. Mutually
    exclusive with ``position_direct``/``position_summary``; see the module
    docstring.

    Observed on: EQUITY summaries.
    """

    position_indirect_date: RawDate | None = None
    """
    Date ``position_indirect`` was last updated.

    Wire value is a ``{raw, fmt}`` wrapper when present, alongside
    ``position_indirect``.

    Observed on: EQUITY summaries.
    """

    position_summary: RawInt | None = None
    """
    Summary share count for this insider when Yahoo does not break the
    position into direct/indirect components.

    Wire value is a ``{raw, fmt, longFmt}`` wrapper when present. Mutually
    exclusive with ``position_direct``/``position_indirect``; see the
    module docstring.

    Observed on: EQUITY summaries.
    """

    position_summary_date: RawDate | None = None
    """
    Date ``position_summary`` was last updated.

    Wire value is a ``{raw, fmt}`` wrapper when present, alongside
    ``position_summary``.

    Observed on: EQUITY summaries.
    """

    relation: str
    """
    Insider's relationship to the company (for example ``"Chief Executive
    Officer"``, ``"Director"``).

    Observed on: EQUITY summaries.
    """

    transaction_description: str
    """
    Description of this insider's most recent reported transaction type
    (for example ``"Sale"``, ``"Stock Gift"``).

    Observed on: EQUITY summaries.
    """

    url: str
    """
    URL of additional filing detail for this insider.

    Always an empty string in this corpus.

    Observed on: EQUITY summaries.
    """


class InsiderHolders(YahooModel):
    """The ``insiderHolders`` module: current insider share positions."""

    holders: list[InsiderHolder]
    """
    Insider holder entries.

    Observed on: EQUITY summaries.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this module fresh.

    Observed on: EQUITY summaries.
    """


class InsiderTransaction(YahooModel):
    """One entry in the ``insiderTransactions`` module's ``transactions`` list."""

    filer_name: str
    """
    Name of the insider who filed this transaction.

    Observed on: EQUITY summaries.
    """

    filer_relation: str
    """
    Filer's relationship to the company (for example ``"Officer"``,
    ``"Director"``).

    Observed on: EQUITY summaries.
    """

    filer_url: str
    """
    URL of additional filing detail for this transaction.

    Always an empty string in this corpus.

    Observed on: EQUITY summaries.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this entry fresh.

    Always ``1`` in this corpus.

    Observed on: EQUITY summaries.
    """

    money_text: str
    """
    Free-text money description for this transaction.

    Always an empty string in this corpus.

    Observed on: EQUITY summaries.
    """

    ownership: str
    """
    Ownership form of this transaction (observed values: ``"D"`` direct,
    ``"I"`` indirect, ``"D/I"`` mixed).

    Three values observed across 581 corpus entries — a real but thin
    vocabulary, so this stays plain ``str``.

    Observed on: EQUITY summaries.
    """

    shares: RawInt
    """
    Number of shares involved in this transaction.

    Wire value is a ``{raw, fmt, longFmt}`` wrapper on every corpus entry
    (universal); see :mod:`yoghurt.models._base`.

    Observed on: EQUITY summaries.
    """

    start_date: RawDate
    """
    Date this transaction was recorded.

    Wire value is a ``{raw, fmt}`` wrapper on every corpus entry
    (universal).

    Observed on: EQUITY summaries.
    """

    transaction_text: str
    """
    Free-text description of this transaction (for example ``"Sale at
    price 295.14 per share."``); an empty string when Yahoo has no
    descriptive text to report.

    Observed on: EQUITY summaries.
    """

    value: RawInt | None = None
    """
    Total dollar value of this transaction.

    Wire value is a ``{raw, fmt, longFmt}`` wrapper when present. Absent
    (not merely ``{}``) on 169 of 581 corpus entries, for example
    transactions with no disclosed per-share price.

    Observed on: EQUITY summaries.
    """


class InsiderTransactions(YahooModel):
    """The ``insiderTransactions`` module: recent insider trading activity."""

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this module fresh.

    Observed on: EQUITY summaries.
    """

    transactions: list[InsiderTransaction]
    """
    Insider transaction entries, most recent first.

    Observed on: EQUITY summaries.
    """


class OwnershipEntry(YahooModel):
    """One entry in an ``institutionOwnership``/``fundOwnership`` ``ownershipList``.

    Shared by both modules, whose ``ownershipList`` validated against this
    identical shape with zero extras on every one of the 9 EQUITY corpus
    captures that carry either; see the module docstring.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this entry fresh.

    Always ``1`` in this corpus.

    Observed on: EQUITY summaries.
    """

    organization: str
    """
    Name of the institution or fund holding this position.

    Observed on: EQUITY summaries.
    """

    pct_change: RawFloat
    """
    Change in ``pct_held`` since the previous report.

    Wire value is a ``{raw, fmt}`` wrapper on every corpus entry
    (universal, never ``{}``); see :mod:`yoghurt.models._base`.

    Observed on: EQUITY summaries.
    """

    pct_held: RawFloat
    """
    Percentage of outstanding shares this position represents.

    Wire value is a ``{raw, fmt}`` wrapper on every corpus entry
    (universal, never ``{}``).

    Observed on: EQUITY summaries.
    """

    position: RawInt
    """
    Number of shares held.

    Wire value is a ``{raw, fmt, longFmt}`` wrapper on every corpus entry
    (universal, never ``{}``).

    Observed on: EQUITY summaries.
    """

    report_date: RawDate
    """
    Date this position was last reported.

    Wire value is a ``{raw, fmt}`` wrapper on every corpus entry
    (universal, never ``{}``).

    Observed on: EQUITY summaries.
    """

    value: RawInt
    """
    Dollar value of the position held.

    Wire value is a ``{raw, fmt, longFmt}`` wrapper on every corpus entry
    (universal, never ``{}``).

    Observed on: EQUITY summaries.
    """


class InstitutionOwnership(YahooModel):
    """The ``institutionOwnership`` module: institutional ownership positions."""

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this module fresh.

    Observed on: EQUITY summaries.
    """

    ownership_list: list[OwnershipEntry]
    """
    Institutional ownership position entries.

    Observed on: EQUITY summaries.
    """


class FundOwnership(YahooModel):
    """The ``fundOwnership`` module: mutual/index fund ownership positions.

    Field-for-field identical in shape to :class:`InstitutionOwnership` (see
    the module docstring); Yahoo classifies fund-family organizations here
    and other institutions there, not a shape difference.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this module fresh.

    Observed on: EQUITY summaries.
    """

    ownership_list: list[OwnershipEntry]
    """
    Fund ownership position entries.

    Observed on: EQUITY summaries.
    """


class MajorDirectHolder(YahooModel):
    """One entry in the ``majorDirectHolders`` module's ``holders`` list.

    Never observed populated in this corpus — every one of the 9 EQUITY
    captures that carry this module has an empty ``holders`` list; see the
    module docstring.

    Observed only as empty lists in the corpus.
    """


class MajorDirectHolders(YahooModel):
    """The ``majorDirectHolders`` module: direct major shareholders.

    ``holders`` is an empty list on every corpus capture; see
    :class:`MajorDirectHolder` and the module docstring.
    """

    holders: list[MajorDirectHolder]
    """
    Direct major shareholder entries.

    Always an empty list in this corpus.

    Observed on: EQUITY summaries.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this module fresh.

    Observed on: EQUITY summaries.
    """


class MajorHoldersBreakdown(YahooModel):
    """The ``majorHoldersBreakdown`` module: aggregate ownership percentages."""

    insiders_percent_held: float
    """
    Percentage of outstanding shares held by company insiders.

    Observed on: EQUITY summaries.
    """

    institutions_count: int
    """
    Number of institutions reporting a position in this security.

    Observed on: EQUITY summaries.
    """

    institutions_float_percent_held: float
    """
    Percentage of the freely tradable float held by institutions.

    Observed on: EQUITY summaries.
    """

    institutions_percent_held: float
    """
    Percentage of outstanding shares held by institutions.

    Observed on: EQUITY summaries.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this module fresh.

    Observed on: EQUITY summaries.
    """


class NetSharePurchaseActivity(YahooModel):
    """The ``netSharePurchaseActivity`` module: aggregate insider buy/sell activity.

    Four fields narrow to the corpus's three US-listed EQUITY captures; see
    the module docstring.
    """

    buy_info_count: int
    """
    Number of insider buy transactions in ``period``.

    Observed on: EQUITY summaries.
    """

    buy_info_shares: int
    """
    Total shares bought by insiders in ``period``.

    Observed on: EQUITY summaries.
    """

    buy_percent_insider_shares: float | None = None
    """
    Shares bought as a percentage of total insider-held shares.

    Present only on the corpus's three US-listed captures (``AAPL``,
    ``MSFT``, ``OKLO``); see the module docstring.

    Observed on: EQUITY summaries.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this module fresh.

    Observed on: EQUITY summaries.
    """

    net_info_count: int
    """
    Net number of insider buy/sell transactions in ``period``.

    Observed on: EQUITY summaries.
    """

    net_info_shares: int
    """
    Net shares bought (or sold, if negative) by insiders in ``period``.

    Observed on: EQUITY summaries.
    """

    net_inst_buying_percent: float
    """
    Net institutional buying as a percentage of institutional holdings.

    Observed on: EQUITY summaries.
    """

    net_inst_shares_buying: int
    """
    Net shares bought by institutions.

    Observed on: EQUITY summaries.
    """

    net_percent_insider_shares: float | None = None
    """
    Net shares bought (or sold) as a percentage of total insider-held shares.

    Present only on the corpus's three US-listed captures (``AAPL``,
    ``MSFT``, ``OKLO``); see the module docstring.

    Observed on: EQUITY summaries.
    """

    period: str
    """
    Reporting window for this activity summary.

    Only ever observed as ``"6m"`` in this corpus — thin evidence, stays
    plain ``str``.

    Observed on: EQUITY summaries.
    """

    sell_info_count: int
    """
    Number of insider sell transactions in ``period``.

    Observed on: EQUITY summaries.
    """

    sell_info_shares: int | None = None
    """
    Total shares sold by insiders in ``period``.

    Present only on the corpus's three US-listed captures (``AAPL``,
    ``MSFT``, ``OKLO``); see the module docstring.

    Observed on: EQUITY summaries.
    """

    sell_percent_insider_shares: float | None = None
    """
    Shares sold as a percentage of total insider-held shares.

    Present only on the corpus's three US-listed captures (``AAPL``,
    ``MSFT``, ``OKLO``); see the module docstring.

    Observed on: EQUITY summaries.
    """

    total_insider_shares: int
    """
    Total number of shares held by insiders.

    Observed on: EQUITY summaries.
    """
