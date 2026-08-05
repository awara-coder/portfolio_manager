# IBKR developer API and canonical-model audit

Date: 2026-08-05
Confidence: high for Flex reporting and current-state portfolio coverage; medium for unified OAuth availability to every individual-account configuration until validated on the user's account.

## Executive result

The canonical model has the correct architecture but is not yet sufficient for lossless normalization of the IBKR data needed by this project. Its immutable activities, observations, exact money/quantity types, multiple currencies, source evidence, corrections, fees, taxes, transfers, and ACATS linkage should remain. Additive extensions are required before an IBKR connector is implemented.

No IBKR connector exists in the repository today.

## API recommendation

Use Activity Flex Web Service as the first-release authoritative IBKR source:

- It is designed for programmatic retrieval of preconfigured reports without logging into Client Portal for each run.
- Tokens can be configured from six hours to one year and optionally restricted by IP.
- Activity data updates once daily; retrieve the previous day's statement the following morning rather than polling it as real time.
- The flow is asynchronous: `SendRequest` returns a reference code and `GetStatement` may report that generation is still in progress.
- Limit requests to one per second and ten per minute per token. Treat incomplete statement, settlement-not-ready, P/L-not-ready, heavy-load, and generation-in-progress responses as distinct retryable states.
- A single query can cover linked accounts depending on its account selection. Account identity must remain on every normalized record.

Do not require Client Portal Web API or TWS/IB Gateway for the first release. The Web API can later add near-real-time positions and currency ledgers, but it adds a separate session/authentication lifecycle and is unnecessary for daily reporting. TWS/IB Gateway is optimized for trading and live sessions, not the simplest unattended reporting path.

## Coverage against the current model

| IBKR fact | Current fit | Required action |
|---|---|---|
| Accounts, currencies, identifiers, listings | Good | Map account ID and Conid/security identifiers through existing tenant-owned mappings |
| Trades, commissions, transaction taxes | Mostly good | Add source execution price to an instrument leg; retain commission currency and source codes |
| Cash transactions, deposits, withdrawals, dividends, paid interest | Good | Existing typed cash legs cover these without changing their economic meaning |
| Foreign withholding, including source-specific labels | Good | Use `FOREIGN_WITHHOLDING` plus jurisdiction and original source label; do not invent tax treatment |
| FX trades and currency conversion rates | Good | Preserve actual conversion activity separately from report FX-rate observations |
| ACATS/internal transfers | Good | Existing shared transfer identity and independently sourced sides fit |
| Position quantity | Good | Existing position observation fits long, short, and fractional quantities |
| Position mark, market value, cost basis and broker P/L | Missing | Add a broker-reported position-valuation observation; do not silently recompute and call it IBKR-reported |
| Total cash versus settled cash | Missing | Add typed account metrics so settled cash, total cash, NAV, and other balances cannot overwrite one another |
| Interest and dividend accruals | Missing | Add accrual observations; an accrual is a balance-sheet claim, not a settled cash activity |
| Options/futures contract identity | Approved but unimplemented | Add multiplier, underlying, expiry, strike, and put/call terms promised by G2 |
| Exercises, assignments and expirations | Partly good | Typed legs can express effects; add a corporate-action subtype to retain the event meaning |
| ACATS cost-basis lots | Mostly good | Preserve lot-level source identifiers and originating transaction/order references in evidence |
| Advisor/model portfolios | Not represented | Declare unsupported for the first individual-account scope; do not collapse model-level rows if encountered |
| Securities lending and physical commodity details | Not represented | Preserve as unsupported evidence until separately scoped |

## Important IBKR idiosyncrasies

- Flex queries are user-configured schemas. The connector must validate required sections and fields at startup rather than assuming every query contains them.
- Report availability is not equivalent to completeness. IBKR exposes distinct "incomplete", "settlement not ready", and P/L-not-ready errors; data quality must retain those distinctions.
- Flex may return multiple accounts, models, asset classes, currencies, and source-specific codes in one report.
- IBKR reports both source currency and FX-to-base values. Native amounts remain canonical; base-currency amounts are separate broker claims, never replacements.
- Open positions can include multiplier, mark price, position value, cost basis, unrealized P/L, accrued interest, and originating lot references. Quantity alone is insufficient.
- Interest accrues daily and is later reversed when paid. Treating accrual and payment as the same cash activity would double count.
- Option exercise/assignment can affect both the derivative and its underlying and may include cash settlement, commission, tax, basis, and realized P/L.
- Large reports may be batch-generated. Polling must use bounded backoff and persist the reference code as a resumable checkpoint.

## Verification needed from the user later

- Create a least-privilege Activity Flex query locally and share only its selected section/field names, never its token, query ID, or account IDs.
- Run a local sanitized comparison for accounts, open positions, cash, trades, dividends, interest, fees, withholding, FX, and transfers relevant to the account.
- Confirm whether the account uses options, futures, bonds, margin, model portfolios, or securities lending so unsupported capabilities remain explicit.

## Official sources

- [Flex Web Service behavior and refresh cadence](https://www.interactivebrokers.com/docs/web-api/web-api-v-1-0-documentation/flex-web-service)
- [Flex Web Service setup and token lifetime](https://www.interactivebrokers.com/docs/web-api/flex-web-service/flex-web-service/client-portal-configuration/enable-and-create-access-token)
- [Flex Web Service v3 errors and limits](https://www.ibkrguides.com/orgportal/performanceandstatements/flex3error.htm)
- [Activity Flex Query section reference](https://www.ibkrguides.com/reportingreference/reportguide/activity%20flex%20query%20reference.htm)
- [Flex open-position fields](https://www.ibkrguides.com/reportingreference/reportguide/open%20positionsfq.htm)
- [Flex trade fields](https://www.ibkrguides.com/reportingreference/reportguide/tradesfq.htm)
- [Interest accrual semantics](https://www.ibkrguides.com/reportingreference/reportguide/interest%20accrualsfq.htm)
- [Open dividend accruals](https://www.ibkrguides.com/reportingreference/reportguide/open%20dividend%20accrualsfq.htm)
- [Option exercises, assignments, and expirations](https://www.ibkrguides.com/reportingreference/reportguide/options_exercises_expirations_fq.htm)
- [IBKR Web API portfolio and ledger documentation](https://ibkrcampus.com/campus/ibkr-api-page/webapi-doc/)
