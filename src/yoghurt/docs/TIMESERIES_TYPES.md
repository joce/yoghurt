# Timeseries Types

The `timeseries` command passes `--type` values through to Yahoo's
`/ws/fundamentals-timeseries/v1/finance/timeseries/{symbol}` endpoint. Yoghurt
does not validate these names, and availability can vary by symbol, market, and
date range.

This reference documents the observed Yahoo Finance type names used by the
quote, analysis, statistics, and fundamentals-timeseries surfaces.

## Event Types

| Type | Description |
| --- | --- |
| `spEarningsReleaseEvents` | S&P earnings release events. |
| `analystRatings` | Analyst ratings. |
| `economicEvents` | Economic events. |

## Valuation Measures

| Types | Description |
| --- | --- |
| `quarterlyMarketCap`, `trailingMarketCap` | Quarterly and trailing market capitalization. |
| `quarterlyEnterpriseValue`, `trailingEnterpriseValue` | Quarterly and trailing enterprise value. |
| `quarterlyPeRatio`, `trailingPeRatio` | Quarterly and trailing P/E ratio. |
| `quarterlyForwardPeRatio`, `trailingForwardPeRatio` | Quarterly and trailing forward P/E ratio. |
| `quarterlyPegRatio`, `trailingPegRatio` | Quarterly and trailing PEG ratio. |
| `quarterlyPsRatio`, `trailingPsRatio` | Quarterly and trailing price to sales ratio. |
| `quarterlyPbRatio`, `trailingPbRatio` | Quarterly and trailing price to book ratio. |
| `quarterlyEnterprisesValueRevenueRatio`, `trailingEnterprisesValueRevenueRatio` | Quarterly and trailing enterprise value to revenue. |
| `quarterlyEnterprisesValueEBITDARatio`, `trailingEnterprisesValueEBITDARatio` | Quarterly and trailing enterprise value to EBITDA. |

## Annual Statement Types

| Type | Description |
| --- | --- |
| `annualInterestExpense` | Annual interest expense. |
| `annualOtherIncomeExpense` | Annual other income or expense. |
| `annualOperatingCashFlow` | Annual operating cash flow. |
| `annualPurchaseOfInvestment` | Annual investment purchases. |
| `annualEndCashPosition` | Annual ending cash position. |
| `annualBeginningCashPosition` | Annual beginning cash position. |
| `annualNetOtherFinancingCharges` | Annual net other financing charges. |
| `annualRepurchaseOfCapitalStock` | Annual capital stock repurchases. |
| `annualRepaymentOfDebt` | Annual debt repayments. |
| `annualSaleOfInvestment` | Annual investment sales. |
| `annualPurchaseOfBusiness` | Annual business purchases. |
| `annualOtherNonCashItems` | Annual other non-cash items. |
| `annualFreeCashFlow` | Annual free cash flow. |
| `annualAccountsPayable` | Annual accounts payable. |
| `annualStockBasedCompensation` | Annual stock-based compensation. |
| `annualDeferredIncomeTax` | Annual deferred income tax. |
| `annualChangeInWorkingCapital` | Annual change in working capital. |
| `annualCostOfRevenue` | Annual cost of revenue. |
| `annualEBITDA` | Annual EBITDA. |
| `annualNormalizedEBITDA` | Annual normalized EBITDA. |
| `annualOperatingIncome` | Annual operating income. |
| `annualStockholdersEquity` | Annual stockholders' equity. |
| `annualCurrentLiabilities` | Annual current liabilities. |
| `annualTotalLiabilitiesNetMinorityInterest` | Annual total liabilities net minority interest. |
| `annualCurrentAssets` | Annual current assets. |
| `annualTotalAssets` | Annual total assets. |
| `annualChangesInAccountReceivables` | Annual changes in account receivables. |
| `annualCapitalExpenditure` | Annual capital expenditure. |
| `annualNetOtherInvestingChanges` | Annual net other investing changes. |
| `annualCashFlowFromContinuingFinancingActivities` | Annual cash flow from continuing financing activities. |
| `annualChangeInCashSupplementalAsReported` | Annual supplemental change in cash as reported. |
| `annualDepreciationAndAmortization` | Annual depreciation and amortization. |
| `annualChangeInInventory` | Annual change in inventory. |
| `annualInvestingCashFlow` | Annual investing cash flow. |
| `annualCommonStockIssuance` | Annual common stock issuance. |
| `annualCashDividendsPaid` | Annual cash dividends paid. |
| `annualChangeInAccountPayable` | Annual change in account payable. |
| `annualSpecialIncomeCharges` | Annual special income charges. |
| `annualOtherSpecialCharges` | Annual other special charges. |
| `annualRestructuringAndMergernAcquisition` | Annual restructuring and merger or acquisition charges. |
| `annualImpairmentOfCapitalAssets` | Annual impairment of capital assets. |
| `annualWriteOff` | Annual write-off charges. |
| `annualSellingAndMarketingExpense` | Annual selling and marketing expense. |
| `annualNetIncome` | Annual net income. |
| `annualTotalRevenue` | Annual total revenue. |
| `annualGrossProfit` | Annual gross profit. |
| `annualOperatingExpense` | Annual operating expense. |
| `annualResearchAndDevelopment` | Annual research and development expense. |
| `annualSellingGeneralAndAdministration` | Annual selling, general, and administrative expense. |
| `annualPretaxIncome` | Annual pretax income. |
| `annualTaxProvision` | Annual tax provision. |
| `annualBasicEPS` | Annual basic EPS. |
| `annualDilutedEPS` | Annual diluted EPS. |
| `annualBasicAverageShares` | Annual basic average shares. |
| `annualDilutedAverageShares` | Annual diluted average shares. |
| `annualNetIncomeContinuousOperations` | Annual net income from continuing operations. |
| `annualCapitalLeaseObligations` | Annual capital lease obligations. |
| `annualTotalDebt` | Annual total debt. |
| `annualNetDebt` | Annual net debt. |
| `annualGoodwillAndOtherIntangibleAssets` | Annual goodwill and other intangible assets. |
| `annualGoodwill` | Annual goodwill. |
| `annualAccountsReceivable` | Annual accounts receivable. |
| `annualInventory` | Annual inventory. |
| `annualCashCashEquivalentsAndShortTermInvestments` | Annual cash, cash equivalents, and short-term investments. |
| `annualLongTermDebt` | Annual long-term debt. |
| `annualNetPPE` | Annual net property, plant, and equipment. |
| `annualTotalNonCurrentAssets` | Annual total non-current assets. |
| `annualTotalNonCurrentLiabilitiesNetMinorityInterest` | Annual total non-current liabilities net minority interest. |
| `annualInvestedCapital` | Annual invested capital. |
| `annualWorkingCapital` | Annual working capital. |
| `annualTangibleBookValue` | Annual tangible book value. |

