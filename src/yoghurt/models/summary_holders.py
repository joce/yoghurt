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
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this entry fresh.

    Always ``1`` in this corpus.
    """

    name: str
    """
    Insider's full name, typically upper-case (for example ``"COOK TIMOTHY D"``).
    """

    position_direct: RawInt | None = None
    """
    Number of shares this insider holds directly.

    Wire value is a ``{raw, fmt, longFmt}`` wrapper when present. Mutually
    exclusive with ``position_indirect``/``position_summary`` on any given
    row; see the module docstring.
    """

    position_direct_date: RawDate | None = None
    """
    Date ``position_direct`` was last updated.

    Wire value is a ``{raw, fmt}`` wrapper when present, alongside
    ``position_direct``.
    """

    position_indirect: RawInt | None = None
    """
    Number of shares this insider holds indirectly (for example through a
    trust or entity).

    Wire value is a ``{raw, fmt, longFmt}`` wrapper when present. Mutually
    exclusive with ``position_direct``/``position_summary``; see the module
    docstring.
    """

    position_indirect_date: RawDate | None = None
    """
    Date ``position_indirect`` was last updated.

    Wire value is a ``{raw, fmt}`` wrapper when present, alongside
    ``position_indirect``.
    """

    position_summary: RawInt | None = None
    """
    Summary share count for this insider when Yahoo does not break the
    position into direct/indirect components.

    Wire value is a ``{raw, fmt, longFmt}`` wrapper when present. Mutually
    exclusive with ``position_direct``/``position_indirect``; see the
    module docstring.
    """

    position_summary_date: RawDate | None = None
    """
    Date ``position_summary`` was last updated.

    Wire value is a ``{raw, fmt}`` wrapper when present, alongside
    ``position_summary``.
    """

    relation: str
    """
    Insider's relationship to the company (for example ``"Chief Executive
    Officer"``, ``"Director"``).
    """

    transaction_description: str
    """
    Description of this insider's most recent reported transaction type
    (for example ``"Sale"``, ``"Stock Gift"``).
    """

    url: str
    """
    URL of additional filing detail for this insider.

    Always an empty string in this corpus.
    """


class InsiderHolders(YahooModel):
    """The ``insiderHolders`` module: current insider share positions."""

    holders: list[InsiderHolder]
    """
    Insider holder entries.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this module fresh.
    """


class InsiderTransaction(YahooModel):
    """One entry in the ``insiderTransactions`` module's ``transactions`` list."""

    filer_name: str
    """
    Name of the insider who filed this transaction.
    """

    filer_relation: str
    """
    Filer's relationship to the company (for example ``"Officer"``,
    ``"Director"``).
    """

    filer_url: str
    """
    URL of additional filing detail for this transaction.

    Always an empty string in this corpus.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this entry fresh.

    Always ``1`` in this corpus.
    """

    money_text: str
    """
    Free-text money description for this transaction.

    Always an empty string in this corpus.
    """

    ownership: str
    """
    Ownership form of this transaction (observed values: ``"D"`` direct,
    ``"I"`` indirect, ``"D/I"`` mixed).

    Three values observed across 581 corpus entries — a real but thin
    vocabulary, so this stays plain ``str``.
    """

    shares: RawInt
    """
    Number of shares involved in this transaction.

    Wire value is a ``{raw, fmt, longFmt}`` wrapper on every corpus entry
    (universal); see :mod:`yoghurt.models._base`.
    """

    start_date: RawDate
    """
    Date this transaction was recorded.

    Wire value is a ``{raw, fmt}`` wrapper on every corpus entry
    (universal).
    """

    transaction_text: str
    """
    Free-text description of this transaction (for example ``"Sale at
    price 295.14 per share."``); an empty string when Yahoo has no
    descriptive text to report.
    """

    value: RawInt | None = None
    """
    Total dollar value of this transaction.

    Wire value is a ``{raw, fmt, longFmt}`` wrapper when present. Absent
    (not merely ``{}``) on 169 of 581 corpus entries, for example
    transactions with no disclosed per-share price.
    """


