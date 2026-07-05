"""Typed financial-statement models for the ``quote-summary`` endpoint.

Reconciled against the probe corpus at ``tests/fixtures/corpus/quote-summary/``
(23 valid captures across EQUITY, ETF, MUTUALFUND, CRYPTOCURRENCY, CURRENCY,
FUTURE, INDEX, and OPTION quoteTypes), captured 2026-07-04. Regenerate the
applicability evidence with
``uv run python -m tools.fields_report quote-summary:<module>`` after a
corpus refresh (see ``tools/fields_report.py`` for the generic per-module
stream this evidence is built from). This module covers the six
statement-history modules of batch c3 (Part 3c plan): ``balanceSheetHistory``,
``balanceSheetHistoryQuarterly``, ``cashflowStatementHistory``,
``cashflowStatementHistoryQuarterly``, ``incomeStatementHistory``, and
``incomeStatementHistoryQuarterly``. The remaining six batch c3 modules
(``secFilings``, ``recommendationTrend``, ``upgradeDowngradeHistory``,
``indexTrend``, ``sectorTrend``, ``industryTrend``) live in the sibling
:mod:`yoghurt.models.summary_trends`, split by cohesion (statement-shaped
rows here, trend/filing-shaped rows there) rather than by a line-count
overflow the way batch c2 split (this batch's combined size stays well under
that precedent).

All nine captures that carry any statement module in this corpus are EQUITY
(the ETF/MUTUALFUND/INDEX/CURRENCY/FUTURE/CRYPTOCURRENCY/OPTION captures
carry none of these six modules at all).

Per the plan's instruction to reuse one row model per statement type across
both cadences (the batch c2 ``EarningsModule``-reuse precedent):
:class:`BalanceSheetStatement` backs both ``balanceSheetHistory`` and
``balanceSheetHistoryQuarterly``; :class:`CashflowStatement` backs both
``cashflowStatementHistory`` and ``cashflowStatementHistoryQuarterly``;
:class:`IncomeStatement` backs both ``incomeStatementHistory`` and
``incomeStatementHistoryQuarterly``. Requiredness for each row model is
computed over the union of both cadences' rows (identical in every case
observed here: annual and quarterly rows carry exactly the same key set).

Reconciliation notes:

- ``balanceSheetHistory``/``balanceSheetHistoryQuarterly`` rows carry only
  ``endDate``/``maxAge`` in this entire corpus — no balance-sheet line item
  (``totalAssets``, ``totalLiabilities``, and so on) is present on any of
  the 71 rows across all 9 EQUITY captures. This is a genuine, corpus-wide
  Yahoo API narrowing of this endpoint (not a per-symbol gap), so
  :class:`BalanceSheetStatement` has exactly two fields.
- ``cashflowStatementHistory``/``cashflowStatementHistoryQuarterly`` rows add
  exactly one line item, ``netIncome``, atop the same ``endDate``/``maxAge``
  pair — every other cashflow line item (``totalCashFromOperatingActivities``,
  ``capitalExpenditures``, and so on) is likewise absent from every row in
  this corpus. ``netIncome`` is a genuine ``{raw, fmt, longFmt}`` wrapper,
  always populated with a real value (never observed as ``{}``), typed
  ``RawFloat``.
- ``incomeStatementHistory``/``incomeStatementHistoryQuarterly`` rows are the
  richest of the three: 24 keys, identical across both cadences and all 71
  rows. Seven line items (``costOfRevenue``, ``ebit``, ``grossProfit``,
  ``incomeTaxExpense``, ``netIncome``, ``totalOperatingExpenses``,
  ``totalRevenue``) are genuine ``{raw, fmt, longFmt}`` wrappers always
  carrying a real value (``RawFloat``, required). The remaining fifteen
  (``discontinuedOperations``, ``effectOfAccountingCharges``,
  ``extraordinaryItems``, ``incomeBeforeTax``, ``interestExpense``,
  ``minorityInterest``, ``netIncomeApplicableToCommonShares``,
  ``netIncomeFromContinuingOps``, ``nonRecurring``, ``operatingIncome``,
  ``otherItems``, ``otherOperatingExpenses``, ``researchDevelopment``,
  ``sellingGeneralAdministrative``, ``totalOtherIncomeExpenseNet``) are
  present as a key on every single row in this corpus but resolve to ``{}``
  (an empty wrapper, never a populated ``{raw, ...}``) on every one of
  them — a further symptom of the same Yahoo-side line-item narrowing seen
  on the balance-sheet module, just short of dropping the key outright. Per
  the required-but-nullable convention, these fifteen stay required
  (``RawFloatOrNone``, no default) since the *key* is universal even though
  its value never resolves non-``None`` anywhere in this corpus.
- ``endDate`` is a ``{raw, fmt}`` wrapper on every row of all six modules,
  verified midnight-UTC-aligned against every one of the 213 observed
  values (35+36 balance sheet, 35+36 cashflow, 35+36 income, all annual and
  quarterly rows) — tier 1 of the epoch-typing ruling, typed ``RawDate``.
- ``maxAge`` appears both at the module level (the whole module's freshness)
  and on every individual statement row (always ``1`` in this corpus,
  distinct from the module-level value, which varies); both are plain
  ``int``, matching the row/module ``max_age`` split seen throughout the
  quote-summary family.
"""

