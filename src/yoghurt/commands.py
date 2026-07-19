"""Yahoo Finance command metadata."""

from __future__ import annotations

from dataclasses import dataclass

from yoghurt.params import CHART_INTERVALS, CHART_RANGES, ParamKind, ParamSpec


@dataclass(frozen=True, slots=True)
class FieldReference:
    """Describe a known open-ended Yahoo parameter value."""

    name: str
    description: str


@dataclass(frozen=True, slots=True)
class ReferenceSection:
    """Describe a titled help reference section."""

    title: str
    values: tuple[FieldReference, ...]


@dataclass(frozen=True, slots=True)
class CommandSpec:
    """Describe one yoghurt command backed by a Yahoo Finance endpoint."""

    name: str
    path: str
    summary: str
    description: str
    params: tuple[ParamSpec, ...]
    examples: tuple[str, ...]
    field_reference: tuple[FieldReference, ...] = ()
    field_reference_title: str = "Quote --fields reference"
    reference_sections: tuple[ReferenceSection, ...] = ()
    common_modules: tuple[str, ...] = ()
    common_types: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    use_crumb: bool = True
    base_url: str = "https://query1.finance.yahoo.com"

    @property
    def yahoo_url(self) -> str:
        """Full Yahoo URL for this endpoint."""

        return f"{self.base_url}{self.path}"


def _prefixed_field_references(
    prefixes: tuple[FieldReference, ...],
    metrics: tuple[FieldReference, ...],
) -> tuple[FieldReference, ...]:
    """Return Yahoo timeseries type references with generated prefixes."""

    return tuple(
        FieldReference(
            f"{prefix.name}{metric.name}",
            f"{prefix.description} {metric.description}",
        )
        for prefix in prefixes
        for metric in metrics
    )


_TIMESERIES_EVENTS: tuple[FieldReference, ...] = (
    FieldReference("spEarningsReleaseEvents", "S&P earnings release events"),
    FieldReference("analystRatings", "analyst ratings"),
    FieldReference("economicEvents", "economic events"),
)

_TIMESERIES_ANNUAL_PREFIXES: tuple[FieldReference, ...] = (
    FieldReference("annual", "Annual"),
)

_TIMESERIES_QUARTERLY_TRAILING_PREFIXES: tuple[FieldReference, ...] = (
    FieldReference("quarterly", "Quarterly"),
    FieldReference("trailing", "Trailing"),
)

_TIMESERIES_VALUATION_METRICS: tuple[FieldReference, ...] = (
    FieldReference("MarketCap", "market capitalization"),
    FieldReference("EnterpriseValue", "enterprise value"),
    FieldReference("PeRatio", "P/E ratio"),
    FieldReference("ForwardPeRatio", "forward P/E ratio"),
    FieldReference("PegRatio", "PEG ratio"),
    FieldReference("PsRatio", "price to sales ratio"),
    FieldReference("PbRatio", "price to book ratio"),
    FieldReference("EnterprisesValueRevenueRatio", "enterprise value to revenue"),
    FieldReference("EnterprisesValueEBITDARatio", "enterprise value to EBITDA"),
)

_TIMESERIES_ANNUAL_METRICS: tuple[FieldReference, ...] = (
    FieldReference("InterestExpense", "interest expense"),
    FieldReference("OtherIncomeExpense", "other income or expense"),
    FieldReference("OperatingCashFlow", "operating cash flow"),
    FieldReference("PurchaseOfInvestment", "investment purchases"),
    FieldReference("EndCashPosition", "ending cash position"),
    FieldReference("BeginningCashPosition", "beginning cash position"),
    FieldReference("NetOtherFinancingCharges", "net other financing charges"),
    FieldReference("RepurchaseOfCapitalStock", "capital stock repurchases"),
    FieldReference("RepaymentOfDebt", "debt repayments"),
    FieldReference("SaleOfInvestment", "investment sales"),
    FieldReference("PurchaseOfBusiness", "business purchases"),
    FieldReference("OtherNonCashItems", "other non-cash items"),
    FieldReference("FreeCashFlow", "free cash flow"),
    FieldReference("AccountsPayable", "accounts payable"),
    FieldReference("StockBasedCompensation", "stock-based compensation"),
    FieldReference("DeferredIncomeTax", "deferred income tax"),
    FieldReference("ChangeInWorkingCapital", "change in working capital"),
    FieldReference("CostOfRevenue", "cost of revenue"),
    FieldReference("EBITDA", "EBITDA"),
    FieldReference("NormalizedEBITDA", "normalized EBITDA"),
    FieldReference("OperatingIncome", "operating income"),
    FieldReference("StockholdersEquity", "stockholders' equity"),
    FieldReference("CurrentLiabilities", "current liabilities"),
    FieldReference(
        "TotalLiabilitiesNetMinorityInterest",
        "total liabilities net minority interest",
    ),
    FieldReference("CurrentAssets", "current assets"),
    FieldReference("TotalAssets", "total assets"),
    FieldReference("ChangesInAccountReceivables", "changes in account receivables"),
    FieldReference("CapitalExpenditure", "capital expenditure"),
    FieldReference("NetOtherInvestingChanges", "net other investing changes"),
    FieldReference(
        "CashFlowFromContinuingFinancingActivities",
        "cash flow from continuing financing activities",
    ),
    FieldReference(
        "ChangeInCashSupplementalAsReported",
        "supplemental change in cash as reported",
    ),
    FieldReference("DepreciationAndAmortization", "depreciation and amortization"),
    FieldReference("ChangeInInventory", "change in inventory"),
    FieldReference("InvestingCashFlow", "investing cash flow"),
    FieldReference("CommonStockIssuance", "common stock issuance"),
    FieldReference("CashDividendsPaid", "cash dividends paid"),
    FieldReference("ChangeInAccountPayable", "change in account payable"),
    FieldReference("SpecialIncomeCharges", "special income charges"),
    FieldReference("OtherSpecialCharges", "other special charges"),
    FieldReference(
        "RestructuringAndMergernAcquisition",
        "restructuring and merger or acquisition charges",
    ),
    FieldReference("ImpairmentOfCapitalAssets", "impairment of capital assets"),
    FieldReference("WriteOff", "write-off charges"),
    FieldReference("SellingAndMarketingExpense", "selling and marketing expense"),
    FieldReference("NetIncome", "net income"),
    FieldReference("TotalRevenue", "total revenue"),
    FieldReference("GrossProfit", "gross profit"),
    FieldReference("OperatingExpense", "operating expense"),
    FieldReference("ResearchAndDevelopment", "research and development expense"),
    FieldReference(
        "SellingGeneralAndAdministration",
        "selling, general, and administrative expense",
    ),
    FieldReference("PretaxIncome", "pretax income"),
    FieldReference("TaxProvision", "tax provision"),
    FieldReference("BasicEPS", "basic EPS"),
    FieldReference("DilutedEPS", "diluted EPS"),
    FieldReference("BasicAverageShares", "basic average shares"),
    FieldReference("DilutedAverageShares", "diluted average shares"),
    FieldReference(
        "NetIncomeContinuousOperations", "net income from continuing operations"
    ),
    FieldReference("CapitalLeaseObligations", "capital lease obligations"),
    FieldReference("TotalDebt", "total debt"),
    FieldReference("NetDebt", "net debt"),
    FieldReference(
        "GoodwillAndOtherIntangibleAssets",
        "goodwill and other intangible assets",
    ),
    FieldReference("Goodwill", "goodwill"),
    FieldReference("AccountsReceivable", "accounts receivable"),
    FieldReference("Inventory", "inventory"),
    FieldReference(
        "CashCashEquivalentsAndShortTermInvestments",
        "cash, cash equivalents, and short-term investments",
    ),
    FieldReference("LongTermDebt", "long-term debt"),
    FieldReference("NetPPE", "net property, plant, and equipment"),
    FieldReference("TotalNonCurrentAssets", "total non-current assets"),
    FieldReference(
        "TotalNonCurrentLiabilitiesNetMinorityInterest",
        "total non-current liabilities net minority interest",
    ),
    FieldReference("InvestedCapital", "invested capital"),
    FieldReference("WorkingCapital", "working capital"),
    FieldReference("TangibleBookValue", "tangible book value"),
)

_TIMESERIES_QUARTERLY_TRAILING_METRICS: tuple[FieldReference, ...] = (
    FieldReference("TotalRevenue", "total revenue"),
    FieldReference("NetIncome", "net income"),
    FieldReference("CostOfRevenue", "cost of revenue"),
    FieldReference("GrossProfit", "gross profit"),
    FieldReference("OperatingIncome", "operating income"),
    FieldReference("InterestExpense", "interest expense"),
    FieldReference("BasicEPS", "basic EPS"),
    FieldReference("DilutedEPS", "diluted EPS"),
    FieldReference("EBITDA", "EBITDA"),
    FieldReference("OperatingExpense", "operating expense"),
    FieldReference("PretaxIncome", "pretax income"),
    FieldReference("TaxProvision", "tax provision"),
    FieldReference("BasicAverageShares", "basic average shares"),
    FieldReference("DilutedAverageShares", "diluted average shares"),
    FieldReference("OtherIncomeExpense", "other income or expense"),
    FieldReference(
        "NetIncomeContinuousOperations", "net income from continuing operations"
    ),
    FieldReference("NormalizedEBITDA", "normalized EBITDA"),
    FieldReference("SellingAndMarketingExpense", "selling and marketing expense"),
    FieldReference(
        "SellingGeneralAndAdministration",
        "selling, general, and administrative expense",
    ),
    FieldReference("ResearchAndDevelopment", "research and development expense"),
)

TIMESERIES_TYPE_REFERENCES: tuple[FieldReference, ...] = (
    *_TIMESERIES_EVENTS,
    *_prefixed_field_references(
        _TIMESERIES_QUARTERLY_TRAILING_PREFIXES,
        _TIMESERIES_VALUATION_METRICS,
    ),
    *_prefixed_field_references(
        _TIMESERIES_ANNUAL_PREFIXES, _TIMESERIES_ANNUAL_METRICS
    ),
    *_prefixed_field_references(
        _TIMESERIES_QUARTERLY_TRAILING_PREFIXES,
        _TIMESERIES_QUARTERLY_TRAILING_METRICS,
    ),
)


