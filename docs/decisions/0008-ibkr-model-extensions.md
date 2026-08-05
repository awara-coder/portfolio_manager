# ADR 0008: IBKR-driven canonical-model extensions

- Status: approved
- Date: 2026-08-05
- Gate: G2 amendment
- Approved by: product owner

## Context

The approved model represents IBKR economic activity and quantities, but cannot yet preserve several broker-reported claims without flattening or discarding meaning.

## Proposed decision

Add broker-neutral, optional structures for:

- derivative contract terms: multiplier, underlying instrument, expiry, strike, and option right;
- source execution price on trade instrument legs;
- position valuation observations: mark, market value, cost basis, and reported realized/unrealized P/L, with missing metrics remaining absent;
- typed account metric observations including total cash, settled cash, net liquidation value, accrued interest, and dividend accrual;
- interest/dividend accrual observations distinct from settled cash activities;
- corporate-action subtype for split, merger, spin-off, exercise, assignment, expiration, cash settlement, and other.

Native-currency and base-currency values remain separate observations linked to their source FX evidence. Broker-reported P/L remains distinguishable from project-derived analytics. Initial IBKR scope rejects model-portfolio rows, securities-lending detail, and unsupported physical-commodity attributes into preserved unsupported evidence rather than coercing them.

## Consequences

These are additive extensions to G2; immutable activity/observation semantics and existing identifiers remain unchanged. More explicit values prevent double counting accruals and stop broker valuations from being mistaken for project calculations.

Approval authorizes domain implementation and synthetic tests before the IBKR connector. Analytics interpretation remains gated by G3.

## References

- [Flex open positions](https://www.ibkrguides.com/reportingreference/reportguide/open%20positionsfq.htm)
- [Interest accruals](https://www.ibkrguides.com/reportingreference/reportguide/interest%20accrualsfq.htm)
- [Option events](https://www.ibkrguides.com/reportingreference/reportguide/options_exercises_expirations_fq.htm)
