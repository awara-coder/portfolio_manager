# Zerodha Kite Connect API audit

Date: 2026-08-05

## Result

No Zerodha connector exists in the repository yet. `packages/connectors` contains only its package marker, so there is no implementation whose requests or mappings can currently be certified as correct. The implementation plan is directionally correct, subject to the constraints below.

## Required connector behavior

| Source | Correct use | Important constraint |
|---|---|---|
| `/portfolio/holdings` | Authoritative point-in-time long-term holding observation | Preserve realised, T1, used, collateral, short, MTF, and discrepancy fields separately; do not collapse them into one unexplained quantity |
| `/portfolio/positions` | Authoritative point-in-time net and day position observations | `net` and `day` have different semantics; overnight equity can move into holdings the next day |
| `/user/margins/:segment` | Point-in-time funds and margin observation | Margin availability is not a complete cash ledger |
| `/orders` and `/trades` | Intraday evidence and partial-fill mapping | Both collection endpoints describe the current day, so they cannot reconstruct missed historical activity |
| `/instruments` | Daily reference-data snapshot | It is a large, once-daily gzipped CSV; cache it around the documented 08:30 recommendation because expired derivative tokens disappear |
| `/quote`, `/quote/ohlc`, `/quote/ltp` | Current market observations | Batch at most 250 instruments and treat omitted response keys as missing, never zero |
| Historical candles | Historical price evidence | Respect the 3 requests/second limit and cache immutable ranges; continuous history is limited to supported futures behavior |

## Authentication and unattended operation

- Login must redirect the user to Kite and exchange the short-lived `request_token` server-side using the API secret.
- Retail access tokens expire by 06:00 the next day and can also be invalidated earlier. A `TokenException` requires session clearing and a new interactive login.
- The connector must never automate login, store a TOTP seed, fabricate browser sessions, or expose the API secret/access token to the browser.
- Therefore Kite alone cannot guarantee uninterrupted authoritative daily collection. Scheduled jobs may collect while a valid token exists; after expiry, reports must use approved imported evidence or remain visibly stale/incomplete until the user authenticates again.

## Error and rate-limit contract

- Send `X-Kite-Version: 3` and `Authorization: token api_key:access_token` on authenticated calls.
- Map the documented error type as well as HTTP status. In particular, distinguish authentication, rate limit, invalid input, broker/OMS network failure, temporary service failure, and unknown permanent errors.
- Enforce client-side limits: quotes 1 request/second, historical candles 3 requests/second, and other endpoints 10 requests/second. Add bounded retries with jitter only for safe transient reads; never retry authentication or validation failures blindly.
- Store the raw successful response before normalization and retain unknown fields/enums in source evidence. An unexpected enum must not be coerced into a known financial meaning.

## Correctness tests required before real use

- Contract fixtures for holdings with T1, collateral, discrepancy, MTF, zero, and short quantities.
- Net-versus-day positions, derivatives with multipliers, partial fills, and an empty trading day.
- Expired token, early invalidation, 429, 502/503/504, omitted quote keys, unknown instruments, and malformed payloads.
- Daily instrument-master versioning and lookup of an expired derivative from a prior cached master.
- User-assisted comparison of holdings, positions, and funds with Kite UI using local credentials only.

## Sources

- [Kite Connect login and token lifecycle](https://kite.trade/docs/connect/v3/user/)
- [Kite holdings and positions](https://kite.trade/docs/connect/v3/portfolio/)
- [Kite daily orders and trades](https://kite.trade/docs/connect/v3/orders/)
- [Kite instruments and market quotes](https://kite.trade/docs/connect/v3/market-data-and-instruments/)
- [Kite historical candles](https://kite.trade/docs/connect/v3/historical/)
- [Kite errors and rate limits](https://kite.trade/docs/connect/v3/exceptions/)