QUOTE_FIELDS: tuple[FieldReference, ...] = (
    FieldReference(
        "ask", "Lowest price a seller is willing to accept for the security."
    ),
    FieldReference("askSize", "Number of units available at current ask price."),
    FieldReference(
        "averageAnalystRating",
        "Consensus rating from financial analysts for the quote.",
    ),
    FieldReference(
        "averageDailyVolume10Day",
        "Average number of shares traded each day over the last 10 days.",
    ),
    FieldReference(
        "averageDailyVolume3Month",
        "Average number of shares traded each day over the last 3 months.",
    ),
    FieldReference("bid", "Highest price a buyer is willing to pay for the security."),
    FieldReference(
        "bidSize", "Total number of shares that buyers want to buy at the bid price."
    ),
    FieldReference("bookValue", "Net accounting value of a company's assets."),
    FieldReference(
        "circulatingSupply",
        "Number of cryptocurrency units currently in public circulation.",
    ),
    FieldReference("coinImageUrl", "URL of the image representing the cryptocurrency."),
    FieldReference(
        "coinMarketCapLink", "URL of the MarketCap site for the cryptocurrency."
    ),
    FieldReference("contractSymbol", "Ticker symbol for a futures contract."),
    FieldReference("cryptoTradeable", "Whether the cryptocurrency can be traded."),
    FieldReference(
        "customPriceAlertConfidence", "Undocumented Yahoo price alert confidence value."
    ),
    FieldReference("currency", "Currency in which the security is traded."),
    FieldReference("displayName", "User-friendly name of the quote or security."),
    FieldReference(
        "dividendDate", "Date when the company is expected to pay its next dividend."
    ),
    FieldReference("dividendRate", "Amount of dividends expected over the next year."),
    FieldReference(
        "dividendYield",
        "Annual dividend as a percentage of the security's current price.",
    ),
    FieldReference(
        "earningsTimestamp", "Raw timestamp for the company's earnings announcement."
    ),
    FieldReference(
        "earningsTimestampEnd",
        "Raw timestamp for the end of the earnings announcement window.",
    ),
    FieldReference(
        "earningsTimestampStart",
        "Raw timestamp for the start of the earnings announcement window.",
    ),
    FieldReference(
        "epsCurrentYear", "Company's earnings per share for the current year."
    ),
    FieldReference(
        "epsForward", "Company's projected earnings per share for the next fiscal year."
    ),
    FieldReference(
        "epsTrailingTwelveMonths",
        "Company's earnings per share for the past 12 months.",
    ),
    FieldReference("esgPopulated", "Availability status of ESG ratings data."),
    FieldReference("exchange", "Securities exchange on which the security is traded."),
    FieldReference(
        "exchangeDataDelayedBy",
        "Delay in data from the exchange, typically in minutes.",
    ),
    FieldReference("exchangeTimezoneName", "Name of the exchange timezone."),
    FieldReference("exchangeTimezoneShortName", "Short name of the exchange timezone."),
    FieldReference(
        "extendedMarketChange", "Change in the extended-hours market price."
    ),
    FieldReference(
        "extendedMarketChangePercent",
        "Percent change in the extended-hours market price.",
    ),
    FieldReference("extendedMarketPrice", "Latest price from extended-hours trading."),
    FieldReference(
        "extendedMarketTime",
        "Raw timestamp of the most recent extended-hours price.",
    ),
    FieldReference("expireDate", "Date on which the option contract expires."),
    FieldReference("expireIsoDate", "Option expiration date in ISO 8601 format."),
    FieldReference(
        "fiftyDayAverage", "Average closing price over the past 50 trading days."
    ),
    FieldReference(
        "fiftyDayAverageChange",
        "Change in the 50-day average price from the previous trading day.",
    ),
    FieldReference(
        "fiftyDayAverageChangePercent",
        "Percent change in the 50-day average price from the previous trading day.",
    ),
    FieldReference(
        "fiftyTwoWeekChangePercent",
        "Percentage change in price over the past 52 weeks.",
    ),
    FieldReference("fiftyTwoWeekHigh", "Highest price traded over the past 52 weeks."),
    FieldReference(
        "fiftyTwoWeekHighChange",
        "Change in the 52-week high price from the previous trading day.",
    ),
    FieldReference(
        "fiftyTwoWeekHighChangePercent",
        "Percent change in the 52-week high price from the previous trading day.",
    ),
    FieldReference("fiftyTwoWeekLow", "Lowest price traded over the past 52 weeks."),
    FieldReference(
        "fiftyTwoWeekLowChange",
        "Change in the 52-week low price from the previous trading day.",
    ),
    FieldReference(
        "fiftyTwoWeekLowChangePercent",
        "Percent change in the 52-week low price from the previous trading day.",
    ),
    FieldReference("fiftyTwoWeekRange", "Trading price range over the past 52 weeks."),
    FieldReference(
        "financialCurrency", "Currency in which the company reports financial results."
    ),
    FieldReference(
        "firstTradeDateMilliseconds", "Raw first-trade timestamp in milliseconds."
    ),
    FieldReference(
        "forwardPe", "Projected price-to-earnings ratio for the next 12 months."
    ),
    FieldReference("fromCurrency", "Base currency in an exchange pair."),
    FieldReference(
        "fromExchange", "Source exchange for a currency or conversion pair."
    ),
    FieldReference("fullExchangeName", "Full name of the securities exchange."),
    FieldReference(
        "gmtOffSetMilliseconds", "Exchange offset from GMT in milliseconds."
    ),
    FieldReference(
        "headSymbolAsString", "Symbol of the contract's underlying security."
    ),
    FieldReference("ipoExpectedDate", "Expected date of the initial public offering."),
    FieldReference("language", "Language in which financial results are reported."),
    FieldReference("lastMarket", "Last market in which the security was traded."),
    FieldReference(
        "companyLogoUrl", "URL of the company's logo in Yahoo quote responses."
    ),
    FieldReference("logoUrl", "URL of the company's logo."),
    FieldReference("longName", "Official name of the company or security."),
    FieldReference("market", "Primary market for the security."),
    FieldReference(
        "marketCap", "Total market value of the security in trading currency."
    ),
    FieldReference("marketState", "Current state of the market for the security."),
    FieldReference("messageBoardId", "Identifier for the Yahoo Finance message board."),
    FieldReference(
        "morningstarIndustry",
        "Morningstar industry classification when Yahoo returns it.",
    ),
    FieldReference(
        "nameChangeDate", "Date on which the company last changed its name."
    ),
    FieldReference("netAssets", "Total net assets of the fund or company."),
    FieldReference("netExpenseRatio", "Ratio of total expenses to total net assets."),
    FieldReference(
        "openInterest", "Total number of open futures or options contracts."
    ),
    FieldReference(
        "optionsType", "Yahoo option-type metadata returned by quote-page requests."
    ),
    FieldReference("optionType", "Type of option."),
    FieldReference("overnightMarketChange", "Change in the overnight-market price."),
    FieldReference(
        "overnightMarketChangePercent",
        "Percent change in the overnight-market price.",
    ),
    FieldReference("overnightMarketPrice", "Latest overnight-market price."),
    FieldReference(
        "overnightMarketTime",
        "Raw timestamp of the most recent overnight-market price.",
    ),
    FieldReference("postMarketChange", "Change in the security's post-market price."),
    FieldReference(
        "postMarketChangePercent", "Percent change in the security's post-market price."
    ),
    FieldReference("postMarketPrice", "Price of the security in post-market trading."),
    FieldReference(
        "postMarketTime", "Raw timestamp of the most recent post-market trade."
    ),
    FieldReference("preMarketChange", "Change in the security's pre-market price."),
    FieldReference(
        "preMarketChangePercent", "Percent change in the security's pre-market price."
    ),
    FieldReference("preMarketPrice", "Price of the security in pre-market trading."),
    FieldReference(
        "preMarketTime", "Raw timestamp of the most recent pre-market trade."
    ),
    FieldReference("prevName", "Company name before its most recent name change."),
    FieldReference("priceEpsCurrentYear", "Current-year price-to-earnings ratio."),
    FieldReference("priceHint", "Decimal precision indicator for price values."),
    FieldReference("priceToBook", "Market value relative to book value per share."),
    FieldReference("quartrId", "Yahoo Quartr identifier when quote pages request it."),
    FieldReference("quoteSourceName", "Name of the source providing the quote."),
    FieldReference("quoteType", "Type of quote."),
    FieldReference("region", "Region in which the company or security is located."),
    FieldReference(
        "regularMarketChange", "Change in the security's regular-market price."
    ),
    FieldReference(
        "regularMarketChangePercent",
        "Percent change in the security's regular-market price.",
    ),
    FieldReference(
        "regularMarketDayHigh", "Highest price during the regular trading session."
    ),
    FieldReference(
        "regularMarketDayLow", "Lowest price during the regular trading session."
    ),
    FieldReference(
        "regularMarketDayRange", "Price range during the regular trading session."
    ),
    FieldReference(
        "regularMarketOpen", "Opening price for the regular trading session."
    ),
    FieldReference(
        "regularMarketPreviousClose", "Previous regular-session closing price."
    ),
    FieldReference(
        "regularMarketPrice", "Latest price from the regular trading session."
    ),
    FieldReference("regularMarketSource", "Source label for the regular-market quote."),
    FieldReference(
        "regularMarketTime", "Raw timestamp of the most recent regular-session trade."
    ),
    FieldReference(
        "regularMarketVolume", "Number of units traded in the regular session."
    ),
    FieldReference(
        "sharesOutstanding", "Number of shares currently held by shareholders."
    ),
    FieldReference("shortName", "Short user-friendly name for the quote or security."),
    FieldReference(
        "sourceInterval",
        "Interval at which the data source provides updates, in seconds.",
    ),
    FieldReference("startDate", "Date on which the coin started trading."),
    FieldReference("stockStory", "Yahoo StockStory metadata when returned."),
    FieldReference("strike", "Contractually specified price for options exercise."),
    FieldReference("symbol", "Ticker symbol of the security."),
    FieldReference("toCurrency", "Counter currency in an exchange pair."),
    FieldReference(
        "toExchange", "Destination exchange for a currency or conversion pair."
    ),
    FieldReference("tradeable", "Whether the security is currently tradeable."),
    FieldReference(
        "trailingAnnualDividendRate",
        "Dividend payment per share over the past 12 months.",
    ),
    FieldReference(
        "trailingAnnualDividendYield", "Dividend yield over the past 12 months."
    ),
    FieldReference(
        "trailingPE",
        "Trailing price-to-earnings ratio based on past twelve-month results.",
    ),
    FieldReference(
        "trailingThreeMonthNavReturns", "Trailing three-month net asset value returns."
    ),
    FieldReference("trailingThreeMonthReturns", "Trailing three-month returns."),
    FieldReference(
        "triggerable", "Internal Yahoo Finance flag with undocumented purpose."
    ),
    FieldReference(
        "twoHundredDayAverage", "Average closing price over the past 200 trading days."
    ),
    FieldReference(
        "twoHundredDayAverageChange",
        "Change in the 200-day average price from the previous trading day.",
    ),
    FieldReference(
        "twoHundredDayAverageChangePercent",
        "Percent change in the 200-day average price from the previous trading day.",
    ),
    FieldReference("typeDisp", "User-friendly representation of the quote type."),
    FieldReference(
        "underlyingExchangeSymbol",
        "Exchange symbol for the underlying asset's trading venue.",
    ),
    FieldReference(
        "underlyingShortName", "Short name of the underlying derivative security."
    ),
    FieldReference(
        "underlyingSymbol", "Ticker symbol of the underlying derivative security."
    ),
    FieldReference(
        "volume24Hr", "Total cryptocurrency trading volume in the past 24 hours."
    ),
    FieldReference(
        "volumeAllCurrencies",
        "Aggregate 24-hour cryptocurrency volume across currency pairs.",
    ),
    FieldReference("ytdReturn", "Year-to-date return on the security."),
)


