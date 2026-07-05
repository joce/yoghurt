"""Round-trip tests for typed batch c3 statement models against real captures.

The corpus coverage gate (``tests/models/test_summary_statements_corpus.py``)
proves every capture validates with no extras; these tests instead check
representative typed attributes: ``endDate`` unwrapping to a calendar date,
the balance-sheet module's corpus-wide line-item narrowing, and
0700.HK's ``{}``-heavy income-statement row (the fifteen
universal-but-always-``{}`` line items).
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any

from yoghurt.models.summary_statements import (
    BalanceSheetHistory,
    CashflowStatementHistory,
    IncomeStatement,
    IncomeStatementHistory,
    IncomeStatementHistoryQuarterly,
)

_CORPUS_QUOTE_SUMMARY_DIR = (
    Path(__file__).resolve().parent.parent / "fixtures" / "corpus" / "quote-summary"
)

_AAPL_TOTAL_REVENUE = 416161000000
_ZERO_SEVEN_ZERO_ZERO_HK_NET_INCOME = 224842000000


def _load_module(filename: str, module: str) -> dict[str, Any]:
    payload = json.loads(
        (_CORPUS_QUOTE_SUMMARY_DIR / filename).read_text(encoding="utf-8")
    )
    result: dict[str, Any] = payload["quoteSummary"]["result"][0][module]
    return result


def test_balance_sheet_history_rows_carry_only_end_date_and_max_age() -> None:
    """BalanceSheetHistory rows have no line items anywhere in this corpus.

    Documents the corpus-wide Yahoo API narrowing: BalanceSheetStatement
    has exactly two fields, and every AAPL row round-trips with just those.
    """

    history = BalanceSheetHistory.model_validate(
        _load_module("AAPL.json", "balanceSheetHistory")
    )

    first_statement = history.balance_sheet_statements[0]
    assert first_statement.end_date == datetime.date(2025, 9, 30)
    assert isinstance(first_statement.end_date, datetime.date)
    assert first_statement.max_age == 1


def test_cashflow_statement_history_rows_add_only_net_income() -> None:
    """CashflowStatementHistory rows add exactly one line item to endDate/maxAge."""

    history = CashflowStatementHistory.model_validate(
        _load_module("AAPL.json", "cashflowStatementHistory")
    )

    first_statement = history.cashflow_statements[0]
    assert first_statement.net_income is not None
    assert isinstance(first_statement.net_income, float)


def test_income_statement_history_unwraps_raw_fmt_wrapper_for_real_line_items() -> None:
    """IncomeStatementHistory unwraps {raw, fmt, longFmt} for populated fields."""

    history = IncomeStatementHistory.model_validate(
        _load_module("AAPL.json", "incomeStatementHistory")
    )

    first_statement = history.income_statement_history[0]
    assert first_statement.total_revenue == _AAPL_TOTAL_REVENUE
    assert isinstance(first_statement.total_revenue, float)
    assert first_statement.end_date == datetime.date(2025, 9, 30)


def test_income_statement_history_empty_wrappers_unwrap_to_none_for_0700_hk() -> None:
    """0700.HK's row unwraps {} to None on all fifteen always-empty line items.

    This is the batch's {}-evidence proof: these fifteen keys are present
    on every corpus row but never resolve to a real value anywhere,
    confirmed here against a real capture rather than just the corpus gate.
    """

    history = IncomeStatementHistory.model_validate(
        _load_module("0700.HK.json", "incomeStatementHistory")
    )

    first_statement = history.income_statement_history[0]
    assert first_statement.research_development is None
    assert first_statement.selling_general_administrative is None
    assert first_statement.non_recurring is None
    assert first_statement.other_operating_expenses is None
    assert first_statement.operating_income is None
    assert first_statement.total_other_income_expense_net is None
    assert first_statement.interest_expense is None
    assert first_statement.income_before_tax is None
    assert first_statement.minority_interest is None
    assert first_statement.net_income_from_continuing_ops is None
    assert first_statement.discontinued_operations is None
    assert first_statement.extraordinary_items is None
    assert first_statement.effect_of_accounting_charges is None
    assert first_statement.other_items is None
    assert first_statement.net_income_applicable_to_common_shares is None
    # netIncome is a sibling wrapped field that IS genuinely populated even
    # on this capture, proving {} isn't a blanket per-row failure mode.
    assert first_statement.net_income == _ZERO_SEVEN_ZERO_ZERO_HK_NET_INCOME


def test_income_statement_history_quarterly_shares_the_same_row_model() -> None:
    """The quarterly module validates through the identical IncomeStatement model.

    Proves the plan's one-row-model-per-statement-type reuse with a
    concrete instance check, complementing the corpus gate's exhaustive
    version of the same claim.
    """

    annual = IncomeStatementHistory.model_validate(
        _load_module("AAPL.json", "incomeStatementHistory")
    )
    quarterly = IncomeStatementHistoryQuarterly.model_validate(
        _load_module("AAPL.json", "incomeStatementHistoryQuarterly")
    )

    assert isinstance(annual.income_statement_history[0], IncomeStatement)
    assert isinstance(quarterly.income_statement_history[0], IncomeStatement)
    assert type(annual.income_statement_history[0]) is type(
        quarterly.income_statement_history[0]
    )