from __future__ import annotations

from yoghurt.models._base import RawDate, RawFloat, RawFloatOrNone, YahooModel


class BalanceSheetStatement(YahooModel):
    """One annual or quarterly row shared by both balance-sheet modules.

    Carries only ``endDate``/``maxAge`` in this corpus — no balance-sheet
    line item is present on any observed row (see the module docstring).
    """

    end_date: RawDate
    """
    Last calendar day of this statement's reporting period.

    Wire value is a ``{raw, fmt}`` wrapper with ``raw`` a midnight-UTC-
    aligned epoch timestamp in seconds (verified against every corpus
    value) and ``fmt`` a human-readable ``"YYYY-MM-DD"`` string.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this row fresh.

    Always ``1`` in this corpus, distinct from the module-level ``maxAge``.
    """


class CashflowStatement(YahooModel):
    """One annual or quarterly row shared by both cashflow-statement modules.

    Carries ``endDate``/``maxAge`` plus exactly one line item,
    ``netIncome`` — every other cashflow line item is absent from every
    observed row (see the module docstring).
    """

    end_date: RawDate
    """
    Last calendar day of this statement's reporting period.

    Wire value is a ``{raw, fmt}`` wrapper with ``raw`` a midnight-UTC-
    aligned epoch timestamp in seconds (verified against every corpus
    value) and ``fmt`` a human-readable ``"YYYY-MM-DD"`` string.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this row fresh.

    Always ``1`` in this corpus, distinct from the module-level ``maxAge``.
    """

    net_income: RawFloat
    """
    Net income for this statement's reporting period.

    Wire value is a ``{raw, fmt, longFmt}`` wrapper, always populated with a
    real value in this corpus (never observed as ``{}``).
    """