QUOTE_COMMAND = CommandSpec(
    name="quote",
    path="/v7/finance/quote",
    summary="Fetch quotes for one or more symbols.",
    description=(
        "Prices, trading state, identity, market data, and optional --fields "
        "extras for up to 10 symbols in a single call."
    ),
    use_crumb=True,
    params=(
        ParamSpec(
            name="symbols",
            cli_name="symbols",
            kind=ParamKind.CSV,
            positional=True,
            required=True,
            metavar="SYMBOL[,SYMBOL...]",
            min_items=1,
            max_items=10,
            help=(
                "1 to 10 comma-separated Yahoo symbols, such as AAPL,MSFT or SHOP.TO."
            ),
        ),
        ParamSpec(
            name="fields",
            cli_name="fields",
            kind=ParamKind.CSV,
            metavar="FIELD[,FIELD...]",
            help=(
                "Optional comma-separated Yahoo quote fields to request. "
                "Yoghurt does not validate field names."
            ),
        ),
        ParamSpec(
            name="formatted",
            cli_name="formatted",
            kind=ParamKind.BOOLEAN,
            default=False,
            help="Request Yahoo formatted values.",
        ),
        ParamSpec(
            name="enablePrivateCompany",
            cli_name="disable-private-company",
            kind=ParamKind.BOOLEAN,
            default=True,
            help="Do not include private company quote matches.",
        ),
        ParamSpec(
            name="overnightPrice",
            cli_name="no-overnight-price",
            kind=ParamKind.BOOLEAN,
            default=True,
            help="Do not request overnight price fields.",
        ),
        ParamSpec(
            name="topPickThisMonth",
            cli_name="top-pick-this-month",
            kind=ParamKind.BOOLEAN,
            help="Request top-pick-this-month quote metadata when Yahoo supports it.",
        ),
        ParamSpec(
            name="lang",
            cli_name="lang",
            kind=ParamKind.STRING,
            default="en-US",
            metavar="LANG",
            help="Yahoo response language.",
        ),
        ParamSpec(
            name="region",
            cli_name="region",
            kind=ParamKind.STRING,
            default="US",
            metavar="REGION",
            help="Yahoo response region.",
        ),
        ParamSpec(
            name="imgHeights",
            cli_name="img-heights",
            kind=ParamKind.INTEGER,
            metavar="PIXELS",
            help="Logo/image height requested from Yahoo.",
        ),
        ParamSpec(
            name="imgLabels",
            cli_name="img-labels",
            kind=ParamKind.CSV,
            metavar="LABEL[,LABEL...]",
            help="Image labels to request, such as logoUrl.",
        ),
        ParamSpec(
            name="imgWidths",
            cli_name="img-widths",
            kind=ParamKind.INTEGER,
            metavar="PIXELS",
            help="Logo/image width requested from Yahoo.",
        ),
    ),
    examples=(
        "yoghurt quote SMR,OKLO,LEU,VST,CEG",
        (
            "yoghurt quote SMR,SERV,SYM,GEV,LASE,RR "
            "--fields marketCap,morningstarIndustry,logoUrl,longName,"
            "regularMarketPrice,regularMarketChange,regularMarketChangePercent,"
            "shortName,regularMarketTime,regularMarketVolume "
            "--img-heights 50 --img-labels logoUrl --img-widths 50"
        ),
    ),
    field_reference=QUOTE_FIELDS,
)

SPARK_COMMAND = CommandSpec(
    name="spark",
    path="/v7/finance/spark",
    summary="Fetch sparkline price series for one or more symbols.",
    description=(
        "Compact timestamp and price series for equities, ETFs, indices, futures, "
        "forex, and crypto when Yahoo supports them."
    ),
    use_crumb=True,
    params=(
        ParamSpec(
            name="symbols",
            cli_name="symbols",
            kind=ParamKind.CSV,
            positional=True,
            required=True,
            metavar="SYMBOL[,SYMBOL...]",
            min_items=1,
            help=(
                "One or more comma-separated Yahoo symbols, such as AAPL,MSFT, "
                "^GSPC, GC=F, EURUSD=X, or BTC-USD."
            ),
        ),
        ParamSpec(
            name="range",
            cli_name="range",
            kind=ParamKind.STRING,
            default="1d",
            metavar="RANGE",
            help=(
                "Spark range to request. Observed quote-page values: 1d and 24h. "
                "Yoghurt does not validate range values."
            ),
        ),
        ParamSpec(
            name="interval",
            cli_name="interval",
            kind=ParamKind.STRING,
            default="5m",
            metavar="INTERVAL",
            help=(
                "Spark interval to request. Observed quote-page value: 5m. "
                "Yoghurt does not validate interval values."
            ),
        ),
        ParamSpec(
            name="indicators",
            cli_name="indicators",
            kind=ParamKind.CSV,
            default="close",
            metavar="INDICATOR[,INDICATOR...]",
            help=(
                "Comma-separated Spark indicators to request. Observed value: close. "
                "Yoghurt does not validate indicator names."
            ),
        ),
        ParamSpec(
            name="includeTimestamps",
            cli_name="include-timestamps",
            kind=ParamKind.BOOLEAN,
            default=False,
            help="Include timestamp arrays when Yahoo supports them.",
        ),
        ParamSpec(
            name="includePrePost",
            cli_name="include-pre-post",
            kind=ParamKind.BOOLEAN,
            default=False,
            help="Include pre-market and post-market data when Yahoo supports it.",
        ),
        ParamSpec(
            name="corsDomain",
            cli_name="cors-domain",
            kind=ParamKind.STRING,
            default="finance.yahoo.com",
            metavar="DOMAIN",
            help="Yahoo CORS domain parameter observed on finance.yahoo.com pages.",
        ),
        ParamSpec(
            name=".tsrc",
            cli_name="tsrc",
            kind=ParamKind.STRING,
            default="finance",
            metavar="SOURCE",
            help="Yahoo source marker observed on finance.yahoo.com pages.",
        ),
    ),
    examples=(
        "yoghurt spark AAPL,MSFT",
        "yoghurt spark SPY,QQQ --range 1d --interval 5m",
        (
            "yoghurt spark ^GSPC,GC=F,EURUSD=X,BTC-USD --indicators close "
            "--include-timestamps --include-pre-post"
        ),
    ),
    notes=(
        (
            "Observed quote-page request: range=1d (or 24h), interval=5m, "
            "indicators=close."
        ),
        (
            "--range, --interval, and --indicators are open-ended; Yahoo may "
            "accept values beyond the observed quote-page request."
        ),
    ),
)

OPTIONS_COMMAND = CommandSpec(
    name="options",
    path="/v7/finance/options/{symbol}",
    summary="Fetch the option chain for a symbol.",
    description=(
        "Expiration list, contracts, strikes, implied volatility, and underlying "
        "quote data for one symbol."
    ),
    use_crumb=True,
    params=(
        ParamSpec(
            name="symbol",
            cli_name="symbol",
            kind=ParamKind.STRING,
            positional=True,
            path_param=True,
            required=True,
            metavar="SYMBOL",
            help="A single Yahoo symbol, such as AAPL or SHOP.TO.",
        ),
        ParamSpec(
            name="date",
            cli_name="date",
            kind=ParamKind.DATETIME,
            default=-1,
            metavar="DATE",
            help=(
                "Option expiration date as a Unix timestamp, YYYY-MM-DD date, "
                "or ISO datetime. Date-only values are converted at UTC midnight. "
                "Yahoo uses -1 for the default chain."
            ),
        ),
        ParamSpec(
            name="formatted",
            cli_name="formatted",
            kind=ParamKind.BOOLEAN,
            default=False,
            help="Request Yahoo formatted values.",
        ),
        ParamSpec(
            name="straddle",
            cli_name="straddle",
            kind=ParamKind.BOOLEAN,
            default=False,
            help="Request Yahoo straddle data when available.",
        ),
        ParamSpec(
            name="lang",
            cli_name="lang",
            kind=ParamKind.STRING,
            default="en-US",
            metavar="LANG",
            help="Yahoo response language.",
        ),
        ParamSpec(
            name="region",
            cli_name="region",
            kind=ParamKind.STRING,
            default="US",
            metavar="REGION",
            help="Yahoo response region.",
        ),
    ),
    examples=(
        "yoghurt options AAPL",
        "yoghurt options AAPL --date 2017-11-17",
        "yoghurt options AAPL --date 1510876800 --formatted --straddle",
    ),
)

QUOTE_TYPE_COMMAND = CommandSpec(
    name="quote-type",
    path="/v1/finance/quoteType/{symbol}",
    summary="Fetch instrument classification metadata for a symbol.",
    description=("Quote type, exchange, market, and identity metadata for one symbol."),
    use_crumb=True,
    params=(
        ParamSpec(
            name="symbol",
            cli_name="symbol",
            kind=ParamKind.STRING,
            positional=True,
            path_param=True,
            required=True,
            metavar="SYMBOL",
            help="A single Yahoo symbol, such as AAPL, ^GSPC, or SHOP.TO.",
        ),
        ParamSpec(
            name="formatted",
            cli_name="formatted",
            kind=ParamKind.BOOLEAN,
            default=False,
            help="Request Yahoo formatted values.",
        ),
        ParamSpec(
            name="lang",
            cli_name="lang",
            kind=ParamKind.STRING,
            default="en-US",
            metavar="LANG",
            help="Yahoo response language.",
        ),
        ParamSpec(
            name="region",
            cli_name="region",
            kind=ParamKind.STRING,
            default="US",
            metavar="REGION",
            help="Yahoo response region.",
        ),
        ParamSpec(
            name="enablePrivateCompany",
            cli_name="disable-private-company",
            kind=ParamKind.BOOLEAN,
            default=True,
            help="Do not include private company data.",
        ),
        ParamSpec(
            name="overnightPrice",
            cli_name="no-overnight-price",
            kind=ParamKind.BOOLEAN,
            default=True,
            help="Do not request overnight price fields.",
        ),
    ),
    examples=(
        "yoghurt quote-type AAPL",
        "yoghurt quote-type AAPL --disable-private-company",
    ),
)

