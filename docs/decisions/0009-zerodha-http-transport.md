# ADR 0009: Zerodha HTTP transport

- Status: approved
- Date: 2026-08-06
- Gate: Zerodha transport dependency
- Approved by: product owner

## Decision

Implement the production Kite transport directly against Zerodha's documented HTTP API using
constrained `httpx>=0.28,<0.29`. Use one injected asynchronous client with explicit timeouts,
connection limits, an endpoint allowlist, and typed error translation. Preserve response content
before normalization and keep retries in the connector policy rather than the HTTP library.

Do not depend on the official `kiteconnect` Python SDK. Do not expose generic URLs, arbitrary HTTP
verbs, WebSocket streaming, or trading endpoints.

## Rationale

The official SDK is synchronous, returns decoded Python values instead of replayable response
content, and includes legacy WebSocket dependencies that this read-only reporting connector does
not need. A small HTTP transport fits the approved asynchronous connector boundary and makes
read-only scope, provenance, throttling, and secret-safe behavior enforceable in our code.

## Consequences

We must maintain and contract-test the small set of approved endpoint mappings and update them when
Zerodha changes its documented API. Authentication headers and response bodies must never be
logged. Real-account validation still requires user-controlled interactive login; fixtures and the
official sandbox cover automated tests where available.