class IncomeStatement(YahooModel):
    """One annual or quarterly row shared by both income-statement modules.

    The richest of the three statement row shapes in this corpus (24 keys,
    identical across both cadences); fifteen of its line items are
    universal-but-always-``{}`` in this corpus (see the module docstring
    for the full reconciliation and which seven stay genuinely populated).
    """

    cost_of_revenue: RawFloat
    """
    Cost of goods and services sold during this period.

    Wire value is a ``{raw, fmt, longFmt}`` wrapper, always populated with a
    real value in this corpus.
    """

    discontinued_operations: RawFloatOrNone
    """
    Income or loss from discontinued operations.

    Wire value is a ``{}`` wrapper (unwraps to ``None``) on every row in
    this corpus; the key itself is universal, so this field stays required
    (no default) per the required-but-nullable convention — see the module
    docstring.
    """

    ebit: RawFloat
    """
    Earnings before interest and taxes.

    Wire value is a ``{raw, fmt, longFmt}`` wrapper, always populated with a
    real value in this corpus.
    """

    effect_of_accounting_charges: RawFloatOrNone
    """
    Impact of accounting-method changes on net income.

    Wire value is a ``{}`` wrapper (unwraps to ``None``) on every row in
    this corpus; required-but-nullable, see ``discontinued_operations``.
    """

    end_date: RawDate
    """
    Last calendar day of this statement's reporting period.

    Wire value is a ``{raw, fmt}`` wrapper with ``raw`` a midnight-UTC-
    aligned epoch timestamp in seconds (verified against every corpus
    value) and ``fmt`` a human-readable ``"YYYY-MM-DD"`` string.
    """

    extraordinary_items: RawFloatOrNone
    """
    Gains or losses from extraordinary, non-recurring events.

    Wire value is a ``{}`` wrapper (unwraps to ``None``) on every row in
    this corpus; required-but-nullable, see ``discontinued_operations``.
    """

    gross_profit: RawFloat
    """
    Total revenue minus cost of revenue for this period.

    Wire value is a ``{raw, fmt, longFmt}`` wrapper, always populated with a
    real value in this corpus.
    """

    income_before_tax: RawFloatOrNone
    """
    Pre-tax income for this period.

    Wire value is a ``{}`` wrapper (unwraps to ``None``) on every row in
    this corpus; required-but-nullable, see ``discontinued_operations``.
    """

    income_tax_expense: RawFloat
    """
    Income tax expense for this period.

    Wire value is a ``{raw, fmt, longFmt}`` wrapper, always populated with a
    real value in this corpus.
    """

    interest_expense: RawFloatOrNone
    """
    Interest expense for this period.

    Wire value is a ``{}`` wrapper (unwraps to ``None``) on every row in
    this corpus; required-but-nullable, see ``discontinued_operations``.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this row fresh.

    Always ``1`` in this corpus, distinct from the module-level ``maxAge``.
    """

    minority_interest: RawFloatOrNone
    """
    Portion of net income attributable to minority shareholders.

    Wire value is a ``{}`` wrapper (unwraps to ``None``) on every row in
    this corpus; required-but-nullable, see ``discontinued_operations``.
    """

    net_income: RawFloat
    """
    Net income for this statement's reporting period.

    Wire value is a ``{raw, fmt, longFmt}`` wrapper, always populated with a
    real value in this corpus.
    """

    net_income_applicable_to_common_shares: RawFloatOrNone
    """
    Net income attributable to common shareholders.

    Wire value is a ``{}`` wrapper (unwraps to ``None``) on every row in
    this corpus; required-but-nullable, see ``discontinued_operations``.
    """

    net_income_from_continuing_ops: RawFloatOrNone
    """
    Net income from continuing operations, excluding discontinued
    operations.

    Wire value is a ``{}`` wrapper (unwraps to ``None``) on every row in
    this corpus; required-but-nullable, see ``discontinued_operations``.
    """

    non_recurring: RawFloatOrNone
    """
    Non-recurring gains or losses for this period.

    Wire value is a ``{}`` wrapper (unwraps to ``None``) on every row in
    this corpus; required-but-nullable, see ``discontinued_operations``.
    """

    operating_income: RawFloatOrNone
    """
    Operating income for this period.

    Wire value is a ``{}`` wrapper (unwraps to ``None``) on every row in
    this corpus; required-but-nullable, see ``discontinued_operations``.
    """

    other_items: RawFloatOrNone
    """
    Other miscellaneous income-statement items.

    Wire value is a ``{}`` wrapper (unwraps to ``None``) on every row in
    this corpus; required-but-nullable, see ``discontinued_operations``.
    """

    other_operating_expenses: RawFloatOrNone
    """
    Operating expenses not broken out elsewhere on this statement.

    Wire value is a ``{}`` wrapper (unwraps to ``None``) on every row in
    this corpus; required-but-nullable, see ``discontinued_operations``.
    """

    research_development: RawFloatOrNone
    """
    Research and development expense for this period.

    Wire value is a ``{}`` wrapper (unwraps to ``None``) on every row in
    this corpus; required-but-nullable, see ``discontinued_operations``.
    """

    selling_general_administrative: RawFloatOrNone
    """
    Selling, general, and administrative expense for this period.

    Wire value is a ``{}`` wrapper (unwraps to ``None``) on every row in
    this corpus; required-but-nullable, see ``discontinued_operations``.
    """

    total_operating_expenses: RawFloat
    """
    Total operating expenses for this period.

    Wire value is a ``{raw, fmt, longFmt}`` wrapper, always populated with a
    real value in this corpus.
    """

    total_other_income_expense_net: RawFloatOrNone
    """
    Net of other, non-operating income and expense items.

    Wire value is a ``{}`` wrapper (unwraps to ``None``) on every row in
    this corpus; required-but-nullable, see ``discontinued_operations``.
    """

    total_revenue: RawFloat
    """
    Total revenue for this period.

    Wire value is a ``{raw, fmt, longFmt}`` wrapper, always populated with a
    real value in this corpus.
    """