QUOTE_SUMMARY_MODULES: tuple[FieldReference, ...] = (
    FieldReference(
        "assetProfile",
        "Company address, industry, officers, governance, and business summary.",
    ),
    FieldReference("balanceSheetHistory", "Annual balance sheet statements."),
    FieldReference(
        "balanceSheetHistoryQuarterly", "Quarterly balance sheet statements."
    ),
    FieldReference(
        "calendarEvents",
        "Earnings dates, ex-dividend date, and related calendar data.",
    ),
    FieldReference(
        "corporateActions", "Corporate action metadata when Yahoo returns it."
    ),
    FieldReference("cashflowStatementHistory", "Annual cash flow statements."),
    FieldReference(
        "cashflowStatementHistoryQuarterly", "Quarterly cash flow statements."
    ),
    FieldReference(
        "defaultKeyStatistics",
        "Valuation, share-count, short-interest, and per-share statistics.",
    ),
    FieldReference("earnings", "Earnings charts and annual financial summaries."),
    FieldReference("earningsCallTranscripts", "Earnings call transcript metadata."),
    FieldReference("earningsGaap", "GAAP earnings data."),
    FieldReference("earningsHistory", "Historical EPS estimate and surprise data."),
    FieldReference("earningsNonGaap", "Non-GAAP earnings data."),
    FieldReference("earningsTrend", "Analyst earnings and revenue estimate trends."),
    FieldReference(
        "equityPerformance", "Equity performance overview and peer context."
    ),
    FieldReference(
        "financialData",
        "Analyst targets, recommendation data, margins, cash, debt, and growth fields.",
    ),
    FieldReference(
        "financialsTemplate",
        "Yahoo financial statement display template metadata.",
    ),
    FieldReference("fundOwnership", "Institutional fund ownership records."),
    FieldReference(
        "fundPerformance",
        "Fund returns, risk statistics, and performance category comparisons.",
    ),
    FieldReference(
        "fundProfile", "Fund family, category, fees, expenses, and management details."
    ),
    FieldReference("incomeStatementHistory", "Annual income statements."),
    FieldReference("incomeStatementHistoryQuarterly", "Quarterly income statements."),
    FieldReference("indexTrend", "Index-level earnings trend context."),
    FieldReference("industryTrend", "Industry-level earnings trend context."),
    FieldReference("insiderHolders", "Current insider holder records."),
    FieldReference("insiderTransactions", "Insider purchase and sale transactions."),
    FieldReference("institutionOwnership", "Institutional ownership records."),
    FieldReference("majorDirectHolders", "Major direct holder records."),
    FieldReference(
        "majorHoldersBreakdown",
        "Insider, institution, and float ownership percentages.",
    ),
    FieldReference("netSharePurchaseActivity", "Insider net share purchase activity."),
    FieldReference("pageViews", "Yahoo page-view engagement metadata."),
    FieldReference(
        "price",
        "Current price, exchange, currency, market state, and quote source data.",
    ),
    FieldReference(
        "quoteType", "Instrument type, exchange, timezone, and symbol identity."
    ),
    FieldReference(
        "quoteUnadjustedPerformanceOverview",
        "Unadjusted quote performance overview data.",
    ),
    FieldReference("recommendationTrend", "Analyst recommendation trend counts."),
    FieldReference("secFilings", "Recent SEC filing metadata."),
    FieldReference("sectorTrend", "Sector-level earnings trend context."),
    FieldReference(
        "summaryDetail", "Market summary, dividend, volume, beta, and valuation fields."
    ),
    FieldReference(
        "summaryProfile",
        "Business summary, sector, industry, employees, and website.",
    ),
    FieldReference("topHoldings", "Fund holdings, sector weights, and bond ratings."),
    FieldReference("upgradeDowngradeHistory", "Analyst upgrade and downgrade history."),
)

QUOTE_SUMMARY_COMMAND = CommandSpec(
    name="quote-summary",
    path="/v10/finance/quoteSummary/{symbol}",
    summary="Fetch quoteSummary modules for a symbol.",
    description=(
        "Selected quoteSummary modules — price, profile, financialData, earnings, "
        "statistics, holders, fund data, and more — for one symbol."
    ),
    use_crumb=True,
    params=(
        ParamSpec(
            name="symbol",
            cli_name="symbol",
            kind=ParamKind.STRING,
            positional=True,
            path_param=True,
            required=True,
            metavar="SYMBOL",
            help="A single Yahoo symbol, such as AAPL or SHOP.TO.",
        ),
        ParamSpec(
            name="modules",
            cli_name="modules",
            kind=ParamKind.CSV,
            default=(
                "summaryProfile,financialData,recommendationTrend,earnings,"
                "equityPerformance,defaultKeyStatistics"
            ),
            metavar="MODULE[,MODULE...]",
            help=(
                "Comma-separated Yahoo quoteSummary modules to request. "
                "Yoghurt does not validate module names."
            ),
        ),
        ParamSpec(
            name="formatted",
            cli_name="formatted",
            kind=ParamKind.BOOLEAN,
            default=False,
            help="Request Yahoo formatted values.",
        ),
        ParamSpec(
            name="enablePrivateCompany",
            cli_name="disable-private-company",
            kind=ParamKind.BOOLEAN,
            default=True,
            help="Do not include private company data.",
        ),
        ParamSpec(
            name="enableQSPExpandedEarnings",
            cli_name="disable-qsp-expanded-earnings",
            kind=ParamKind.BOOLEAN,
            default=True,
            help="Do not request Yahoo expanded quote summary earnings fields.",
        ),
        ParamSpec(
            name="overnightPrice",
            cli_name="no-overnight-price",
            kind=ParamKind.BOOLEAN,
            default=True,
            help="Do not request overnight price fields.",
        ),
        ParamSpec(
            name="lang",
            cli_name="lang",
            kind=ParamKind.STRING,
            default="en-US",
            metavar="LANG",
            help="Yahoo response language.",
        ),
        ParamSpec(
            name="region",
            cli_name="region",
            kind=ParamKind.STRING,
            default="US",
            metavar="REGION",
            help="Yahoo response region.",
        ),
    ),
    examples=(
        "yoghurt quote-summary AAPL",
        "yoghurt quote-summary AAPL --modules price,quoteType,summaryDetail",
    ),
    field_reference=QUOTE_SUMMARY_MODULES,
    field_reference_title="Quote summary --modules reference",
    notes=(
        (
            "Module availability depends on instrument type — funds populate "
            "fundProfile, fundPerformance, and topHoldings; equities do not."
        ),
    ),
)

RECOMMENDATIONS_BY_SYMBOL_COMMAND = CommandSpec(
    name="recommendations-by-symbol",
    path="/v6/finance/recommendationsbysymbol/{symbol}",
    summary="Fetch related-symbol recommendations for a symbol.",
    description=(
        "Yahoo's related-symbol recommendations rooted at one anchor symbol — "
        "the same list served behind index and equity quote pages."
    ),
    use_crumb=True,
    params=(
        ParamSpec(
            name="symbol",
            cli_name="symbol",
            kind=ParamKind.STRING,
            positional=True,
            path_param=True,
            required=True,
            metavar="SYMBOL",
            help="A single Yahoo symbol, such as ^GSPC, ^DJI, ^IXIC, or AAPL.",
        ),
        ParamSpec(
            name="fields",
            cli_name="fields",
            kind=ParamKind.CSV,
            metavar="FIELD[,FIELD...]",
            help=(
                "Optional comma-separated Yahoo recommendation fields to request. "
                "Yoghurt does not validate field names."
            ),
        ),
        ParamSpec(
            name="lang",
            cli_name="lang",
            kind=ParamKind.STRING,
            default="en-US",
            metavar="LANG",
            help="Yahoo response language.",
        ),
        ParamSpec(
            name="region",
            cli_name="region",
            kind=ParamKind.STRING,
            default="US",
            metavar="REGION",
            help="Yahoo response region.",
        ),
    ),
    examples=(
        "yoghurt recommendations-by-symbol ^GSPC",
        "yoghurt recommendations-by-symbol ^DJI",
        "yoghurt recommendations-by-symbol ^IXIC --fields symbol,recommendedSymbols",
    ),
    notes=(
        (
            "Index quote pages drive this endpoint: ^GSPC, ^DJI, and ^IXIC are "
            "the canonical anchors."
        ),
        (
            "Observed traffic sometimes includes an empty fields= parameter; "
            "yoghurt omits --fields by default because empty CSV values are rejected."
        ),
    ),
)

STOCK_RECOMMENDER_COMMAND = CommandSpec(
    name="stock-recommender",
    path="/xhr/stock-recommender",
    base_url="https://finance.yahoo.com",
    summary="Fetch related-tickers peers for an equity symbol.",
    description=(
        "Yahoo's stock-recommender related_tickers feed — a short ordered list "
        "of peer or competitor tickers Yahoo serves alongside an equity quote "
        "page."
    ),
    use_crumb=False,
    params=(
        ParamSpec(
            name="symbol",
            cli_name="symbol",
            kind=ParamKind.STRING,
            positional=True,
            required=True,
            metavar="SYMBOL",
            help="A single Yahoo equity symbol, such as AAPL or RY.TO.",
        ),
    ),
    examples=(
        "yoghurt stock-recommender AAPL",
        "yoghurt stock-recommender MSFT",
        "yoghurt stock-recommender RY.TO",
    ),
    notes=(
        (
            "Equity-only endpoint: ETFs, futures, forex, and crypto return 404; "
            "indices return 400."
        ),
        (
            "Hosted on finance.yahoo.com, not the query1 host used by most "
            "yoghurt commands; the query1 mirror returns 500."
        ),
    ),
)

PRICE_INSIGHTS_COMMAND = CommandSpec(
    name="price-insights",
    path="/ws/company-fundamentals/v1/finance/price-insights",
    summary="Fetch AI-generated price insights for one or more symbols.",
    description=(
        "News summaries, AI analysis, anomaly checks, and analyst-rating context "
        "for one or more symbols when Yahoo has them."
    ),
    use_crumb=True,
    params=(
        ParamSpec(
            name="symbols",
            cli_name="symbols",
            kind=ParamKind.CSV,
            positional=True,
            required=True,
            metavar="SYMBOL[,SYMBOL...]",
            min_items=1,
            help=(
                "One or more comma-separated Yahoo symbols, such as AAPL or AAPL,MSFT."
            ),
        ),
        ParamSpec(
            name="modules",
            cli_name="modules",
            kind=ParamKind.CSV,
            metavar="MODULE[,MODULE...]",
            help=(
                "Optional comma-separated Yahoo price-insights modules to request. "
                "Observed useful value: ai. Yoghurt does not validate module names."
            ),
        ),
        ParamSpec(
            name="aiModules",
            cli_name="ai-modules",
            kind=ParamKind.CSV,
            metavar="AI_MODULE[,AI_MODULE...]",
            help=(
                "Optional comma-separated Yahoo AI submodules to request. "
                "Observed values: news_summary,price_movement. Yoghurt does not "
                "validate names."
            ),
        ),
        ParamSpec(
            name="checkAnomaly",
            cli_name="check-anomaly",
            kind=ParamKind.BOOLEAN,
            help=(
                "Ask Yahoo to check only for a price anomaly. Observed true value "
                "returns a tiny hasPriceAnomaly-only response."
            ),
        ),
        ParamSpec(
            name="lang",
            cli_name="lang",
            kind=ParamKind.STRING,
            default="en-US",
            metavar="LANG",
            help="Yahoo response language.",
        ),
        ParamSpec(
            name="region",
            cli_name="region",
            kind=ParamKind.STRING,
            default="US",
            metavar="REGION",
            help="Yahoo response region.",
        ),
    ),
    examples=(
        "yoghurt price-insights AAPL",
        "yoghurt price-insights AAPL,MSFT --modules ai",
        ("yoghurt price-insights AAPL --ai-modules news_summary,price_movement"),
    ),
    common_modules=("ai",),
    notes=(
        (
            "Default (no modules) returns news, aiAnalysis, analystRating, and "
            "anomaly data; modules=ai returned aiAnalysis and hasPriceAnomaly "
            "without the surrounding news/rating sections."
        ),
        (
            "aiModules=news_summary,price_movement does not change the response "
            "when modules is omitted."
        ),
        (
            "checkAnomaly=true narrows the response to hasPriceAnomaly; "
            "checkAnomaly=false behaves like omission."
        ),
    ),
)

CALENDAR_EVENTS_MODULES: tuple[FieldReference, ...] = (
    FieldReference(
        "earnings",
        "Upcoming and recent earnings release dates and EPS estimates.",
    ),
    FieldReference(
        "economicEvents",
        (
            "Macro economic calendar events (CPI, Fed decisions, employment "
            "reports, etc.). Filters controlled by "
            "--include-all-economic-events and --economic-events-region-filter."
        ),
    ),
    FieldReference(
        "ipoEvents",
        "Upcoming and recent IPO events.",
    ),
    FieldReference(
        "secReports",
        "Recent SEC filing events (10-K, 10-Q, 8-K, etc.).",
    ),
)

