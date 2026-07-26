# Quote Summary Modules

`yoghurt quote-summary` passes the `--modules` value through to Yahoo Finance's
`/v10/finance/quoteSummary/{symbol}` endpoint. Yoghurt does not validate module
names, and Yahoo can vary availability by instrument type.

These module names were researched from Yahoo Finance client metadata and live
Yoghurt probes against Yahoo's raw quote summary endpoint. Equity probes used
`AAPL`; fund-specific probes used `VT`.

| Module | Description |
| --- | --- |
| `assetProfile` | Company address, industry, officers, governance, and business summary. |
| `balanceSheetHistory` | Annual balance sheet statements. |
| `balanceSheetHistoryQuarterly` | Quarterly balance sheet statements. |
| `calendarEvents` | Earnings dates, ex-dividend date, and related calendar data. |
| `corporateActions` | Corporate action metadata when Yahoo returns it. |
| `cashflowStatementHistory` | Annual cash flow statements. |
| `cashflowStatementHistoryQuarterly` | Quarterly cash flow statements. |
| `defaultKeyStatistics` | Valuation, share-count, short-interest, and per-share statistics. |
| `earnings` | Earnings charts and annual financial summaries. |
| `earningsCallTranscripts` | Earnings call transcript metadata. |
| `earningsGaap` | GAAP earnings data. |
| `earningsHistory` | Historical EPS estimate and surprise data. |
| `earningsNonGaap` | Non-GAAP earnings data. |
| `earningsTrend` | Analyst earnings and revenue estimate trends. |
| `equityPerformance` | Equity performance overview and peer context. |
| `financialData` | Analyst targets, recommendation data, margins, cash, debt, and growth fields. |
| `financialsTemplate` | Yahoo financial statement display template metadata. |
| `fundOwnership` | Institutional fund ownership records. |
| `fundPerformance` | Fund returns, risk statistics, and performance category comparisons. |
| `fundProfile` | Fund family, category, fees, expenses, and management details. |
| `incomeStatementHistory` | Annual income statements. |
| `incomeStatementHistoryQuarterly` | Quarterly income statements. |
| `indexTrend` | Index-level earnings trend context. |
| `industryTrend` | Industry-level earnings trend context. |
| `insiderHolders` | Current insider holder records. |
| `insiderTransactions` | Insider purchase and sale transactions. |
| `institutionOwnership` | Institutional ownership records. |
| `majorDirectHolders` | Major direct holder records. |
| `majorHoldersBreakdown` | Insider, institution, and float ownership percentages. |
| `netSharePurchaseActivity` | Insider net share purchase activity. |
| `pageViews` | Yahoo page-view engagement metadata. |
| `price` | Current price, exchange, currency, market state, and quote source data. |
| `quoteType` | Instrument type, exchange, timezone, and symbol identity. |
| `quoteUnadjustedPerformanceOverview` | Unadjusted quote performance overview data. |
| `recommendationTrend` | Analyst recommendation trend counts. |
| `secFilings` | Recent SEC filing metadata. |
| `sectorTrend` | Sector-level earnings trend context. |
| `summaryDetail` | Market summary, dividend, volume, beta, and valuation fields. |
| `summaryProfile` | Business summary, sector, industry, employees, and website. |
| `topHoldings` | Fund holdings, sector weights, and bond ratings. |
| `upgradeDowngradeHistory` | Analyst upgrade and downgrade history. |

## Research Notes

- `AAPL` populated the equity-focused modules, including financial statements,
  holders, trends, recommendations, price, quote type, and `equityPerformance`.
- `VT` populated the fund-specific `fundProfile`, `fundPerformance`, and
  `topHoldings` modules.
- Index quote pages were observed requesting `price`, `summaryDetail`,
  `pageViews`, `financialsTemplate`, `calendarEvents`,
  `quoteUnadjustedPerformanceOverview`, `corporateActions`,
  `earningsCallTranscripts`, `earningsGaap`, `earningsNonGaap`, and
  `upgradeDowngradeHistory`.
- `esgScores` appears in older third-party references, but live Yahoo probes
  returned HTTP 404 for `AAPL`, so it is not listed as a supported module here.