class InsiderTransactions(YahooModel):
    """The ``insiderTransactions`` module: recent insider trading activity."""

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this module fresh.
    """

    transactions: list[InsiderTransaction]
    """
    Insider transaction entries, most recent first.
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
    """

    organization: str
    """
    Name of the institution or fund holding this position.
    """

    pct_change: RawFloat
    """
    Change in ``pct_held`` since the previous report.

    Wire value is a ``{raw, fmt}`` wrapper on every corpus entry
    (universal, never ``{}``); see :mod:`yoghurt.models._base`.
    """

    pct_held: RawFloat
    """
    Percentage of outstanding shares this position represents.

    Wire value is a ``{raw, fmt}`` wrapper on every corpus entry
    (universal, never ``{}``).
    """

    position: RawInt
    """
    Number of shares held.

    Wire value is a ``{raw, fmt, longFmt}`` wrapper on every corpus entry
    (universal, never ``{}``).
    """

    report_date: RawDate
    """
    Date this position was last reported.

    Wire value is a ``{raw, fmt}`` wrapper on every corpus entry
    (universal, never ``{}``).
    """

    value: RawInt
    """
    Dollar value of the position held.

    Wire value is a ``{raw, fmt, longFmt}`` wrapper on every corpus entry
    (universal, never ``{}``).
    """


class InstitutionOwnership(YahooModel):
    """The ``institutionOwnership`` module: institutional ownership positions."""

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this module fresh.
    """

    ownership_list: list[OwnershipEntry]
    """
    Institutional ownership position entries.
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
    """

    ownership_list: list[OwnershipEntry]
    """
    Fund ownership position entries.
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
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this module fresh.
    """


class MajorHoldersBreakdown(YahooModel):
    """The ``majorHoldersBreakdown`` module: aggregate ownership percentages."""

    insiders_percent_held: float
    """
    Percentage of outstanding shares held by company insiders.
    """

    institutions_count: int
    """
    Number of institutions reporting a position in this security.
    """

    institutions_float_percent_held: float
    """
    Percentage of the freely tradable float held by institutions.
    """

    institutions_percent_held: float
    """
    Percentage of outstanding shares held by institutions.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this module fresh.
    """


class NetSharePurchaseActivity(YahooModel):
    """The ``netSharePurchaseActivity`` module: aggregate insider buy/sell activity.

    Four fields narrow to the corpus's three US-listed EQUITY captures; see
    the module docstring.
    """

    buy_info_count: int
    """
    Number of insider buy transactions in ``period``.
    """

    buy_info_shares: int
    """
    Total shares bought by insiders in ``period``.
    """

    buy_percent_insider_shares: float | None = None
    """
    Shares bought as a percentage of total insider-held shares.

    Present only on the corpus's three US-listed captures (``AAPL``,
    ``MSFT``, ``OKLO``); see the module docstring.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this module fresh.
    """

    net_info_count: int
    """
    Net number of insider buy/sell transactions in ``period``.
    """

    net_info_shares: int
    """
    Net shares bought (or sold, if negative) by insiders in ``period``.
    """

    net_inst_buying_percent: float
    """
    Net institutional buying as a percentage of institutional holdings.
    """

    net_inst_shares_buying: int
    """
    Net shares bought by institutions.
    """

    net_percent_insider_shares: float | None = None
    """
    Net shares bought (or sold) as a percentage of total insider-held shares.

    Present only on the corpus's three US-listed captures (``AAPL``,
    ``MSFT``, ``OKLO``); see the module docstring.
    """

    period: str
    """
    Reporting window for this activity summary.

    Only ever observed as ``"6m"`` in this corpus — thin evidence, stays
    plain ``str``.
    """

    sell_info_count: int
    """
    Number of insider sell transactions in ``period``.
    """

    sell_info_shares: int | None = None
    """
    Total shares sold by insiders in ``period``.

    Present only on the corpus's three US-listed captures (``AAPL``,
    ``MSFT``, ``OKLO``); see the module docstring.
    """

    sell_percent_insider_shares: float | None = None
    """
    Shares sold as a percentage of total insider-held shares.

    Present only on the corpus's three US-listed captures (``AAPL``,
    ``MSFT``, ``OKLO``); see the module docstring.
    """

    total_insider_shares: int
    """
    Total number of shares held by insiders.
    """