CALENDAR_EVENTS_COMMAND = CommandSpec(
    name="calendar-events",
    path="/ws/screeners/v1/finance/calendar-events",
    summary="Fetch earnings, IPO, economic, and SEC filing events for a symbol.",
    description=(
        "Calendar events over a date range for one symbol. Pick which event "
        "types to return via --modules (earnings, ipoEvents, secReports, "
        "economicEvents)."
    ),
    use_crumb=True,
    params=(
        ParamSpec(
            name="tickersFilter",
            cli_name="symbol",
            kind=ParamKind.STRING,
            positional=True,
            required=True,
            metavar="SYMBOL",
            help="A single Yahoo symbol, such as AAPL or SHOP.TO.",
        ),
        ParamSpec(
            name="modules",
            cli_name="modules",
            kind=ParamKind.CSV,
            default="earnings",
            metavar="MODULE[,MODULE...]",
            min_items=1,
            help=(
                "Comma-separated event modules to request. "
                "See the --modules reference below. "
                "Yoghurt does not validate module names."
            ),
        ),
        ParamSpec(
            name="countPerDay",
            cli_name="count-per-day",
            kind=ParamKind.INTEGER,
            default=100,
            metavar="COUNT",
            help="Maximum calendar event rows to request per day.",
        ),
        ParamSpec(
            name="startDate",
            cli_name="start-date",
            kind=ParamKind.DATETIME_MILLISECONDS,
            default="now-3d",
            metavar="DATE",
            help=(
                "Start date as Unix seconds, Unix milliseconds, YYYY-MM-DD date, "
                "or ISO datetime. Yoghurt sends milliseconds to Yahoo."
            ),
        ),
        ParamSpec(
            name="endDate",
            cli_name="end-date",
            kind=ParamKind.DATETIME_MILLISECONDS,
            default="now",
            metavar="DATE",
            help=(
                "End date as Unix seconds, Unix milliseconds, YYYY-MM-DD date, "
                "or ISO datetime. Yoghurt sends milliseconds to Yahoo."
            ),
        ),
        ParamSpec(
            name="economicEventsHighImportanceOnly",
            cli_name="include-all-economic-events",
            kind=ParamKind.BOOLEAN,
            default=True,
            help="Include lower-importance economic events when Yahoo supports them.",
        ),
        ParamSpec(
            name="economicEventsRegionFilter",
            cli_name="economic-events-region-filter",
            kind=ParamKind.STRING,
            default="",
            allow_empty_default=True,
            metavar="REGION",
            help=(
                "Economic event region filter. Observed Yahoo requests send an "
                "empty value. Defaults to an empty value when omitted."
            ),
        ),
        ParamSpec(
            name="lang",
            cli_name="lang",
            kind=ParamKind.STRING,
            default="en-US",
            metavar="LANG",
            help="Yahoo response language.",
        ),
        ParamSpec(
            name="region",
            cli_name="region",
            kind=ParamKind.STRING,
            default="US",
            metavar="REGION",
            help="Yahoo response region.",
        ),
    ),
    examples=(
        "yoghurt calendar-events AAPL",
        "yoghurt calendar-events AAPL --modules ipoEvents",
        "yoghurt calendar-events AAPL --modules secReports",
        (
            "yoghurt calendar-events AAPL --start-date 2026-05-01 "
            "--end-date 2026-05-31 --modules economicEvents "
            "--include-all-economic-events"
        ),
        (
            "yoghurt calendar-events AAPL --start-date 1777593600000 "
            "--end-date 1777852800000 --modules earnings"
        ),
    ),
    field_reference=CALENDAR_EVENTS_MODULES,
    field_reference_title="Calendar events --modules reference",
    notes=(
        "startDate and endDate are sent to Yahoo as milliseconds.",
        (
            "Observed Yahoo requests include economic event filters even when "
            "requesting earnings."
        ),
    ),
)

FUNDAMENTALS_TIMESERIES_COMMAND = CommandSpec(
    name="timeseries",
    path="/ws/fundamentals-timeseries/v1/finance/timeseries/{symbol}",
    summary="Fetch fundamentals timeseries for a symbol.",
    description=(
        "Timestamped fundamentals, valuation ratios, earnings events, analyst "
        "ratings, and economic events over a date range for one symbol."
    ),
    use_crumb=True,
    params=(
        ParamSpec(
            name="symbol",
            cli_name="symbol",
            kind=ParamKind.STRING,
            positional=True,
            path_param=True,
            required=True,
            metavar="SYMBOL",
            help="A single Yahoo symbol, such as AAPL or SHOP.TO.",
        ),
        ParamSpec(
            name="type",
            cli_name="type",
            kind=ParamKind.CSV,
            default="spEarningsReleaseEvents,analystRatings,economicEvents",
            metavar="TYPE[,TYPE...]",
            min_items=1,
            help=(
                "One or more comma-separated Yahoo fundamentals timeseries "
                "types to request. Yoghurt does not validate type names."
            ),
        ),
        ParamSpec(
            name="period1",
            cli_name="period1",
            kind=ParamKind.DATETIME,
            default="now-3d",
            metavar="DATE",
            help=(
                "Start date as a Unix timestamp, YYYY-MM-DD date, or ISO "
                "datetime. Defaults to a recent quote-page window when omitted. "
                "Date-only values are converted at UTC midnight."
            ),
        ),
        ParamSpec(
            name="period2",
            cli_name="period2",
            kind=ParamKind.DATETIME,
            default="now",
            metavar="DATE",
            help=(
                "End date as a Unix timestamp, YYYY-MM-DD date, or ISO "
                "datetime. Defaults to the current Unix timestamp when omitted. "
                "Date-only values are converted at UTC midnight."
            ),
        ),
        ParamSpec(
            name="merge",
            cli_name="merge",
            kind=ParamKind.BOOLEAN,
            help="Ask Yahoo to merge timeseries results when supported.",
        ),
        ParamSpec(
            name="padTimeSeries",
            cli_name="no-pad-time-series",
            kind=ParamKind.BOOLEAN,
            default=True,
            help="Ask Yahoo not to pad missing timeseries values.",
        ),
        ParamSpec(
            name="lang",
            cli_name="lang",
            kind=ParamKind.STRING,
            default="en-US",
            metavar="LANG",
            help="Yahoo response language.",
        ),
        ParamSpec(
            name="region",
            cli_name="region",
            kind=ParamKind.STRING,
            default="US",
            metavar="REGION",
            help="Yahoo response region.",
        ),
    ),
    examples=(
        "yoghurt timeseries AAPL",
        (
            "yoghurt timeseries AAPL --period1 2025-11-03 "
            "--period2 2026-05-03 --type quarterlyMarketCap,trailingMarketCap"
        ),
        (
            "yoghurt timeseries AAPL --period1 1762192800 "
            "--period2 1777831199 --type quarterlyPeRatio,trailingPeRatio "
            "--merge --no-pad-time-series"
        ),
    ),
    field_reference=TIMESERIES_TYPE_REFERENCES,
    field_reference_title="Timeseries --type reference",
    notes=(
        "The --type parameter is open-ended; availability depends on symbol.",
        (
            "period1 and period2 accept Unix timestamps, YYYY-MM-DD dates, "
            "or ISO datetimes."
        ),
        (
            "When period arguments are omitted, yoghurt requests a recent "
            "quote-page-style window ending at the current Unix timestamp."
        ),
    ),
)

INSIGHTS_COMMAND = CommandSpec(
    name="insights",
    path="/ws/insights/v3/finance/insights",
    summary="Fetch research reports and insights for one or more symbols.",
    description=(
        "Research report metadata, company snapshots, and instrument insights "
        "for one or more symbols when Yahoo has them."
    ),
    use_crumb=True,
    params=(
        ParamSpec(
            name="symbols",
            cli_name="symbols",
            kind=ParamKind.CSV,
            positional=True,
            required=True,
            metavar="SYMBOL[,SYMBOL...]",
            min_items=1,
            help=(
                "One or more comma-separated Yahoo symbols, such as AAPL or AAPL,MSFT."
            ),
        ),
        ParamSpec(
            name="disableRelatedReports",
            cli_name="enable-related-reports",
            kind=ParamKind.BOOLEAN,
            default=True,
            help="Allow Yahoo to include related research reports.",
        ),
        ParamSpec(
            name="formatted",
            cli_name="formatted",
            kind=ParamKind.BOOLEAN,
            default=False,
            help="Request Yahoo formatted values.",
        ),
        ParamSpec(
            name="getAllResearchReports",
            cli_name="skip-all-research-reports",
            kind=ParamKind.BOOLEAN,
            default=True,
            help="Do not request all available research reports.",
        ),
        ParamSpec(
            name="reportsCount",
            cli_name="reports-count",
            kind=ParamKind.INTEGER,
            default=4,
            metavar="COUNT",
            help="Number of research reports to request.",
        ),
        ParamSpec(
            name="ssl",
            cli_name="no-ssl",
            kind=ParamKind.BOOLEAN,
            default=True,
            help="Do not request SSL URLs in Yahoo response fields.",
        ),
        ParamSpec(
            name="lang",
            cli_name="lang",
            kind=ParamKind.STRING,
            default="en-US",
            metavar="LANG",
            help="Yahoo response language.",
        ),
        ParamSpec(
            name="region",
            cli_name="region",
            kind=ParamKind.STRING,
            default="US",
            metavar="REGION",
            help="Yahoo response region.",
        ),
    ),
    examples=(
        "yoghurt insights AAPL",
        "yoghurt insights AAPL,MSFT",
        "yoghurt insights AAPL --reports-count 4",
    ),
    notes=(
        (
            "Yahoo returns one finance.result item per requested symbol — "
            "AAPL,MSFT,NVDA yields three result objects."
        ),
    ),
)

_SCREENER_EQUITIES_MOVERS = (
    FieldReference("MOST_ACTIVES", "Stocks with the highest daily trading volume."),
    FieldReference("MOST_ACTIVE_PENNY_STOCKS", "Penny stocks with high daily volume."),
    FieldReference("UNUSUAL_VOLUME_STOCKS", "Stocks with unusual trading volume."),
    FieldReference("DAY_GAINERS", "Stocks with the greatest daily gains."),
    FieldReference("DAY_LOSERS", "Stocks with the greatest daily losses."),
    FieldReference("MOST_SHORTED_STOCKS", "Stocks with high short interest."),
)

_SCREENER_EQUITIES_SIZE_PRICE = (
    FieldReference("SMALL_CAP_STOCKS", "Small-cap stocks."),
    FieldReference("LARGE_CAP_STOCKS", "Large-cap stocks."),
    FieldReference("MOST_EXPENSIVE_STOCKS", "Stocks trading at the highest prices."),
    FieldReference("HIGHEST_BETA_STOCKS", "Stocks with the highest beta."),
    FieldReference("PINK_SHEET_STOCKS", "OTC pink sheet stocks."),
    FieldReference("SMALL_CAP_GAINERS", "Small-cap stocks with recent gains."),
)

_SCREENER_EQUITIES_TECHNICAL = (
    FieldReference(
        "RECENT_52_WEEK_HIGHS", "Stocks recently trading near 52-week highs."
    ),
    FieldReference("RECENT_52_WEEK_LOWS", "Stocks recently trading near 52-week lows."),
    FieldReference(
        "BULLISH_STOCKS_RIGHT_NOW", "Stocks matching Yahoo bullish screens."
    ),
    FieldReference(
        "BEARISH_STOCKS_RIGHT_NOW", "Stocks matching Yahoo bearish screens."
    ),
)

