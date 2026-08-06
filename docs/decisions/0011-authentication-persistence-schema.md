# ADR 0011: Authentication persistence schema

- Status: approved
- Date: 2026-08-06
- Gate: G4 implementation
- Approved by: product owner

## Decision

Persist tenant, institution, broker-connection, encrypted-secret, and authorization-nonce records in PostgreSQL. Secrets are stored only as the versioned envelope fields defined by ADR 0010. Nonce consumption uses one atomic `DELETE ... RETURNING` operation so a callback can succeed only once across processes and restarts.

Sensitive tables carry tenant IDs, composite tenant/connection foreign keys, and forced PostgreSQL row-level security. Policies read a transaction-local `app.tenant_id`; an unset context denies access. The migration is additive and does not include real credentials or financial data.

## Consequences

Runtime roles must establish tenant context inside each transaction and must not bypass RLS. Migration and real-PostgreSQL integration tests remain required before production account use. Secret rotation and broker-connection lifecycle operations can be added without changing the nonce replay contract.
