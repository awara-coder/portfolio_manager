# ADR 0004: Security, privacy, and tenancy

- Status: proposed
- Date: 2026-08-05
- Gate: G4
- Approved by: pending

## Context

The system stores portfolio history, bank-statement data, account identifiers, and renewable broker tokens. It must be safe for local self-hosting and remotely exposed multi-user installations without assuming that a private network, container boundary, application bug, database role, or object store is independently sufficient protection.

## Options considered

1. Trust a single local user and filesystem permissions. Easy to operate, but unsafe when a port is exposed, a backup escapes, or multiple users are added.
2. Protect only at the application layer. Conventional, but one missing tenant predicate can expose another tenant's financial data.
3. Use deployment profiles plus layered authorization, database isolation, envelope encryption, minimized retention, and auditable deletion. More implementation and operational work, but appropriate for sensitive financial data and public self-hosting.

## Decision

Choose option 3. All real-data deployments require authentication. Authorization is deny-by-default and tenant-scoped in both application services and PostgreSQL. Secrets and highly sensitive artifacts use application-layer envelope encryption in addition to storage and transport protection.

### Deployment profiles

- `development` permits synthetic data only, binds to loopback by default, and may use explicit developer conveniences that cannot be enabled when real-data mode is active.
- `local` supports real data for one or more users, binds to loopback by default, and still requires authentication. Binding beyond loopback requires TLS termination and explicit server configuration.
- `server` assumes hostile networks, requires HTTPS, secure identity configuration, trusted proxy allowlisting, and production secret/key providers.
- The application fails closed on contradictory settings, default credentials, missing encryption keys, unsafe forwarded headers, or real-data use in `development`.

### Identity and authentication

- A user has a random internal identifier and may belong to multiple tenants through a membership with `owner`, `admin`, or `viewer` role. The first release may expose fewer roles but must not encode one-user-per-tenant assumptions.
- OIDC Authorization Code flow with PKCE is preferred for `server`; issuer, signature, audience, nonce, and redirect URI are strictly validated. Identity-provider tokens are not browser application sessions.
- Local credentials remain available for self-hosting without an identity provider. Passwords use Argon2id with versioned parameters, unique salts, breached/common-password blocking, no arbitrary periodic rotation, and no composition rules beyond a long minimum.
- Remotely exposed local-credential deployments require a phishing-resistant second factor such as WebAuthn/passkeys for privileged users. TOTP may be a compatibility fallback but is not treated as phishing-resistant.
- Bootstrap and recovery use one-time, short-lived CLI-generated grants or pre-generated recovery codes stored as hashes. There are no default passwords, security questions, or email-only privileged recovery.
- Login, recovery, and enrollment endpoints use generic errors, rate limits, attempt auditing, and step-up authentication for secret changes, exports, membership changes, and deletion.

### Browser sessions and CSRF

- Browser sessions use opaque, random, single-purpose tokens. Only a keyed hash is stored server-side; raw tokens exist only in `Secure`, `HttpOnly`, appropriately scoped cookies and are never stored in browser web storage.
- Session identifiers rotate after authentication and privilege changes. Logout, password reset, membership removal, or suspected compromise can revoke one or all sessions.
- Remote defaults are 30 minutes idle and 12 hours absolute lifetime; local deployments may opt into a documented longer absolute lifetime. Privileged actions always require recent authentication.
- State-changing requests require a CSRF token plus same-origin validation. `SameSite` cookies are an additional mitigation, not the sole defense. GET and HEAD remain side-effect free.
- Content Security Policy, frame restrictions, safe redirect allowlists, output encoding, and dependency-supported framework primitives reduce XSS and session theft risk.

### Tenant isolation and authorization

- Every sensitive aggregate root carries a non-null `tenant_id`; child ownership is enforced through foreign keys and repository contracts.
- Application entry points construct an immutable actor context containing user, tenant, role, purpose, and request/job correlation identifiers. Tenant identifiers supplied by clients never grant access.
- PostgreSQL row-level security is enabled and forced on tenant tables. Policies use transaction-local tenant context and both `USING` and `WITH CHECK` constraints.
- Runtime database roles are non-owner, non-superuser, and lack `BYPASSRLS`. Migration, backup, and break-glass roles are separate, unavailable to normal processes, and audited.
- API, worker, scheduled job, export, reconciliation, and administrative code use the same tenant-scoped repositories. Background jobs carry an explicit tenant and re-establish context inside each database transaction.
- Cross-tenant uniqueness and foreign-key errors are normalized to prevent identifier-existence leaks. Automated tests attempt reads, writes, joins, exports, jobs, and object access across tenants.

### Secret and key hierarchy

- Broker tokens, API credentials, webhook secrets, and provider keys are never stored as plaintext application columns, configuration committed to Git, logs, traces, URLs, browser state, or job payloads.
- Each encrypted value or artifact uses a random data-encryption key (DEK) and authenticated encryption. Ciphertext records include algorithm/key versions and bind tenant, object, and schema identity as associated data.
- DEKs are wrapped by a key-encryption key (KEK) through a versioned provider interface. Production providers may use cloud KMS or Vault. Local mode uses a separately mounted root key file with restrictive permissions; the key itself is never stored in PostgreSQL, object storage, images, or backups containing ciphertext.
- Only the worker-side connector boundary may unwrap broker credentials, just in time and for the intended connector operation. API, web, assistant, MCP, analytics, and reporting modules never receive broker credentials.
- Key access and secret lifecycle events record actor, purpose, version, and outcome without secret values. Rotation rewraps DEKs when possible; compromise can revoke credentials and replace affected keys.
- Nonces are generated according to the selected audited AEAD library and are never reused under the same key. The implementation does not invent cryptographic primitives or serialize ad hoc ciphertext formats.