## Quarterly and Trailing Statement Types

| Quarterly type | Trailing type | Description |
| --- | --- | --- |
| `quarterlyTotalRevenue` | `trailingTotalRevenue` | Quarterly and trailing total revenue. |
| `quarterlyNetIncome` | `trailingNetIncome` | Quarterly and trailing net income. |
| `quarterlyCostOfRevenue` | `trailingCostOfRevenue` | Quarterly and trailing cost of revenue. |
| `quarterlyGrossProfit` | `trailingGrossProfit` | Quarterly and trailing gross profit. |
| `quarterlyOperatingIncome` | `trailingOperatingIncome` | Quarterly and trailing operating income. |
| `quarterlyInterestExpense` | `trailingInterestExpense` | Quarterly and trailing interest expense. |
| `quarterlyBasicEPS` | `trailingBasicEPS` | Quarterly and trailing basic EPS. |
| `quarterlyDilutedEPS` | `trailingDilutedEPS` | Quarterly and trailing diluted EPS. |
| `quarterlyEBITDA` | `trailingEBITDA` | Quarterly and trailing EBITDA. |
| `quarterlyOperatingExpense` | `trailingOperatingExpense` | Quarterly and trailing operating expense. |
| `quarterlyPretaxIncome` | `trailingPretaxIncome` | Quarterly and trailing pretax income. |
| `quarterlyTaxProvision` | `trailingTaxProvision` | Quarterly and trailing tax provision. |
| `quarterlyBasicAverageShares` | `trailingBasicAverageShares` | Quarterly and trailing basic average shares. |
| `quarterlyDilutedAverageShares` | `trailingDilutedAverageShares` | Quarterly and trailing diluted average shares. |
| `quarterlyOtherIncomeExpense` | `trailingOtherIncomeExpense` | Quarterly and trailing other income or expense. |
| `quarterlyNetIncomeContinuousOperations` | `trailingNetIncomeContinuousOperations` | Quarterly and trailing net income from continuing operations. |
| `quarterlyNormalizedEBITDA` | `trailingNormalizedEBITDA` | Quarterly and trailing normalized EBITDA. |
| `quarterlySellingAndMarketingExpense` | `trailingSellingAndMarketingExpense` | Quarterly and trailing selling and marketing expense. |
| `quarterlySellingGeneralAndAdministration` | `trailingSellingGeneralAndAdministration` | Quarterly and trailing selling, general, and administrative expense. |
| `quarterlyResearchAndDevelopment` | `trailingResearchAndDevelopment` | Quarterly and trailing research and development expense. |