class BalanceSheetHistory(YahooModel):
    """The ``balanceSheetHistory`` module: annual balance-sheet rows.

    Rows carry only ``end_date``/``max_age`` in this corpus — Yahoo does
    not populate balance-sheet line items here; see
    :class:`BalanceSheetStatement` and the module docstring.
    """

    balance_sheet_statements: list[BalanceSheetStatement]
    """
    Annual balance-sheet rows, most recent first.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this module fresh.
    """


class BalanceSheetHistoryQuarterly(YahooModel):
    """The ``balanceSheetHistoryQuarterly`` module: quarterly balance-sheet rows.

    Rows carry only ``end_date``/``max_age`` in this corpus — Yahoo does
    not populate balance-sheet line items here; see
    :class:`BalanceSheetStatement` and the module docstring.
    """

    balance_sheet_statements: list[BalanceSheetStatement]
    """
    Quarterly balance-sheet rows, most recent first.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this module fresh.
    """


class CashflowStatementHistory(YahooModel):
    """The ``cashflowStatementHistory`` module: annual cashflow-statement rows.

    Rows carry only ``end_date``/``max_age``/``net_income`` in this
    corpus — Yahoo does not populate other cashflow line items here; see
    :class:`CashflowStatement` and the module docstring.
    """

    cashflow_statements: list[CashflowStatement]
    """
    Annual cashflow-statement rows, most recent first.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this module fresh.
    """


class CashflowStatementHistoryQuarterly(YahooModel):
    """The ``cashflowStatementHistoryQuarterly`` module: quarterly cashflow rows.

    Rows carry only ``end_date``/``max_age``/``net_income`` in this
    corpus — Yahoo does not populate other cashflow line items here; see
    :class:`CashflowStatement` and the module docstring.
    """

    cashflow_statements: list[CashflowStatement]
    """
    Quarterly cashflow-statement rows, most recent first.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this module fresh.
    """


class IncomeStatementHistory(YahooModel):
    """The ``incomeStatementHistory`` module: annual income-statement rows."""

    income_statement_history: list[IncomeStatement]
    """
    Annual income-statement rows, most recent first.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this module fresh.
    """


class IncomeStatementHistoryQuarterly(YahooModel):
    """The ``incomeStatementHistoryQuarterly`` module: quarterly income rows."""

    income_statement_history: list[IncomeStatement]
    """
    Quarterly income-statement rows, most recent first.
    """

    max_age: int
    """
    Maximum age, in seconds, that Yahoo considers this module fresh.
    """