### Data classification and minimization

- `public`: source code, public documentation, synthetic fixtures.
- `internal`: operational metadata that cannot identify a portfolio or person.
- `confidential`: normalized financial records, reports, email/name, pseudonymous account metadata.
- `restricted`: broker credentials, session/recovery tokens, full identifiers, raw broker payloads, bank statements, narrations, and exports.
- Restricted raw artifacts use application-layer encryption and per-object authorization. Confidential database fields use infrastructure encryption plus field encryption where disclosure would materially increase harm.
- Bank import is explicitly scoped by account, file/feed, and date range. Only relevant rows and required fields are normalized; unrelated rows are discarded before persistence where the parser can safely do so.
- Logs, metrics, traces, crash reports, support bundles, fixtures, issue templates, and telemetry exclude restricted values and portfolio amounts by default. Telemetry is disabled unless explicitly opted in and remains aggregate-only.

### Retention, export, and deletion

- Normalized records and report revisions are retained until tenant deletion or an explicit user policy because they form the auditable portfolio history.
- Default raw-artifact retention is 30 days for bank statements and 90 days for broker payloads after successful normalization and reconciliation. Users may shorten it; extensions require an explicit policy and visible storage/privacy impact.
- Expiry removes ciphertext and wrapped DEKs while retaining only non-sensitive hashes, lineage status, and parser/version metadata needed to explain that evidence expired.
- Export is asynchronous, tenant-scoped, encrypted at rest, short-lived, access-audited, and protected by recent authentication. Download URLs are single-purpose and expire quickly.
- Tenant deletion immediately revokes sessions, jobs, connector access, and key unwrapping; destroys tenant DEKs; then purges database rows, objects, exports, and search/cache copies through an idempotent tracked workflow.
- Backups are encrypted, access-tested, and expire within 30 days by default. Deletion tombstones survive backup restoration so restored data is re-deleted before service resumes. Physical media erasure follows the storage provider's guarantees.
- Legal or user-configured retention holds are explicit, visible, scoped, and auditable; this project does not silently invent a compliance obligation.

### Imports and untrusted content

- Documents are untrusted input: validate type by content, enforce size/page/row/time limits, isolate parsers without network access, and defend against archive bombs, path traversal, formulas, embedded content, and parser vulnerabilities.
- Original filenames are not storage paths. Derived names are opaque; rendered or extracted content is never executed.
- AI and MCP components cannot access raw documents, secrets, or unrestricted free-text narrations. Their data-sharing and prompt-injection policy remains gated by G9.

## Required verification

- Cross-tenant denial tests at service, repository, RLS, worker, export, and object-storage boundaries.
- Tests proving runtime roles cannot bypass RLS and connection-pool reuse cannot retain a previous tenant context.
- Session fixation, CSRF, logout/revocation, privilege-change, recovery, rate-limit, and cookie-attribute tests.
- Secret/redaction canary tests across responses, logs, traces, errors, jobs, support bundles, and browser state.
- Ciphertext tamper, wrong-tenant associated-data, rotation, provider outage, and key-loss recovery tests.
- Malicious document fixtures and resource-exhaustion limits.
- Retention, cryptographic erasure, export expiry, backup restore, and deletion-tombstone drills.

## Rejected shortcuts

- Authentication bypass for local real-data mode: loopback and home networks are not durable authorization boundaries.
- Long-lived JWTs in browser storage: revocation and XSS exposure are unacceptable for financial data.
- Environment variables as the only production secret store: they are easily inherited, dumped, or exposed through process tooling.
- Database encryption alone for raw artifacts and broker credentials: database/object-store compromise would reveal plaintext.
- RLS alone: owners and `BYPASSRLS` roles can bypass it, and policy/configuration mistakes still require application checks.
- Soft deletion alone: it neither fulfills deletion intent nor removes ciphertext from backups and object stores.

## Compatibility and migration effect

Tenant ownership and encryption metadata are required in the first production schema to avoid a dangerous retrofit. Authentication and KEK providers remain replaceable ports. Algorithm, password-hash, and ciphertext formats are versioned for gradual migration. Deployment-profile changes that weaken a control fail validation and require an explicit ADR revision.

## Consequences

Self-hosting requires management of an external root key and backup discipline. Multi-user authorization, RLS, encrypted artifacts, and deletion workflows increase testing and operational complexity. In return, common application mistakes do not immediately become cross-tenant or plaintext-secret disclosure, and users can minimize and delete highly sensitive evidence predictably.

Approval authorizes implementation of these controls; it does not approve real broker/bank integration until the relevant controls pass, Zerodha source policy until G7, or AI data sharing until G9.

## References

- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [OWASP Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
- [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [PostgreSQL row security policies](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [NIST SP 800-63B-4](https://doi.org/10.6028/NIST.SP.800-63B-4)