_SCREENER_EQUITIES_ANALYST_VALUE = (
    FieldReference(
        "ANALYST_STRONG_BUY_STOCKS", "Stocks with strong-buy analyst signals."
    ),
    FieldReference(
        "MORNINGSTAR_FIVE_STAR_STOCKS", "Five-star Morningstar stock ideas."
    ),
    FieldReference(
        "UNDERVALUED_GROWTH_STOCKS", "Growth stocks Yahoo marks as undervalued."
    ),
    FieldReference(
        "UNDERVALUED_LARGE_CAPS", "Large-cap stocks Yahoo marks as undervalued."
    ),
    FieldReference(
        "UNDERVALUED_WIDE_MOAT_STOCKS",
        "Wide-moat stocks Yahoo marks as undervalued.",
    ),
    FieldReference("GROWTH_TECHNOLOGY_STOCKS", "Technology stocks with growth traits."),
    FieldReference(
        "AGGRESSIVE_SMALL_CAPS", "Small-cap stocks with aggressive growth traits."
    ),
    FieldReference(
        "HIGHEST_DIVIDEND_STOCKS", "Stocks with the highest dividend yield."
    ),
)

_SCREENER_EQUITIES_INSTITUTIONAL = (
    FieldReference(
        "MOST_INSTITUTIONALLY_BOUGHT_LARGE_CAP_STOCKS",
        "Large-cap stocks with institutional buying.",
    ),
    FieldReference(
        "MOST_INSTITUTIONALLY_HELD_LARGE_CAP_STOCKS",
        "Large-cap stocks with high institutional ownership.",
    ),
    FieldReference(
        "TOP_STOCKS_OWNED_BY_CATHIE_WOOD", "Stocks associated with Cathie Wood funds."
    ),
)

_SCREENER_FUNDS_ETFS = (
    FieldReference(
        "TOP_MUTUAL_FUNDS", "Top mutual funds in Yahoo's predefined screen."
    ),
    FieldReference(
        "SOLID_LARGE_GROWTH_FUNDS", "Large-growth funds with solid ratings."
    ),
    FieldReference(
        "SOLID_MIDCAP_GROWTH_FUNDS", "Mid-cap growth funds with solid ratings."
    ),
    FieldReference(
        "CONSERVATIVE_FOREIGN_FUNDS", "Foreign funds with conservative profiles."
    ),
    FieldReference("HIGH_YIELD_BOND", "High-yield bond funds."),
    FieldReference("LARGE_BLEND_ETFS", "Large-blend exchange-traded funds."),
    FieldReference("TECHNOLOGY_ETFS", "Technology exchange-traded funds."),
    FieldReference("PORTFOLIO_ANCHORS", "Funds Yahoo identifies as portfolio anchors."),
)

_SCREENER_CRYPTO = (
    FieldReference(
        "MOST_ACTIVES_CRYPTOCURRENCIES",
        "Cryptocurrencies with the highest daily trading volume.",
    ),
    FieldReference(
        "DAY_GAINERS_CRYPTOCURRENCIES",
        "Cryptocurrencies with the greatest daily gains.",
    ),
    FieldReference(
        "DAY_LOSERS_CRYPTOCURRENCIES",
        "Cryptocurrencies with the greatest daily losses.",
    ),
)

_SCREENER_PRIVATE = (
    FieldReference(
        "52_WEEK_GAINERS_PRIVATE_COMPANY",
        "Private companies with gains over the past 52 weeks.",
    ),
    FieldReference(
        "RECENTLY_FUNDED_PRIVATE_COMPANY", "Recently funded private companies."
    ),
)

_SCREENER_OPTIONS = (
    FieldReference("DAY_GAINERS_OPTIONS", "Options with the greatest daily gains."),
    FieldReference("DAY_LOSERS_OPTIONS", "Options with the greatest daily losses."),
    FieldReference("TOP_OPTIONS_OPEN_INTEREST", "Options ranked by open interest."),
    FieldReference(
        "TOP_OPTIONS_IMPLIED_VOLATALITY",
        "Options ranked by implied volatility. (Yahoo ID has a typo.)",
    ),
)

PREDEFINED_SCREENER_SECTIONS: tuple[ReferenceSection, ...] = (
    ReferenceSection(
        title="Equities — movers and volume",
        values=_SCREENER_EQUITIES_MOVERS,
    ),
    ReferenceSection(
        title="Equities — size and price",
        values=_SCREENER_EQUITIES_SIZE_PRICE,
    ),
    ReferenceSection(
        title="Equities — technical signals",
        values=_SCREENER_EQUITIES_TECHNICAL,
    ),
    ReferenceSection(
        title="Equities — analyst and value",
        values=_SCREENER_EQUITIES_ANALYST_VALUE,
    ),
    ReferenceSection(
        title="Equities — institutional",
        values=_SCREENER_EQUITIES_INSTITUTIONAL,
    ),
    ReferenceSection(title="Funds and ETFs", values=_SCREENER_FUNDS_ETFS),
    ReferenceSection(title="Crypto", values=_SCREENER_CRYPTO),
    ReferenceSection(title="Private companies", values=_SCREENER_PRIVATE),
    ReferenceSection(title="Options", values=_SCREENER_OPTIONS),
)

PREDEFINED_SCREENER_COMMAND = CommandSpec(
    name="screener-predefined",
    path="/v1/finance/screener/predefined/saved",
    summary="Run one or more of Yahoo's predefined screeners.",
    description=(
        "Records from Yahoo's predefined saved screeners — e.g. MOST_ACTIVES, "
        "DAY_GAINERS, TOP_MUTUAL_FUNDS. See the reference below for known IDs."
    ),
    use_crumb=True,
    params=(
        ParamSpec(
            name="scrIds",
            cli_name="scr-ids",
            kind=ParamKind.CSV,
            positional=True,
            required=True,
            metavar="SCR_ID[,SCR_ID...]",
            min_items=1,
            help=(
                "One or more comma-separated Yahoo predefined screener IDs, "
                "such as MOST_ACTIVES."
            ),
        ),
        ParamSpec(
            name="count",
            cli_name="count",
            kind=ParamKind.INTEGER,
            default=200,
            metavar="COUNT",
            help="Number of screener records to request.",
        ),
        ParamSpec(
            name="start",
            cli_name="start",
            kind=ParamKind.INTEGER,
            default=0,
            metavar="OFFSET",
            help="Zero-based record offset for paging through screener results.",
        ),
        ParamSpec(
            name="formatted",
            cli_name="formatted",
            kind=ParamKind.BOOLEAN,
            default=False,
            help="Request Yahoo formatted values.",
        ),
        ParamSpec(
            name="useRecordsResponse",
            cli_name="no-records-response",
            kind=ParamKind.BOOLEAN,
            default=True,
            help="Do not request Yahoo's records-style screener response shape.",
        ),
        ParamSpec(
            name="sortField",
            cli_name="sort-field",
            kind=ParamKind.STRING,
            default="",
            allow_empty_default=True,
            metavar="FIELD",
            help=(
                "Optional Yahoo sort field. Omit it for Yahoo's observed empty "
                "sortField."
            ),
        ),
        ParamSpec(
            name="sortType",
            cli_name="sort-type",
            kind=ParamKind.STRING,
            default="",
            allow_empty_default=True,
            metavar="TYPE",
            help=(
                "Optional Yahoo sort direction/type. Omit it for Yahoo's "
                "observed empty sortType."
            ),
        ),
        ParamSpec(
            name="lang",
            cli_name="lang",
            kind=ParamKind.STRING,
            default="en-US",
            metavar="LANG",
            help="Yahoo response language.",
        ),
        ParamSpec(
            name="region",
            cli_name="region",
            kind=ParamKind.STRING,
            default="US",
            metavar="REGION",
            help="Yahoo response region.",
        ),
    ),
    examples=(
        "yoghurt screener-predefined MOST_ACTIVES",
        "yoghurt screener-predefined MOST_ACTIVES --count 25 --start 25",
        "yoghurt screener-predefined MOST_ACTIVES --no-records-response",
    ),
    reference_sections=PREDEFINED_SCREENER_SECTIONS,
    notes=(
        (
            "Screener IDs are Yahoo-defined and open-ended; "
            "yoghurt does not validate them."
        ),
        (
            "Observed Yahoo quote pages request MOST_ACTIVES with count=200, "
            "start=0, and useRecordsResponse=true; yoghurt defaults formatted=false."
        ),
        (
            "Yahoo's records-style response returns a fixed record field set; "
            "use raw for ad hoc fields= experiments with useRecordsResponse=false."
        ),
        (
            "Observed browser requests include empty sortField and sortType; "
            "yoghurt sends those empty values when the options are omitted."
        ),
    ),
)

CHART_COMMAND = CommandSpec(
    name="chart",
    path="/v8/finance/chart/{symbol}",
    summary="Fetch historical OHLC chart data for a symbol.",
    description=(
        "Timestamps, OHLC, volume, and (optionally) dividends, splits, and "
        "earnings markers over a date range and interval for one symbol."
    ),
    use_crumb=False,
    params=(
        ParamSpec(
            name="symbol",
            cli_name="symbol",
            kind=ParamKind.STRING,
            positional=True,
            path_param=True,
            required=True,
            metavar="SYMBOL",
            help="A single Yahoo symbol, such as AAPL, GC=F, SPY, or BTC-USD.",
        ),
        ParamSpec(
            name="period1",
            cli_name="period1",
            kind=ParamKind.DATETIME,
            default="now-3d",
            metavar="DATE",
            help=(
                "Start date as a Unix timestamp, YYYY-MM-DD date, or ISO "
                "datetime. Defaults to a recent quote-page window when omitted. "
                "Date-only values are converted at UTC midnight."
            ),
        ),
        ParamSpec(
            name="period2",
            cli_name="period2",
            kind=ParamKind.DATETIME,
            default="now",
            metavar="DATE",
            help=(
                "End date as a Unix timestamp, YYYY-MM-DD date, or ISO "
                "datetime. Defaults to the current Unix timestamp when omitted. "
                "Date-only values are converted at UTC midnight."
            ),
        ),
        ParamSpec(
            name="range",
            cli_name="range",
            kind=ParamKind.STRING,
            metavar="RANGE",
            help=(
                "Relative chart window. Supported values: "
                f"{', '.join(CHART_RANGES)}. Cannot be combined with period1 "
                "or period2."
            ),
        ),
        ParamSpec(
            name="interval",
            cli_name="interval",
            kind=ParamKind.STRING,
            default="1m",
            metavar="INTERVAL",
            help=(f"Chart interval. Supported values: {', '.join(CHART_INTERVALS)}."),
        ),
        ParamSpec(
            name="includePrePost",
            cli_name="include-pre-post",
            kind=ParamKind.BOOLEAN,
            default=False,
            help="Include pre-market and post-market data when Yahoo supports it.",
        ),
        ParamSpec(
            name="events",
            cli_name="events",
            kind=ParamKind.CSV,
            default="div,split,earn",
            metavar="EVENT[,EVENT...]",
            allowed_values=("div", "split", "earn"),
            csv_separator="|",
            help=(
                "Comma-separated chart events to request. Supported values: "
                "div, split, earn."
            ),
        ),
        ParamSpec(
            name="lang",
            cli_name="lang",
            kind=ParamKind.STRING,
            default="en-US",
            metavar="LANG",
            help="Yahoo response language.",
        ),
        ParamSpec(
            name="region",
            cli_name="region",
            kind=ParamKind.STRING,
            default="US",
            metavar="REGION",
            help="Yahoo response region.",
        ),
    ),
    examples=(
        "yoghurt chart AAPL",
        "yoghurt chart AAPL --range 1mo --interval 1d",
        "yoghurt chart AAPL --period1 2026-04-30",
        "yoghurt chart AAPL --period1 1777507200 --period2 1777593600 --interval 1m",
        "yoghurt chart SPY --period1 2026-01-01 --interval 1d --events div,split",
    ),
    notes=(
        "period2 must be greater than period1.",
        "range cannot be combined with period1 or period2.",
        (
            "When period2 is omitted, yoghurt sends the current Unix timestamp; "
            "now is not accepted as a user-provided value."
        ),
        ("Yahoo can reject overlong windows for short intervals (1m, 5m, 15m)."),
    ),
)

