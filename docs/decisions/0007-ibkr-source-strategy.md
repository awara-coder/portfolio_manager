# ADR 0007: IBKR source strategy

- Status: proposed
- Date: 2026-08-05
- Gate: G6
- Approved by: pending product-owner approval

## Context

The first IBKR release needs authoritative unattended daily history. Flex provides configurable activity statements and long-lived tokens; Web API and TWS/IB Gateway add fresher state but introduce session and operational complexity not required for a daily report.

## Proposed decision

Use Activity Flex Web Service v3 as the sole IBKR source for the first release. Retrieve the prior day's configured XML report once each morning, with bounded polling for generation, typed handling of IBKR error codes, overlap-based backfill, immutable raw storage, and tenant/account-scoped idempotency.

Require a documented Flex template containing account information, financial instruments, open positions at lot detail, cash report/statement of funds, trades at execution detail, cash transactions, corporate actions, currency conversion rates, transfers, transaction fees, interest accruals, and dividend accruals as applicable. Validate the template's actual sections and fields on every report; missing configured coverage is partial, not zero.

Defer Client Portal Web API and TWS/IB Gateway. Add Web API later only if approved freshness requirements cannot be met by Flex. Trading operations remain out of scope.

## Consequences

Daily collection can be unattended with a user-configured token of suitable lifetime, but Flex activity data is end-of-day and may be delayed. Reports must expose source date and completeness. The user must configure the Flex query and run local real-account validation.

Approval authorizes the IBKR Flex connector after the shared connector contract and required model extensions are approved and implemented.

## References

- [Flex service behavior](https://www.interactivebrokers.com/docs/web-api/web-api-v-1-0-documentation/flex-web-service)
- [Flex errors and limits](https://www.ibkrguides.com/orgportal/performanceandstatements/flex3error.htm)
- [Activity Flex sections](https://www.ibkrguides.com/reportingreference/reportguide/activity%20flex%20query%20reference.htm)
