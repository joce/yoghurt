"""Round-trip tests for typed batch c4 holder models against real captures.

The corpus coverage gate (``tests/models/test_summary_holders_corpus.py``)
proves every capture validates with no extras; these tests instead check
representative typed attributes: the RawFmt unwrap on insider position
fields, the mutually exclusive direct/indirect/summary position variants,
and the always-empty ``majorDirectHolders`` placeholder.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any

from yoghurt.models.summary_holders import (
    FundOwnership,
    InsiderHolders,
    InsiderTransactions,
    InstitutionOwnership,
    MajorDirectHolders,
    NetSharePurchaseActivity,
)

_CORPUS_QUOTE_SUMMARY_DIR = (
    Path(__file__).resolve().parent.parent / "fixtures" / "corpus" / "quote-summary"
)


def _load_module(filename: str, module: str) -> dict[str, Any]:
    payload = json.loads(
        (_CORPUS_QUOTE_SUMMARY_DIR / filename).read_text(encoding="utf-8")
    )
    result: dict[str, Any] = payload["quoteSummary"]["result"][0][module]
    return result


def test_insider_holders_unwraps_raw_fmt_wrapper_for_direct_position() -> None:
    """InsiderHolders unwraps {raw, fmt, longFmt} for the direct-position variant."""

    holders = InsiderHolders.model_validate(_load_module("AAPL.json", "insiderHolders"))

    first_holder = holders.holders[0]
    assert first_holder.position_direct is not None
    assert isinstance(first_holder.position_direct, int)
    assert first_holder.position_indirect is None
    assert first_holder.position_summary is None
    assert isinstance(first_holder.latest_trans_date, datetime.date)


def test_insider_holders_supports_indirect_and_summary_position_variants() -> None:
    """OKLO's holders exercise the position_indirect/position_summary variants."""

    holders = InsiderHolders.model_validate(_load_module("OKLO.json", "insiderHolders"))

    kinds = {
        "direct": 0,
        "indirect": 0,
        "summary": 0,
    }
    for holder in holders.holders:
        if holder.position_direct is not None:
            kinds["direct"] += 1
        if holder.position_indirect is not None:
            kinds["indirect"] += 1
        if holder.position_summary is not None:
            kinds["summary"] += 1

    assert kinds["indirect"] > 0
    assert kinds["summary"] > 0


def test_insider_transactions_value_is_optional() -> None:
    """insiderTransactions.transactions[].value is absent, not null, when unpriced."""

    transactions = InsiderTransactions.model_validate(
        _load_module("AAPL.json", "insiderTransactions")
    )

    missing_value = [t for t in transactions.transactions if t.value is None]
    present_value = [t for t in transactions.transactions if t.value is not None]
    assert missing_value
    assert present_value
    assert isinstance(present_value[0].value, int)


def test_institution_and_fund_ownership_share_the_same_row_type() -> None:
    """institutionOwnership/fundOwnership validate through the identical row type."""

    institution = InstitutionOwnership.model_validate(
        _load_module("AAPL.json", "institutionOwnership")
    )
    fund = FundOwnership.model_validate(_load_module("AAPL.json", "fundOwnership"))

    assert type(institution.ownership_list[0]) is type(fund.ownership_list[0])
    assert institution.ownership_list[0].pct_held > 0
    assert isinstance(institution.ownership_list[0].report_date, datetime.date)


def test_major_direct_holders_is_empty_placeholder() -> None:
    """majorDirectHolders.holders round-trips as an empty list."""

    holders = MajorDirectHolders.model_validate(
        _load_module("AAPL.json", "majorDirectHolders")
    )
    assert holders.holders == []


def test_net_share_purchase_activity_narrows_to_us_listed_equities() -> None:
    """The module's four US-only fields are absent on a foreign listing."""

    us_listed = NetSharePurchaseActivity.model_validate(
        _load_module("AAPL.json", "netSharePurchaseActivity")
    )
    foreign_listed = NetSharePurchaseActivity.model_validate(
        _load_module("SHEL.L.json", "netSharePurchaseActivity")
    )

    assert us_listed.buy_percent_insider_shares is not None
    assert us_listed.sell_info_shares is not None
    assert foreign_listed.buy_percent_insider_shares is None
    assert foreign_listed.sell_info_shares is None
    assert foreign_listed.sell_percent_insider_shares is None
    assert foreign_listed.net_percent_insider_shares is None