RATINGS_TOP_COMMAND = CommandSpec(
    name="ratings-top",
    path="/v2/ratings/top/{symbol}",
    summary="Fetch top analyst rating buckets for a symbol.",
    description=(
        "Direction, momentum, price-target, and financial-score components "
        "from Yahoo's top scored analyst rating buckets for one symbol."
    ),
    use_crumb=False,
    params=(
        ParamSpec(
            name="symbol",
            cli_name="symbol",
            kind=ParamKind.STRING,
            positional=True,
            path_param=True,
            required=True,
            metavar="SYMBOL",
            help="A single Yahoo symbol, such as AAPL or SHOP.TO.",
        ),
        ParamSpec(
            name="exclude_noncurrent",
            cli_name="include-noncurrent",
            kind=ParamKind.BOOLEAN,
            default=True,
            help=(
                "Include non-current analyst records in Yahoo's top scored rating "
                "buckets."
            ),
        ),
        ParamSpec(
            name="lang",
            cli_name="lang",
            kind=ParamKind.STRING,
            default="en-US",
            metavar="LANG",
            help="Yahoo response language.",
        ),
        ParamSpec(
            name="region",
            cli_name="region",
            kind=ParamKind.STRING,
            default="US",
            metavar="REGION",
            help="Yahoo response region.",
        ),
    ),
    examples=(
        "yoghurt ratings-top AAPL",
        "yoghurt ratings-top AAPL --include-noncurrent",
    ),
    notes=(
        (
            "Observed Yahoo quote pages request exclude_noncurrent=true and "
            "return dir, mm, pt, and fin_score top analyst buckets."
        ),
        (
            "exclude_noncurrent=false can return older scored analyst records "
            "with null current rating and price-target fields."
        ),
    ),
)

MARKET_TIME_COMMAND = CommandSpec(
    name="market-time",
    path="/v6/finance/markettime",
    summary="Show current market hours and session status.",
    description=(
        "Trading hours and session state for global markets. Symbol-independent."
    ),
    use_crumb=False,
    params=(
        ParamSpec(
            name="formatted",
            cli_name="formatted",
            kind=ParamKind.BOOLEAN,
            default=False,
            help="Request Yahoo formatted values.",
        ),
        ParamSpec(
            name="key",
            cli_name="key",
            kind=ParamKind.STRING,
            default="finance",
            metavar="KEY",
            help="Yahoo product key sent with the request.",
        ),
        ParamSpec(
            name="lang",
            cli_name="lang",
            kind=ParamKind.STRING,
            default="en-US",
            metavar="LANG",
            help="Yahoo response language.",
        ),
        ParamSpec(
            name="region",
            cli_name="region",
            kind=ParamKind.STRING,
            default="US",
            metavar="REGION",
            help="Yahoo response region.",
        ),
    ),
    examples=(
        "yoghurt market-time",
        "yoghurt market-time --formatted",
    ),
    notes=(
        (
            "Observed Yahoo requests send formatted=true; yoghurt defaults to "
            "formatted=false for raw values."
        ),
    ),
)

ANALYST_COMMAND = CommandSpec(
    name="analyst",
    path="/ws/mad/v2/analyst/symbol/{symbol}",
    summary="Fetch analyst intelligence for a symbol.",
    description=(
        "Options put/call ratio, news summary with key takeaways, 1w/1m/1y "
        "timeframe insights, price targets, and analyst ratings — all for "
        "one symbol."
    ),
    use_crumb=True,
    params=(
        ParamSpec(
            name="symbol",
            cli_name="symbol",
            kind=ParamKind.STRING,
            positional=True,
            path_param=True,
            required=True,
            metavar="SYMBOL",
            help="A single Yahoo symbol, such as AAPL or SHOP.TO.",
        ),
        ParamSpec(
            name="debug_flag",
            cli_name="debug-flag",
            kind=ParamKind.BOOLEAN,
            default=False,
            help="Enable Yahoo debug mode in the response.",
        ),
        ParamSpec(
            name="lang",
            cli_name="lang",
            kind=ParamKind.STRING,
            default="en-US",
            metavar="LANG",
            help="Yahoo response language.",
        ),
        ParamSpec(
            name="region",
            cli_name="region",
            kind=ParamKind.STRING,
            default="US",
            metavar="REGION",
            help="Yahoo response region.",
        ),
    ),
    examples=(
        "yoghurt analyst AAPL",
        "yoghurt analyst MSFT --debug-flag",
    ),
    notes=("Coverage across non-equity asset classes is unconfirmed.",),
)

TRENDING_COMMAND = CommandSpec(
    name="trending",
    path="/v1/finance/trending/{region}",
    summary="List trending tickers for a region.",
    description=(
        "The trending tickers Yahoo serves in chart-page sidebars and "
        "trending widgets, scoped to a region."
    ),
    use_crumb=False,
    params=(
        ParamSpec(
            name="region",
            cli_name="region",
            kind=ParamKind.STRING,
            path_param=True,
            default="US",
            metavar="REGION",
            help="Region for trending tickers. Substituted into the URL path.",
        ),
        ParamSpec(
            name="count",
            cli_name="count",
            kind=ParamKind.INTEGER,
            default=5,
            metavar="COUNT",
            help="Number of trending tickers to request.",
        ),
        ParamSpec(
            name="useQuotes",
            cli_name="no-use-quotes",
            kind=ParamKind.BOOLEAN,
            default=True,
            help="Do not request inline quote data with trending results.",
        ),
        ParamSpec(
            name="fields",
            cli_name="fields",
            kind=ParamKind.CSV,
            metavar="FIELD[,FIELD...]",
            min_items=1,
            help=(
                "Comma-separated quote fields to include in the response. "
                "Yoghurt does not validate field names."
            ),
        ),
        ParamSpec(
            name="quoteType",
            cli_name="quote-type",
            kind=ParamKind.STRING,
            metavar="TYPE",
            help=(
                "Filter trending results by quote type (e.g. EQUITY). "
                "Omitted when not specified."
            ),
        ),
        ParamSpec(
            name="formatted",
            cli_name="formatted",
            kind=ParamKind.BOOLEAN,
            default=False,
            help="Request Yahoo formatted values.",
        ),
        ParamSpec(
            name="lang",
            cli_name="lang",
            kind=ParamKind.STRING,
            default="en-US",
            metavar="LANG",
            help="Yahoo response language.",
        ),
    ),
    examples=(
        "yoghurt trending",
        "yoghurt trending --count 10 --quote-type EQUITY",
        (
            "yoghurt trending --fields "
            "symbol,shortName,regularMarketPrice,regularMarketChangePercent"
        ),
    ),
    notes=(
        "The region is substituted into the URL path, not sent as a query parameter.",
        (
            "Observed Yahoo chart pages fire two variants: one with logoUrl and "
            "price fields for the sidebar strip, and one with quoteType=EQUITY "
            "for the trending tickers widget."
        ),
    ),
)

TIMESERIES_FIELDS_COMMAND = CommandSpec(
    name="timeseries-fields",
    path="/ws/fundamentals-timeseries/v1/finance/timeseriesfields",
    summary="List available fundamentals timeseries field names for a type.",
    description=(
        "Field-name catalog for a fundamentals timeseries type. Observed on "
        "chart pages to discover significant-development (sigDev) event fields."
    ),
    use_crumb=False,
    params=(
        ParamSpec(
            name="type",
            cli_name="type",
            kind=ParamKind.STRING,
            default="sigDev",
            metavar="TYPE",
            help="Timeseries field type to query. Observed value: sigDev.",
        ),
        ParamSpec(
            name="lang",
            cli_name="lang",
            kind=ParamKind.STRING,
            default="en-US",
            metavar="LANG",
            help="Yahoo response language.",
        ),
        ParamSpec(
            name="region",
            cli_name="region",
            kind=ParamKind.STRING,
            default="US",
            metavar="REGION",
            help="Yahoo response region.",
        ),
    ),
    examples=(
        "yoghurt timeseries-fields",
        "yoghurt timeseries-fields --type sigDev",
    ),
    notes=(
        (
            "Returns field metadata, not timeseries data. Use the timeseries "
            "command to fetch actual fundamentals values."
        ),
        "Observed Yahoo chart pages request type=sigDev on every page load.",
    ),
)

MARKET_INFO_COMMAND = CommandSpec(
    name="market-info",
    path="/ws/market-info/v1/finance/markets/ids",
    summary="Fetch commodity and currency market data.",
    description=(
        "Commodity and currency tiles used by Yahoo Finance's sidebar "
        "widgets. Symbol-independent."
    ),
    use_crumb=False,
    params=(
        ParamSpec(
            name="modules",
            cli_name="modules",
            kind=ParamKind.CSV,
            default="commodities,currencies",
            metavar="MODULE[,MODULE...]",
            min_items=1,
            help=(
                "Comma-separated market data modules to request. "
                "Observed values: commodities, currencies. "
                "Yoghurt does not validate module names."
            ),
        ),
        ParamSpec(
            name="lang",
            cli_name="lang",
            kind=ParamKind.STRING,
            default="en-US",
            metavar="LANG",
            help="Yahoo response language.",
        ),
        ParamSpec(
            name="region",
            cli_name="region",
            kind=ParamKind.STRING,
            default="US",
            metavar="REGION",
            help="Yahoo response region.",
        ),
    ),
    examples=(
        "yoghurt market-info",
        "yoghurt market-info --modules commodities",
        "yoghurt market-info --modules commodities,currencies",
    ),
    notes=(
        "Observed Yahoo chart pages always request modules=commodities,currencies.",
    ),
)

SCREENER_DISCOVER_COMMAND = CommandSpec(
    name="screener-discover",
    path="/ws/screeners/v1/finance/screener/discover",
    summary="Discover investment ideas from Yahoo screener modules.",
    description=(
        "Yahoo's screener-discover idea modules, such as neo_investment_ideas. "
        "Distinct from the predefined screener endpoint."
    ),
    use_crumb=False,
    params=(
        ParamSpec(
            name="modules",
            cli_name="modules",
            kind=ParamKind.CSV,
            default="neo_investment_ideas",
            metavar="MODULE[,MODULE...]",
            min_items=1,
            help=(
                "Comma-separated screener discover modules to request. "
                "Observed value: neo_investment_ideas. "
                "Yoghurt does not validate module names."
            ),
        ),
        ParamSpec(
            name="count",
            cli_name="count",
            kind=ParamKind.INTEGER,
            default=5,
            metavar="COUNT",
            help="Number of results to request per module.",
        ),
        ParamSpec(
            name="formatted",
            cli_name="formatted",
            kind=ParamKind.BOOLEAN,
            default=False,
            help="Request Yahoo formatted values.",
        ),
        ParamSpec(
            name="lang",
            cli_name="lang",
            kind=ParamKind.STRING,
            default="en-US",
            metavar="LANG",
            help="Yahoo response language.",
        ),
        ParamSpec(
            name="region",
            cli_name="region",
            kind=ParamKind.STRING,
            default="US",
            metavar="REGION",
            help="Yahoo response region.",
        ),
    ),
    examples=(
        "yoghurt screener-discover",
        "yoghurt screener-discover --count 10",
        "yoghurt screener-discover --modules neo_investment_ideas --count 5",
    ),
    notes=(
        (
            "Observed Yahoo chart pages request modules=neo_investment_ideas "
            "with count=5 and formatted=true."
        ),
    ),
)

