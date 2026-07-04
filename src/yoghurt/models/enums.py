"""Enumerated types for Yahoo! Finance quote data.

``str, Enum`` rather than ``StrEnum``: the project floor is Python 3.10,
and ``enum.StrEnum`` only ships from 3.11 onward.
"""

from __future__ import annotations

from enum import Enum


class QuoteType(str, Enum):
    """Classification of financial instruments supported by Yahoo! Finance.

    Members: EQUITY, INDEX, OPTION, CURRENCY, CRYPTOCURRENCY, FUTURE, ETF,
    MUTUALFUND, and PRIVATE_COMPANY.
    """

    EQUITY = "EQUITY"
    INDEX = "INDEX"
    OPTION = "OPTION"
    CURRENCY = "CURRENCY"
    CRYPTOCURRENCY = "CRYPTOCURRENCY"
    FUTURE = "FUTURE"
    ETF = "ETF"
    MUTUALFUND = "MUTUALFUND"
    PRIVATE_COMPANY = "PRIVATE_COMPANY"


class MarketState(str, Enum):
    """Trading session phases for financial markets in Yahoo! Finance.

    PREPRE and POSTPOST bracket the wider extended-hours window; PRE runs
    weekdays roughly 4:00am-9:30am Eastern, REGULAR 9:30am-4:00pm Eastern,
    and POST 4:00pm-8:00pm Eastern, all excluding holidays. CLOSED covers
    everything else.
    """

    PREPRE = "PREPRE"
    PRE = "PRE"
    REGULAR = "REGULAR"
    POST = "POST"
    POSTPOST = "POSTPOST"
    CLOSED = "CLOSED"


class OptionType(str, Enum):
    """Classification of derivative contracts by the right they grant.

    Members: CALL (right to buy the underlying) and PUT (right to sell it).
    """

    CALL = "CALL"
    PUT = "PUT"


class PriceAlertConfidence(str, Enum):
    """Confidence level for Yahoo! Finance's internal price alert feature.

    Members: NONE (no confidence), LOW, and HIGH.
    """

    NONE = "NONE"
    LOW = "LOW"
    HIGH = "HIGH"
