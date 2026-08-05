# Threat model

This model covers the approved architecture before real financial data is accepted. It is maintained alongside material trust-boundary changes.

## Protected assets

- Broker credentials and renewable access tokens.
- Browser sessions, recovery codes, encryption keys, and signing material.
- Bank statements, broker payloads, account identifiers, and narrations.
- Normalized financial records, reports, exports, and portfolio metadata.
- Tenant membership, authorization policy, audit events, and deletion state.
- Integrity and availability of collection, reconciliation, and reporting.

## Actors

- Tenant owner, admin, and viewer.
- Instance operator with host or deployment access.
- API, worker, scheduler, browser, database, object store, identity provider, broker, and optional bank connector.
- External attacker, malicious tenant member, compromised dependency/provider, and accidental contributor/support recipient.

An instance operator can ultimately access process memory and replace application code. G4 reduces stored plaintext exposure and operator mistakes but does not claim protection from a persistently malicious host administrator while the system is running.

## Trust boundaries

1. Browser to HTTPS API.
2. API/worker to PostgreSQL, Redis, and object storage.
3. Worker connector boundary to secret/key provider and broker/bank services.
4. Tenant boundary inside application services, database rows, jobs, caches, objects, exports, and audit data.
5. Untrusted documents and broker payloads entering parser/normalizer isolation.
6. Operational boundary for backups, logs, telemetry, diagnostics, and support.
7. Future AI/MCP boundary, which remains closed to restricted data until G9.

## Primary threats and controls

| Threat | Key controls | Verification |
|---|---|---|
| Credential or session theft | HttpOnly secure cookies, opaque revocable sessions, short lifetimes, CSP, step-up auth, encrypted secrets | fixation, XSS-policy, revocation, and redaction tests |
| CSRF or confused-deputy action | CSRF token, origin validation, side-effect-free GET, explicit actor/tenant context | cross-origin request tests |
| Tenant escape/IDOR | deny-by-default authorization, scoped repositories, forced RLS, non-bypass runtime role | adversarial cross-tenant matrix |
| Connection-pool tenant bleed | transaction-local context, mandatory reset, fail-closed RLS | pool reuse and exception-path tests |
| Worker/job confused tenant | tenant-bound durable job payload references and context re-establishment | forged/replayed job tests |
| Database or object-store disclosure | envelope encryption, external KEK, least privilege, encrypted backups | wrong-key/tenant and storage-dump tests |
| Secret leakage through operations | structured allowlisted logs, canary redaction, no secret job payloads or URLs | scan logs, traces, errors, diagnostics, browser state |
| Malicious statement/document | content validation, limits, parser sandbox, no network, opaque paths | archive bomb, traversal, malformed and timeout fixtures |
| Source/prompt injection | typed normalization, no execution, raw text excluded from AI/MCP | hostile narration and payload tests; G9 review |
| Dependency/supply-chain compromise | lock files, pinned actions, review gates, provenance/SBOM and update policy | CI policy and release verification |
| Unauthorized export | recent auth, tenant scoping, short-lived encrypted artifact, audit | expiry and cross-tenant download tests |
| Incomplete deletion or resurrection | DEK destruction, purge state machine, backup expiry, deletion tombstones | deletion and restore drills |
| Data loss or key loss | encrypted tested backups, separately backed-up KEK procedure, restore runbook | scheduled restore drill |
| Availability/rate abuse | request/import limits, timeouts, backoff, quotas, bounded parsing | resource-exhaustion and retry tests |

## Residual risks

- A compromised running host can observe decrypted data and tokens used by the worker.
- Broker and identity-provider compromise are outside the application's control; least privilege, short lifetimes, reconciliation, and revocation reduce impact.
- Parsed statement classification can be wrong; provenance and reviewable confidence prevent it from silently becoming authoritative.
- Encrypted data is unavailable if root keys are lost. Setup must require a tested recovery procedure before unattended real-data operation.
- PostgreSQL constraints can reveal limited existence information across RLS boundaries; schema and error handling must avoid user-controlled global uniqueness where sensitive.

## Review triggers

Review G4 and this model before adding hosted service operation, new identity methods, write/trading capability, mobile clients, third-party connector execution, AI access to restricted data, new telemetry, shared exports, or a materially different key/storage provider.