MARKET_SUMMARY_COMMAND = CommandSpec(
    name="market-summary",
    path="/v6/finance/quote/marketSummary",
    summary="Fetch global market summary: indices, futures, forex, crypto.",
    description=(
        "Major indices, futures, forex pairs, and cryptocurrencies in one "
        "snapshot. The symbol set returned varies by region."
    ),
    use_crumb=False,
    params=(
        ParamSpec(
            name="formatted",
            cli_name="formatted",
            kind=ParamKind.BOOLEAN,
            default=False,
            help="Request Yahoo formatted values.",
        ),
        ParamSpec(
            name="lang",
            cli_name="lang",
            kind=ParamKind.STRING,
            default="en-US",
            metavar="LANG",
            help="Yahoo response language.",
        ),
        ParamSpec(
            name="region",
            cli_name="region",
            kind=ParamKind.STRING,
            default="US",
            metavar="REGION",
            help=(
                "Yahoo response region. Controls which markets are returned "
                "(e.g. US returns S&P 500, Dow, Nasdaq; CA returns TSX, CAD pairs)."
            ),
        ),
    ),
    examples=(
        "yoghurt market-summary",
        "yoghurt market-summary --region CA",
        "yoghurt market-summary --region GB --lang en-GB",
    ),
    notes=(
        "The region parameter changes which indices, pairs, and assets Yahoo returns.",
        "No symbol or authentication is required.",
    ),
)

_SECTOR_SLUGS: tuple[FieldReference, ...] = (
    FieldReference("technology", "Technology sector."),
    FieldReference("financial-services", "Financial services sector."),
    FieldReference("consumer-cyclical", "Consumer cyclical sector."),
    FieldReference("communication-services", "Communication services sector."),
    FieldReference("healthcare", "Healthcare sector."),
    FieldReference("industrials", "Industrials sector."),
    FieldReference("consumer-defensive", "Consumer defensive sector."),
    FieldReference("energy", "Energy sector."),
    FieldReference("basic-materials", "Basic materials sector."),
    FieldReference("real-estate", "Real estate sector."),
    FieldReference("utilities", "Utilities sector."),
)

_SCREENER_INSTRUMENT_ASSET_CLASSES: tuple[FieldReference, ...] = (
    FieldReference("equity", "Common stocks."),
    FieldReference("etf", "Exchange-traded funds."),
    FieldReference("mutualfund", "Mutual funds."),
    FieldReference("cryptocurrency", "Cryptocurrencies."),
    FieldReference("index", "Market indices."),
    FieldReference("future", "Futures contracts."),
    FieldReference("option", "Option contracts."),
    FieldReference("currency", "Forex pairs."),
    FieldReference("bond", "Bonds."),
    FieldReference("commodity", "Commodities."),
    FieldReference("warrant", "Warrants."),
)

_SCREENER_INSTRUMENT_EVENT_ENTITIES: tuple[FieldReference, ...] = (
    FieldReference("economic_event", "Macroeconomic releases."),
    FieldReference("splits", "Stock split calendar."),
    FieldReference("ipo_info", "IPO calendar with pricing."),
    FieldReference("insider_transaction", "Form 4 insider trades."),
    FieldReference("research_reports", "Morningstar analyst reports."),
    FieldReference("trade_idea", "Trade ideas."),
)

_SCREENER_INSTRUMENT_PREMIUM: tuple[FieldReference, ...] = (
    FieldReference(
        "analyst_ratings",
        "Wall Street ratings and price targets. Data 401-locked; schema readable.",
    ),
    FieldReference(
        "tradingcentral_event_info",
        "Trading Central technical signals. Data 401-locked; schema readable.",
    ),
    FieldReference(
        "institutional_interest",
        "Aggregate institutional buying and selling per ticker. "
        "Data 401-locked; schema readable.",
    ),
    FieldReference(
        "institutional_holdings",
        "Per-fund 13F position rows. Data 401-locked; schema readable.",
    ),
)

_SCREENER_INSTRUMENT_SECTIONS: tuple[ReferenceSection, ...] = (
    ReferenceSection(
        title="Asset classes (use as quoteType in visualization or screener)",
        values=_SCREENER_INSTRUMENT_ASSET_CLASSES,
    ),
    ReferenceSection(
        title=("Event and calendar entities (use as entityIdType in visualization)"),
        values=_SCREENER_INSTRUMENT_EVENT_ENTITIES,
    ),
    ReferenceSection(
        title=(
            "Premium-locked entities "
            "(schema visible here; query data via screener-predefined)"
        ),
        values=_SCREENER_INSTRUMENT_PREMIUM,
    ),
)

SCREENER_INSTRUMENT_FIELDS_COMMAND = CommandSpec(
    name="screener-instrument-fields",
    path="/v1/finance/screener/instrument/{instrument}/fields",
    summary="List every field available for a Yahoo data-platform entity.",
    description=(
        "Schema for one Yahoo screener instrument: each field's ID, display "
        "name, data type, category, and sortable/premium/deprecated flags. "
        "Also enumerates the quick-pick filter chips Yahoo's screener UI "
        "offers per field, with their operator and operand values."
    ),
    use_crumb=True,
    params=(
        ParamSpec(
            name="instrument",
            cli_name="instrument",
            kind=ParamKind.STRING,
            positional=True,
            path_param=True,
            required=True,
            metavar="INSTRUMENT",
            help=(
                "Instrument identifier. See the reference sections below for "
                "confirmed values."
            ),
        ),
        ParamSpec(
            name="lang",
            cli_name="lang",
            kind=ParamKind.STRING,
            default="en-US",
            metavar="LANG",
            help="Yahoo response language.",
        ),
        ParamSpec(
            name="region",
            cli_name="region",
            kind=ParamKind.STRING,
            default="US",
            metavar="REGION",
            help="Yahoo response region.",
        ),
    ),
    examples=(
        "yoghurt screener-instrument-fields equity",
        "yoghurt screener-instrument-fields etf",
        "yoghurt screener-instrument-fields analyst_ratings",
        (
            "yoghurt screener-instrument-fields equity | "
            "jq -r '.finance.result[0].fields | keys[]'"
        ),
    ),
    reference_sections=_SCREENER_INSTRUMENT_SECTIONS,
    notes=(
        (
            "Each field metadata object exposes: fieldId, displayName, type "
            "(STRING / NUMBER / DATE / BOOLEAN), category, sortable, "
            "isPremium, deprecated, and a labels[] array of quick-pick "
            "filter chips with their operator and operand values."
        ),
        (
            "Asset-class field IDs are snake_case or dotted "
            "(e.g. peratio.lasttwelvemonths). Both the visualization and "
            "screener routes accept these names in query.operands."
        ),
        (
            "isPremium=true means the underlying data is paywalled. The "
            "schema itself is always returned. The four premium-data "
            "entities (analyst_ratings, tradingcentral_event_info, "
            "institutional_interest, institutional_holdings) only return "
            "rows through curated screener-predefined presets."
        ),
        (
            "Known quirks: sp_earnings returns a Yahoo 500 here; use the "
            "default columns observed in live visualization queries instead. "
            "privatecompany returns an empty fields map (data paywalled)."
        ),
    ),
)


SECTOR_COMMAND = CommandSpec(
    name="sector",
    path="/v1/finance/sectors/{sector}",
    summary="Fetch sector overview, performance, top holdings, and industries.",
    description=(
        "Sector-level data: performance metrics, top companies, top ETFs, "
        "top mutual funds, industry breakdown, and research reports."
    ),
    use_crumb=True,
    params=(
        ParamSpec(
            name="sector",
            cli_name="sector",
            kind=ParamKind.STRING,
            positional=True,
            path_param=True,
            required=True,
            metavar="SECTOR",
            help=("Sector slug. See the sector reference below for confirmed values."),
        ),
        ParamSpec(
            name="withReturns",
            cli_name="with-returns",
            kind=ParamKind.BOOLEAN,
            default=False,
            help="Include return data in the sector performance response.",
        ),
        ParamSpec(
            name="formatted",
            cli_name="formatted",
            kind=ParamKind.BOOLEAN,
            default=False,
            help="Request Yahoo formatted values.",
        ),
        ParamSpec(
            name="lang",
            cli_name="lang",
            kind=ParamKind.STRING,
            default="en-US",
            metavar="LANG",
            help="Yahoo response language.",
        ),
        ParamSpec(
            name="region",
            cli_name="region",
            kind=ParamKind.STRING,
            default="US",
            metavar="REGION",
            help="Yahoo response region.",
        ),
    ),
    examples=(
        "yoghurt sector technology",
        "yoghurt sector financial-services",
        "yoghurt sector consumer-cyclical --with-returns",
    ),
    field_reference=_SECTOR_SLUGS,
    field_reference_title="Sector reference",
    notes=(
        (
            "Response nests everything under data.*: name, symbol, key, "
            "overview, performance, topCompanies, topETFs, topMutualFunds, "
            "industries, and researchReports."
        ),
    ),
)

COMMANDS: tuple[CommandSpec, ...] = (
    # Daily-driver fetches (known symbol -> data)
    QUOTE_COMMAND,
    CHART_COMMAND,
    OPTIONS_COMMAND,
    QUOTE_SUMMARY_COMMAND,
    QUOTE_TYPE_COMMAND,
    SPARK_COMMAND,
    # Discovery (find symbols, build custom queries).
    # visualization and screener (DSL-driven, defined in cli.py) slot in
    # between screener-predefined and screener-discover at the CLI layer.
    PREDEFINED_SCREENER_COMMAND,
    SCREENER_DISCOVER_COMMAND,
    # Symbol-bound analysis
    FUNDAMENTALS_TIMESERIES_COMMAND,
    CALENDAR_EVENTS_COMMAND,
    ANALYST_COMMAND,
    RATINGS_TOP_COMMAND,
    RECOMMENDATIONS_BY_SYMBOL_COMMAND,
    STOCK_RECOMMENDER_COMMAND,
    PRICE_INSIGHTS_COMMAND,
    INSIGHTS_COMMAND,
    # Market-wide state
    TRENDING_COMMAND,
    SECTOR_COMMAND,
    MARKET_SUMMARY_COMMAND,
    MARKET_INFO_COMMAND,
    MARKET_TIME_COMMAND,
    # Schema introspection
    SCREENER_INSTRUMENT_FIELDS_COMMAND,
    TIMESERIES_FIELDS_COMMAND,
)
COMMANDS_BY_NAME: dict[str, CommandSpec] = {
    command.name: command for command in COMMANDS
}
