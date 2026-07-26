# Quote Fields

The `quote` command accepts an optional `--fields` value for Yahoo quote fields:

```powershell
uv run yoghurt quote AAPL,MSFT --fields symbol,longName,companyLogoUrl,regularMarketPrice,overnightMarketPrice
```

Yoghurt passes field names through to Yahoo without validation. Availability
depends on the symbol, instrument type, exchange, region, and the current Yahoo
response shape.

`morningstarIndustry` is included because Yahoo returns it for some quote
requests and yoghurt uses it in quote examples.

| Field | Best-effort meaning |
| --- | --- |
| `ask` | Lowest price a seller is willing to accept for the security. |
| `askSize` | Number of units available at current ask price. |
| `averageAnalystRating` | Consensus rating from financial analysts for the quote. |
| `averageDailyVolume10Day` | Average number of shares traded each day over the last 10 days. |
| `averageDailyVolume3Month` | Average number of shares traded each day over the last 3 months. |
| `bid` | Highest price a buyer is willing to pay for the security. |
| `bidSize` | Total number of shares that buyers want to buy at the bid price. |
| `bookValue` | Net accounting value of a company's assets. |
| `circulatingSupply` | Number of cryptocurrency units currently in public circulation. |
| `coinImageUrl` | URL of the image representing the cryptocurrency. |
| `coinMarketCapLink` | URL of the MarketCap site for the cryptocurrency. |
| `contractSymbol` | Ticker symbol for a futures contract. |
| `cryptoTradeable` | Whether the cryptocurrency can be traded. |
| `customPriceAlertConfidence` | Undocumented Yahoo price alert confidence value. |
| `currency` | Currency in which the security is traded. |
| `displayName` | User-friendly name of the quote or security. |
| `dividendDate` | Date when the company is expected to pay its next dividend. |
| `dividendRate` | Amount of dividends expected over the next year. |
| `dividendYield` | Annual dividend as a percentage of the security's current price. |
| `earningsTimestamp` | Raw timestamp for the company's earnings announcement. |
| `earningsTimestampEnd` | Raw timestamp for the end of the earnings announcement window. |
| `earningsTimestampStart` | Raw timestamp for the start of the earnings announcement window. |
| `epsCurrentYear` | Company's earnings per share for the current year. |
| `epsForward` | Company's projected earnings per share for the next fiscal year. |
| `epsTrailingTwelveMonths` | Company's earnings per share for the past 12 months. |
| `esgPopulated` | Availability status of ESG ratings data. |
| `exchange` | Securities exchange on which the security is traded. |
| `exchangeDataDelayedBy` | Delay in data from the exchange, typically in minutes. |
| `exchangeTimezoneName` | Name of the exchange timezone. |
| `exchangeTimezoneShortName` | Short name of the exchange timezone. |
| `extendedMarketChange` | Change in the extended-hours market price. |
| `extendedMarketChangePercent` | Percent change in the extended-hours market price. |
| `extendedMarketPrice` | Latest price from extended-hours trading. |
| `extendedMarketTime` | Raw timestamp of the most recent extended-hours price. |
| `expireDate` | Date on which the option contract expires. |
| `expireIsoDate` | Option expiration date in ISO 8601 format. |
| `fiftyDayAverage` | Average closing price over the past 50 trading days. |
| `fiftyDayAverageChange` | Change in the 50-day average price from the previous trading day. |
| `fiftyDayAverageChangePercent` | Percent change in the 50-day average price from the previous trading day. |
| `fiftyTwoWeekChangePercent` | Percentage change in price over the past 52 weeks. |
| `fiftyTwoWeekHigh` | Highest price traded over the past 52 weeks. |
| `fiftyTwoWeekHighChange` | Change in the 52-week high price from the previous trading day. |
| `fiftyTwoWeekHighChangePercent` | Percent change in the 52-week high price from the previous trading day. |
| `fiftyTwoWeekLow` | Lowest price traded over the past 52 weeks. |
| `fiftyTwoWeekLowChange` | Change in the 52-week low price from the previous trading day. |
| `fiftyTwoWeekLowChangePercent` | Percent change in the 52-week low price from the previous trading day. |
| `fiftyTwoWeekRange` | Trading price range over the past 52 weeks. |
| `financialCurrency` | Currency in which the company reports financial results. |
| `firstTradeDateMilliseconds` | Raw first-trade timestamp in milliseconds. |
| `forwardPe` | Projected price-to-earnings ratio for the next 12 months. |
| `fromCurrency` | Base currency in an exchange pair. |
| `fromExchange` | Source exchange for a currency or conversion pair. |
| `fullExchangeName` | Full name of the securities exchange. |
| `gmtOffSetMilliseconds` | Exchange offset from GMT in milliseconds. |
| `headSymbolAsString` | Symbol of the contract's underlying security. |
| `ipoExpectedDate` | Expected date of the initial public offering. |
| `language` | Language in which financial results are reported. |
| `lastMarket` | Last market in which the security was traded. |
| `companyLogoUrl` | URL of the company's logo in Yahoo quote responses. |
| `logoUrl` | URL of the company's logo. |
| `longName` | Official name of the company or security. |
| `market` | Primary market for the security. |
| `marketCap` | Total market value of the security in trading currency. |
| `marketState` | Current state of the market for the security. |
| `messageBoardId` | Identifier for the Yahoo Finance message board. |
| `morningstarIndustry` | Morningstar industry classification when Yahoo returns it. |
| `nameChangeDate` | Date on which the company last changed its name. |
| `netAssets` | Total net assets of the fund or company. |
| `netExpenseRatio` | Ratio of total expenses to total net assets. |
| `openInterest` | Total number of open futures or options contracts. |
| `optionsType` | Yahoo option-type metadata returned by quote-page requests. |
| `optionType` | Type of option. |
| `overnightMarketChange` | Change in the overnight-market price. |
| `overnightMarketChangePercent` | Percent change in the overnight-market price. |
| `overnightMarketPrice` | Latest overnight-market price. |
| `overnightMarketTime` | Raw timestamp of the most recent overnight-market price. |
| `postMarketChange` | Change in the security's post-market price. |
| `postMarketChangePercent` | Percent change in the security's post-market price. |
| `postMarketPrice` | Price of the security in post-market trading. |
| `postMarketTime` | Raw timestamp of the most recent post-market trade. |
| `preMarketChange` | Change in the security's pre-market price. |
| `preMarketChangePercent` | Percent change in the security's pre-market price. |
| `preMarketPrice` | Price of the security in pre-market trading. |
| `preMarketTime` | Raw timestamp of the most recent pre-market trade. |
| `prevName` | Company name before its most recent name change. |
| `priceEpsCurrentYear` | Current-year price-to-earnings ratio. |
| `priceHint` | Decimal precision indicator for price values. |
| `priceToBook` | Market value relative to book value per share. |
| `quartrId` | Yahoo Quartr identifier when quote pages request it. |
| `quoteSourceName` | Name of the source providing the quote. |
| `quoteType` | Type of quote. |
| `region` | Region in which the company or security is located. |
| `regularMarketChange` | Change in the security's regular-market price. |
| `regularMarketChangePercent` | Percent change in the security's regular-market price. |
| `regularMarketDayHigh` | Highest price during the regular trading session. |
| `regularMarketDayLow` | Lowest price during the regular trading session. |
| `regularMarketDayRange` | Price range during the regular trading session. |
| `regularMarketOpen` | Opening price for the regular trading session. |
| `regularMarketPreviousClose` | Previous regular-session closing price. |
| `regularMarketPrice` | Latest price from the regular trading session. |
| `regularMarketSource` | Source label for the regular-market quote. |
| `regularMarketTime` | Raw timestamp of the most recent regular-session trade. |
| `regularMarketVolume` | Number of units traded in the regular session. |
| `sharesOutstanding` | Number of shares currently held by shareholders. |
| `shortName` | Short user-friendly name for the quote or security. |
| `sourceInterval` | Interval at which the data source provides updates, in seconds. |
| `startDate` | Date on which the coin started trading. |
| `stockStory` | Yahoo StockStory metadata when returned. |
| `strike` | Contractually specified price for options exercise. |
| `symbol` | Ticker symbol of the security. |
| `toCurrency` | Counter currency in an exchange pair. |
| `toExchange` | Destination exchange for a currency or conversion pair. |
| `tradeable` | Whether the security is currently tradeable. |
| `trailingAnnualDividendRate` | Dividend payment per share over the past 12 months. |
| `trailingAnnualDividendYield` | Dividend yield over the past 12 months. |
| `trailingPE` | Trailing price-to-earnings ratio based on past twelve-month results. |
| `trailingThreeMonthNavReturns` | Trailing three-month net asset value returns. |
| `trailingThreeMonthReturns` | Trailing three-month returns. |
| `triggerable` | Internal Yahoo Finance flag with undocumented purpose. |
| `twoHundredDayAverage` | Average closing price over the past 200 trading days. |
| `twoHundredDayAverageChange` | Change in the 200-day average price from the previous trading day. |
| `twoHundredDayAverageChangePercent` | Percent change in the 200-day average price from the previous trading day. |
| `typeDisp` | User-friendly representation of the quote type. |
| `underlyingExchangeSymbol` | Exchange symbol for the underlying asset's trading venue. |
| `underlyingShortName` | Short name of the underlying derivative security. |
| `underlyingSymbol` | Ticker symbol of the underlying derivative security. |
| `volume24Hr` | Total cryptocurrency trading volume in the past 24 hours. |
| `volumeAllCurrencies` | Aggregate 24-hour cryptocurrency volume across currency pairs. |
| `ytdReturn` | Year-to-date return on the security. |
