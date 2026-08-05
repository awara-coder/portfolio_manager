# ADR 0006: Connector SDK contract

- Status: approved
- Date: 2026-08-05
- Gate: connector API approval
- Approved by: product owner

## Context

Zerodha, IBKR, synthetic, and optional future connectors need one stable application-facing contract without sharing broker payload models. Collection must be retryable, provenance-preserving, tenant-scoped, and explicit about partial success and authentication state.

## Proposed decision

Define the SDK as an application port with these broker-neutral types:

- `ConnectorDescriptor`: stable connector key, schema version, and declared capabilities.
- `Capability`: accounts, holdings, positions, balances, activities, instruments, prices, and tax lots. A connector declares only what it can collect.
- `AuthenticationState`: `ready`, `action_required`, `expired`, `revoked`, or `unavailable`, plus a safe reason code and optional expiry time. It never contains credentials or login URLs with secrets.
- `CollectionRequest`: tenant, connection, selected account, requested capabilities, optional UTC time range, opaque prior checkpoint, and idempotency key.
- `CollectionResult`: immutable raw artifacts, per-capability outcomes, proposed next checkpoint, source coverage, and safe issues. Partial success is a valid result rather than an exception.
- `RawArtifact`: bytes, media type, source timestamp, retrieval timestamp, connector/schema versions, and content digest. Its payload is excluded from representations and logs.
- `ConnectorError`: typed authentication, permission, rate-limit, transient, validation, unsupported, and permanent failures, with retry metadata but no sensitive payload.
- `Connector` protocol: asynchronous `describe`, `authentication_state`, and `collect` operations. Normalization is a separate versioned protocol so raw capture can succeed even when mapping fails.

Checkpoints are opaque to the application and versioned by the connector. The application persists a checkpoint only in the same transaction that accepts the corresponding collection result. Connectors cannot access repositories directly and cannot choose a tenant from ambient state.

## Compatibility

Adding an optional capability or result field is compatible. Removing or changing meaning requires a new SDK major version. Broker payload changes increment the connector schema version and retain replayable raw evidence. A reusable compliance suite verifies every connector against retries, duplicate requests, partial results, unknown fields, secret-safe errors, and checkpoint behavior.

## Consequences

The separation adds explicit mapping code but prevents Kite-specific concepts from leaking into IBKR or application services. Asynchronous collection supports bounded network concurrency without dictating the HTTP client. Raw evidence and normalization can evolve independently.

Approval authorizes implementation of these contracts and their compliance tests. It does not approve a stable public REST API, which remains under G5.
