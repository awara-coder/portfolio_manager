# ADR 0005: Zerodha sources and unattended mode

- Status: proposed
- Date: 2026-08-05
- Gate: G7
- Approved by: pending product-owner approval

## Context

Kite provides strong current-state observations but retail authentication is interactive and its access token expires by 06:00 the next day. Orders and trades are daily, not historical ledgers. An unattended report must not imply that an expired session or missed collection produced complete current data.

## Decision

Use a hybrid, read-only Zerodha connector:

- Use interactive Kite authorization without automating credentials or TOTP. Encrypt the API secret and access token under G4 and expose only a non-sensitive authentication state.
- While authenticated, collect holdings, net/day positions, funds, daily orders/trades, relevant quotes, and a versioned daily instrument master.
- Store immutable raw responses before normalization. Preserve T1, settled, used, collateral, short, MTF, and discrepancy attributes rather than reducing them to one quantity.
- Treat holdings, positions, funds, and quotes as point-in-time observations. Treat order/trade data as current-day evidence only.
- After token expiry, continue scheduled report generation from previously collected and separately approved imported evidence, but mark affected sections stale, reconstructed, partial, or unknown. Never label reconstruction as authoritative.
- Import historical activity only through separately approved official exports/documents. Absence of such evidence remains a visible coverage gap.
- Apply endpoint-aware throttling and typed errors. Missing quote keys and missing records are unknown, not zero.

The first connector is read-only even though the Kite API supports order mutation. Trading endpoints are outside project scope.

## Consequences

Authoritative collection requires periodic user login; completely unattended report generation remains possible, but completely unattended authoritative Kite refresh does not. Historical correctness depends on collecting daily evidence and/or importing approved reports. Cached instrument masters are required to retain expired derivative identity.

## Approval effect

Approval authorizes implementation and contract tests for this source policy. Real-account validation still requires the user to authenticate locally and compare sanitized results with Kite; credentials and raw account data must not be shared.

## References

- [Kite authentication](https://kite.trade/docs/connect/v3/user/)
- [Kite portfolio APIs](https://kite.trade/docs/connect/v3/portfolio/)
- [Kite orders and trades](https://kite.trade/docs/connect/v3/orders/)
- [Kite instruments and quotes](https://kite.trade/docs/connect/v3/market-data-and-instruments/)
- [Kite errors and rate limits](https://kite.trade/docs/connect/v3/exceptions/)
