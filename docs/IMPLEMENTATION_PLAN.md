# Portfolio Manager Implementation Plan

Status: planning
Primary focus: IBKR and Zerodha
Secondary focus: optional Vested imports
Delivery model: self-hosted open-source modular monolith
Workflow: trunk-based development with short-lived Git worktrees

## 1. Purpose

Build a secure, scalable, and extensible portfolio intelligence platform that collects broker data, maintains an auditable portfolio ledger, produces reproducible daily reports, displays them in a browser, and answers portfolio questions through deterministic tools exposed to an embedded assistant and MCP clients.

The system prioritizes financial correctness, provenance, and transparent data quality over apparent completeness. Zerodha is the first production broker integration: it should use its official API when a valid interactive session exists and explicitly labeled reconstruction for unattended reporting. IBKR follows after the Zerodha exit criteria pass and should support unattended authoritative collection where its official services permit it. Vested remains optional and must not block the first production release.

## 2. Success criteria

The first stable release succeeds when a self-hosting user can:

1. Install the application using documented Docker Compose instructions.
2. Configure Zerodha without exposing credentials or automating interactive authentication.
3. Import or receive supported Zerodha activity documents for unattended reconstruction.
4. Connect an IBKR account through an approved integration and schedule unattended collection.
5. See combined and broker-specific holdings, balances, allocation, performance, and data quality in a responsive browser.
6. Open a permanent daily report with calculations, provenance, freshness, and warnings.
7. Ask supported natural-language questions and receive answers grounded in deterministic tools.
8. Use the same read-only tools through an MCP server.
9. Back up, restore, export, and delete their data using documented processes.
10. Run without any AI provider configured.

## 3. Non-goals for the initial release

- Trading or order management.
- Automated broker login, TOTP handling, or private endpoint scraping.
- Tax filing or jurisdiction-specific tax advice.
- Automated investment recommendations or rebalancing instructions.
- High-frequency or tick-level market data processing.
- Full Vested API parity.
- Native mobile or desktop applications.
- Microservices or Kubernetes as an installation requirement.

## 4. Proposed stack (subject to the approval gates below)

- Backend: Python 3.13+, `uv`, FastAPI, Pydantic.
- Persistence: PostgreSQL, SQLAlchemy 2, Alembic.
- Analytics: SQL, `Decimal`, Polars, property-based testing with Hypothesis.
- Jobs: Dramatiq with Redis; PostgreSQL for durable run state.
- Raw artifacts: S3-compatible object storage, with MinIO in local integration tests if needed.
- Web: Next.js, strict TypeScript, generated OpenAPI client, TanStack Query.
- Browser verification: Playwright.
- AI/MCP: provider-neutral tool interface and official MCP SDK.
- Observability: structured logging and OpenTelemetry.
- Packaging: Docker Compose first; optional Helm deployment after the core is stable.

Dependency versions and exact libraries are chosen and pinned during bootstrap after compatibility checks. Alternatives that materially alter architecture require an ADR and user approval.

## 5. Delivery principles

- Complete one verifiable increment at a time; no big-bang implementation.
- Parallelize only work with settled boundaries and disjoint ownership.
- Put approval gates before implementation that would freeze a major contract.
- Use synthetic and sanitized data until security, retention, and deletion controls are approved.
- Treat raw inputs and normalized financial events as immutable evidence.
- Make every scheduled operation idempotent and retry-safe.
- Keep structured reports independent of AI-generated narrative.
- Keep `main` releasable after every integration.

## 6. Approval gates and ADRs

Create ADRs under `docs/decisions/` using the template established in Phase 0. An ADR progresses through `proposed`, `approved`, `superseded`, or `rejected`. Only the user can supply the required product-owner approval for the following gates.

| Gate | Decision | Required before |
|---|---|---|
| G0 | Repository license and contribution model — approved in ADR 0001 | Public release preparation |
| G1 | System boundaries and module dependency rules — approved in ADR 0002 | Phase 1 implementation |
| G2 | Canonical data, ledger, snapshot, identifiers, and provenance model | Schema/domain implementation |
| G3 | Financial calculations, cash flows, FX, rounding, valuation cutoff, and benchmark semantics | Analytics implementation |
| G4 | Authentication, tenant isolation, secret storage, privacy, retention, and deletion model | Real account integration |
| G5 | REST API conventions and initial OpenAPI contracts | API and web feature implementation |
| G6 | IBKR data sources, authorization, collection schedule, and reconciliation policy | IBKR production connector |
| G7 | Zerodha API/reconstruction sources, authentication UX, and confidence policy | Zerodha production connector |
| G8 | Browser information architecture and visual/report specification | Production dashboard implementation |
| G9 | LLM providers, data-sharing boundary, MCP tools, audit behavior, and AI threat model | AI/MCP production integration |
| G10 | Backup, restore, deployment, telemetry, and release security model | First public release |

Each proposal must include context, options, recommendation, trade-offs, security/privacy effect, compatibility effect, migration implications, and concrete examples. Approval applies to the recorded revision; material changes return the ADR to `proposed`.

### 6.1 Broker implementation order

The mandatory broker sequence is Zerodha first, then IBKR. Phase 4 may be researched while Phase 3 is in progress only when that work cannot influence unapproved shared contracts, but no IBKR production implementation begins until the Zerodha Phase 3 exit criteria pass or the user explicitly approves an exception. The broker reference chapters below retain independent detail; phase numbers, gates, and the progress ledger—not their physical proximity in this document—define execution order.

## 7. Worktree execution model

### 7.1 Repository initialization

The current directory was not a Git repository when this plan was created. Phase 0 deliberately initializes Git, establishes `main`, and adds the first verified baseline. Do not create worktrees until that baseline exists.

### 7.2 Branch lifecycle

For each ready task:

1. Pull or inspect the latest `main`.
2. Claim the task in the worktree ledger.
3. Create a short-lived branch from `main`.
4. Add its worktree under `../portfolio_manager-worktrees/`.
5. Implement only the claimed scope.
6. Run task-specific tests and repository-wide affected checks.
7. Update documentation and progress records.
8. Rebase onto current `main` and rerun checks.
9. Review and integrate one branch at a time.
10. Run post-integration checks on `main`.
11. Mark the task done, then remove the worktree and branch safely.

Suggested commands are documented later during repository bootstrap; do not blindly run examples when paths or branch ownership are uncertain.

### 7.3 Parallel work rules

Parallel work is permitted when:

- Dependencies and approval gates are complete.
- Each branch has a single owner and disjoint file ownership.
- Shared schemas/interfaces are already approved and protected by contract tests.
- Integration order is stated before implementation begins.
- Each branch is independently testable and safe to merge.

Examples of safe parallelism after contracts are settled:

- IBKR fixture normalization and dashboard component primitives.
- Backend API implementation and generated-client verification.
- Documentation and test-infrastructure improvements.
- Different connector failure fixtures owned by separate branches.

Examples of unsafe parallelism:

- Two branches independently defining the canonical transaction model.
- API and UI branches guessing different response schemas.
- Concurrent migrations using the same Alembic parent revision.
- Multiple agents editing the same progress table without coordination.

### 7.4 Worktree ledger

Update this table before beginning work. Use agent/task identifiers rather than personal data.

| Task | Branch | Worktree | Owner | Depends on | Status | Last update |
|---|---|---|---|---|---|---|
| Planning baseline | `main` | repository root | primary agent | none | in progress | 2026-08-05 |
| Worktree smoke test | `docs/worktree-smoke` | `/private/tmp/portfolio-manager-worktrees/docs-worktree-smoke` | primary agent | Planning baseline | done | 2026-08-05 |
| Record G0/G1 decisions | `docs/approve-g0-g1` | `/private/tmp/portfolio-manager-worktrees/approve-g0-g1` | primary agent | G0 and G1 approval | done | 2026-08-05 |
| Configure code ownership | `chore/configure-codeowners` | `/private/tmp/portfolio-manager-worktrees/configure-codeowners` | primary agent | GitHub owner supplied | done | 2026-08-05 |
| Governance baseline | `docs/governance-baseline` | `/private/tmp/portfolio-manager-worktrees/governance-baseline` | primary agent | G0/G1 approved | done | 2026-08-05 |
| Python workspace bootstrap | `chore/python-workspace-bootstrap` | `/private/tmp/portfolio-manager-worktrees/python-workspace-bootstrap` | primary agent | G1 approved | done | 2026-08-05 |
| Propose G2 data model | `docs/propose-g2-data-model` | `/private/tmp/portfolio-manager-worktrees/g2-data-model` | primary agent | Python workspace bootstrap | done | 2026-08-05 |
| Propose G4 security model | `docs/propose-g4-security` | `/private/tmp/portfolio-manager-worktrees/g4-security` | primary agent | G2 approved | done | 2026-08-05 |
| Domain value objects | `feat/domain-value-objects` | `/private/tmp/portfolio-manager-worktrees/domain-value-objects` | primary agent | G2/G4 approved | done | 2026-08-05 |
| Tenant-owned domain entities | `feat/domain-ownership` | `/private/tmp/portfolio-manager-worktrees/domain-ownership` | primary agent | Domain value objects | done | 2026-08-05 |
| Immutable activity model | `feat/domain-activities` | `/private/tmp/portfolio-manager-worktrees/domain-activities` | primary agent | Tenant-owned domain entities | done | 2026-08-05 |
| Immutable observation model | `feat/domain-observations` | `/private/tmp/portfolio-manager-worktrees/domain-observations` | primary agent | Immutable activity model | done | 2026-08-05 |
| Record G7 and propose connector contract | `docs/approve-g7-connector-contract` | `/private/tmp/portfolio-manager-worktrees/approve-g7-connector-contract` | primary agent | G7 product-owner approval | done | 2026-08-05 |
| Connector SDK contract | `feat/connector-sdk` | `/private/tmp/portfolio-manager-worktrees/connector-sdk` | primary agent | ADR 0006 approved | done | 2026-08-05 |
| Zerodha connector foundation | `feat/zerodha-connector-foundation` | `/private/tmp/portfolio-manager-worktrees/zerodha-connector-foundation` | primary agent | Connector SDK contract and G7 approved | done | 2026-08-06 |
| Zerodha HTTP transport | `feat/zerodha-http-transport` | `/private/tmp/portfolio-manager-worktrees/zerodha-http-transport` | primary agent | ADR 0009 approved | in review | 2026-08-06 |

Valid states: `planned`, `blocked`, `ready`, `in progress`, `in review`, `integrating`, `done`.

Only one owner edits a claimed task. If ownership changes, record the handoff before the new owner continues.

## 8. Phase 0 — Repository and governance baseline

Goal: establish a safe, reproducible repository in which multiple contributors and agents can work without inventing process along the way.

### 0.1 Initialize repository and main branch

Deliverables:

- Initialize Git with `main` as the default branch.
- Commit `AGENTS.md` and this implementation plan as the baseline.
- Add editor, line-ending, and ignore configuration.
- Define the merge policy and conventional commit expectations.
- Document worktree creation, inspection, rebasing, integration, and cleanup.

Tests and checks:

- Fresh clone contains the rules and plan.
- No secrets, caches, OS files, or local environment files are tracked.
- A disposable worktree can run the repository's initial validation command.

Exit criteria:

- Git baseline exists on `main`.
- Worktree workflow has been exercised once with a documentation-only branch.

### 0.2 Establish decision and contribution process

Deliverables:

- ADR directory, index, and template.
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, and initial `SECURITY.md`.
- Issue and pull-request templates capturing approvals, tests, migrations, and privacy impact.
- Decision on Apache-2.0 versus AGPL-3.0 at G0.

Tests and checks:

- Template validation or documentation lint passes.
- A sample proposed ADR demonstrates the approval workflow.

Approval gate:

- G0 before applying the release license.

### 0.3 Bootstrap monorepo tooling

Deliverables:

- Python workspace using `uv` and a pinned supported Python range.
- Next.js workspace with strict TypeScript.
- Root commands for format, lint, type-check, unit test, integration test, browser test, build, and full verification.
- Pre-commit hooks or equivalent fast local validation.
- CI with dependency caching and concurrency cancellation.
- Renovation/dependency-update policy.

Tests and checks:

- Clean installation from lockfiles in CI.
- Backend and frontend sample tests pass.
- Production builds contain no development secrets.
- Generated artifacts are reproducible or checked for drift.

Exit criteria:

- A new contributor can clone and run the fast verification suite using documented commands.

### 0.4 Define module boundaries

Deliverables:

- Proposed package tree and allowed dependency directions.
- G1 ADR describing modular-monolith boundaries and extraction criteria.
- Machine-readable dependency policy and automated boundary checks in required CI.
- Separate `uv` workspace packages with declared internal dependencies, Import Linter contracts, and local pre-commit enforcement.
- Designated-owner review for boundary policy, enforcement, security, schemas, and workflows once repository ownership is configured.

Approval gate:

- G1 approved in ADR 0002. Boundary checks must remain green before implementing domain packages.

## 9. Phase 1 — Security and domain foundations

Goal: agree on correctness and trust boundaries before accepting real financial data.

### 1.1 Threat model and data classification

Deliverables:

- Assets, actors, trust boundaries, threats, and mitigations.
- Classification of secrets, personal information, financial records, derived analytics, logs, and public metadata.
- Local-only, self-hosted multi-user, and hosted deployment threat scenarios.
- Policy for sanitized fixtures and support diagnostics.

Tests and checks:

- Threat cases cover credential theft, tenant escape, malicious imports, dependency compromise, prompt injection, and accidental telemetry leakage.
- Every sensitive data class has retention, encryption, logging, and deletion expectations.

### 1.2 Authentication, tenants, and secret management proposal

Deliverables:

- User/session model.
- Tenant and account ownership model.
- Active-tenant invariant requiring at least one active owner membership.
- Local development secret backend and production secret-manager interface.
- Envelope-encryption key hierarchy and rotation proposal.
- Browser cookie, CSRF, session expiry, and recovery design.

Tests and checks:

- Tenant creation atomically creates its first owner membership.
- Removing, disabling, or demoting the last active owner fails with a stable error.
- Ownership transfer promotes the successor before changing the prior owner in one transaction.
- Concurrent last-owner changes serialize on the tenant and cannot commit an abandoned active tenant.
- Tenant deletion is the only controlled exception and follows the approved revocation and purge workflow.
- PostgreSQL uses a deferred commit-time invariant as a backstop to application authorization.

Approval gate:

- G4 design approval may occur here; real-account use remains blocked until its implementation tests pass.

### 1.3 Canonical domain model proposal

Model at minimum:

- User, tenant, broker connection, institution, broker account.
- Instrument identity, listings, identifiers, asset class, multiplier, currency.
- Cash account, balance observation, transaction, trade, income, fee, tax, transfer, corporate action.
- Position/holding observation, tax lot where available, price observation, FX observation.
- Collection run, raw artifact, normalized batch, source record, reconciliation result.
- Portfolio snapshot, report, report revision, benchmark observation.
- Provenance, confidence, completeness, and freshness.

Questions the ADR must settle:

- Event ledger versus observation semantics and how they coexist.
- External and internal identifiers, deduplication, and corrections.
- Fractional quantities, shorts, derivatives, multipliers, and expiration.
- Native, account-base, and user-reporting currencies.
- Trade date, settlement date, effective date, and ingestion time.
- Corporate action and off-market transfer representation.
- Linked inbound and outbound broker-transfer sides, including full and partial ACATS transfers of securities and cash.
- Late or corrected transfer-lot cost basis, residual cash sweeps, ineligible assets, and fractional-share liquidation without treating a transfer as a trade.
- Immutable correction and supersession behavior.

Tests before approval:

- Walk through synthetic buy, sell, dividend, fee, deposit, withdrawal, split, transfer, option, and FX cases.
- Demonstrate idempotent re-import and corrected-source handling.
- Demonstrate that missing data cannot silently become zero.

Approval gate:

- G2. No production domain classes or database schema before approval.

### 1.4 Financial semantics proposal

Deliverables:

- Money, quantity, price, and FX precision policy.
- Rounding policy by calculation and display boundary.
- Daily gain/loss, realized/unrealized P&L, money-weighted return, and time-weighted return definitions.
- Cash-flow timing and valuation-cutoff rules.
- FX return attribution and base-currency conversion rules.
- Benchmark comparison and unavailable-data behavior.

Tests before approval:

- Independently computed worked examples, including cross-currency cash flows.
- Boundary cases for zero value, missing prior price, non-trading day, partial day, and stale source.

Approval gate:

- G3 before analytics implementation.

### 1.5 Implement approved primitives

May begin only after G1–G4 relevant sections are approved.

Deliverables:

- Domain value objects and invariant tests.
- Initial PostgreSQL schema and Alembic migration.
- Repository interfaces and transaction boundaries.
- Raw artifact interface and local S3-compatible adapter.
- Secret-redacted structured logging.

Tests and checks:

- Unit and property tests for money, quantities, currencies, dates, identifiers, and idempotency.
- Migration up/down or forward-recovery tests according to approved policy.
- PostgreSQL integration tests using the real engine, not SQLite substitutes.
- Cross-tenant access denial tests.
- Secret-redaction tests.

Exit criteria:

- Approved examples can be represented without broker-specific leakage into the domain.
- Foundation checks pass in a clean container.

## 10. Phase 2 — Ingestion framework and synthetic vertical slice

Goal: prove the complete pipeline with synthetic data before connecting a real broker.

### 2.1 Connector SDK

Deliverables:

- Capability declaration contract.
- Authentication-state and health contracts.
- Collection request/result, pagination, checkpoint, and raw-artifact contracts.
- Error taxonomy: authentication, permission, rate-limit, transient, validation, unsupported, and permanent.
- Versioning and compatibility policy for third-party connectors.

Tests and checks:

- Connector compliance suite reusable by every adapter.
- Simulated pagination, timeout, retry, duplicate batch, partial response, and unknown enum cases.
- Type and import-boundary checks.

### 2.2 Durable job framework

Deliverables:

- PostgreSQL collection-run state machine.
- Dramatiq/Redis delivery adapter.
- Idempotency, concurrency lock, retry/backoff, timeout, and dead-letter behavior.
- External scheduling entry point.

Tests and checks:

- Process crash and retry do not duplicate financial records.
- Concurrent duplicate jobs result in one effective collection.
- Redis loss does not erase durable success/failure history.
- Partial connector success remains visible.

### 2.3 Synthetic broker connector

Deliverables:

- Deterministic synthetic accounts with INR and USD instruments.
- Trades, unsettled cash flows, dividends, typed fees/taxes, fractional shares, shorts, derivatives, stale source coverage, historical FX conversions, bank-statement rows, and a corporate action.
- Failure modes configurable for demonstrations and tests.

Tests and checks:

- Golden normalized outputs.
- Repeatable snapshots for fixed clocks and seeds.
- A report retrieved today but covering yesterday remains stale and provisional.
- T+1/T+2 and calendar-driven settlement examples do not create false cash discrepancies.
- Cross-currency round trips preserve historical conversions, explicit fees, and TCS as separate facts.
- No real-looking credentials or personal data.

### 2.4 Minimal end-to-end vertical slice

Deliverables:

- Collect synthetic data.
- Normalize and store it.
- Build one structured daily snapshot.
- Expose a temporary internal read endpoint.
- Render a minimal browser report page.

Approval gate:

- G5 approves the API conventions before the endpoint becomes a stable contract.

Exit criteria:

- One command starts dependencies and services.
- One command runs the synthetic collection.
- A browser displays the expected report.
- Unit, integration, contract, and one Playwright flow pass.

This phase is the earliest proof that all major layers integrate; do not begin real broker collection before it passes.

## 11. Phase 4 — IBKR integration

Goal: deliver unattended, authoritative IBKR collection through supported interfaces.

### 4.1 IBKR discovery and ADR

Evaluate:

- Flex Web Service report sections and generation/polling behavior.
- Web API requirements and whether current positions add necessary value.
- Account structures, base currencies, subaccounts, fractional shares, options, futures, bonds, and cash.
- Token lifecycle, rate limits, report availability, corrections, and paper-account limitations.
- Required user setup and least-privilege permissions.

Deliverables:

- Mapping matrix from IBKR fields to the proposed canonical model.
- Sanitized representative fixtures for supported asset/activity types.
- G6 ADR selecting Flex-only or Flex plus Web API for the first release.

Approval gate:

- G6 before production connector implementation.

User-assisted integration testing likely required:

- The user configures an IBKR Flex query and token locally.
- The user confirms behavior for their account and enabled asset classes.
- Only sanitized fixtures or structural findings enter the repository.

### 4.2 Flex connector

Deliverables:

- Secret configuration and validation.
- Report request, polling, download, checksum, raw storage, and parsing.
- Pagination/report-period checkpointing where applicable.
- Normalization for approved sections.
- Error classification and observability.

Tests and checks:

- Golden XML/CSV fixture tests.
- Malformed, truncated, delayed, empty, duplicate, corrected, and rate-limited report tests.
- Parser resource limits and malicious-document tests.
- Sandbox/real-account smoke test performed locally by the user when required.

### 4.3 Optional IBKR Web API increment

Implement only if G6 selects it and Flex cannot meet approved freshness requirements.

Deliverables and tests:

- Supported authentication flow without credential automation.
- Accounts, paginated positions, and balances required by the approved scope.
- Reconciliation between Web API observations and Flex activity.
- Session-loss and delayed-data behavior.

### 4.4 IBKR scheduled collection and reconciliation

Deliverables:

- Daily schedule configuration with timezone and availability windows.
- Backfill and resume from checkpoint.
- Reconciliation of observations against transaction-derived state.
- Data-quality dashboard state and alerts.

Exit criteria:

- Repeated daily jobs are idempotent.
- Backfill produces the same normalized result as incremental collection.
- Real-account user-assisted validation covers at least holdings, cash, trades, dividends, fees, and FX relevant to the account.
- Secrets never appear in logs, browser output, or test artifacts.

## 12. Phase 3 — Zerodha integration

Goal: combine official session-based API observations with safe unattended reconstruction.

### 3.1 Zerodha discovery and ADR

Evaluate:

- Kite holdings, positions, trades, orders, funds, instruments, quotes, and historical data needed for reporting.
- Daily token expiry and interactive callback UX.
- Which official activity documents or exports can be ingested automatically or from a watched input.
- Settlement behavior, T1 holdings, collateral, discrepancies, derivatives, and corporate actions.
- Reconstruction limits and reconciliation confidence rules.

Deliverables:

- Field mapping and data-quality matrix.
- Explicit list of authoritative, reconstructed, estimated, stale, and unsupported fields.
- G7 ADR covering authentication and unattended-mode behavior.

Approval gate:

- G7 before production connector implementation.

User-assisted integration testing required:

- The user completes Kite authentication locally.
- The user validates holdings/positions/funds behavior against the official UI.
- The user provides sanitized structure or locally runs parsers against representative contract notes/exports.
- Credentials, TOTP seeds, full statements, and account identifiers must not be shared.

### 3.2 Kite connector

Deliverables:

- Interactive authorization callback and token lifecycle state.
- Read-only holdings, positions, trades, and funds collection within approved scope.
- Instrument reference-data update process.
- Raw response storage, normalization, rate limiting, and errors.

Tests and checks:

- Sandbox or approved mock contract tests.
- Expired token, incomplete login, rate limit, unknown instrument, partial response, and market-closed behavior.
- Authentication state is visible without leaking sensitive details.
- No automated login or token fabrication.

### 3.3 Zerodha activity/document ingestion

Deliverables:

- Approved local upload, watched-folder, or email-derived ingestion boundary.
- Strict file validation, duplicate detection, parser isolation, and raw storage.
- Parser and mapping for approved document formats.
- Correction/version behavior when broker formats or documents change.

Tests and checks:

- Sanitized golden files for buys, sells, charges, taxes, derivatives, and empty days as supported.
- Password-protected, malformed, oversized, duplicate, and malicious file cases.
- Parser upgrades can replay stored versions deterministically.

### 3.4 Reconstruction and reconciliation

Deliverables:

- Transaction-derived holdings and cash state.
- Price/FX enrichment through approved providers.
- Comparison against the latest authoritative Kite observation.
- Confidence/freshness downgrade rules and visible discrepancy explanations.

Tests and checks:

- Multi-day property tests conserve quantities and cash under the approved model.
- Settlement, partial fills, fees, stale prices, missing documents, and corporate-action gaps are visible.
- Reconstruction never silently overwrites authoritative observations.

### 3.5 Bank-statement ingestion and cash reconciliation

Deliverables:

- Explicitly scoped local import and a connector interface for future read-only bank feeds.
- Parsers that extract selected date ranges and relevant rows without requiring unrelated statement data to be normalized.
- Typed bank, FX, platform, brokerage, regulatory, and tax/TCS charge records with source provenance.
- Confidence-bearing reconciliation between bank entries, broker funding/withdrawal activity, and currency conversions.
- Review flow for ambiguous, partial, one-to-many, and many-to-one matches.

Tests and checks:

- Sanitized fixtures cover INR-to-foreign-currency funding, sale proceeds, remittance, TCS, explicit FX/bank fees, bundled charges, reversals, and duplicate statements.
- Raw account numbers and narrations never enter logs, diagnostics, committed fixtures, or browser URLs.
- Unrelated rows remain excluded; an unmatched entry remains visible rather than being forced into a broker activity.
- Historical INR attribution uses transaction/conversion evidence and never today's FX rate for historical cost.

Approval gates:

- G4 before importing real statements or retaining sensitive raw artifacts.
- G3 before treating any charge as performance cost, tax credit, or FX attribution in analytics.

Exit criteria:

- Daily reports continue unattended after a Kite token expires, clearly labeled as reconstructed or stale.
- A later interactive reconciliation explains discrepancies without rewriting history.
- Approved bank imports can reconcile funding, withdrawals, conversions, fees, and TCS without ingesting unrelated rows into the canonical model.
- User-assisted tests confirm approved behavior on the user's account.

## 13. Phase 5 — Pricing, FX, and portfolio analytics

Goal: produce independently tested, reproducible calculations for combined portfolios.

### 5.1 Market-data provider ADR and connectors

Decide:

- Official broker prices versus independent providers.
- Exchange coverage, adjusted prices, licensing, quotas, and historical retention.
- FX source, observation time, weekend behavior, and rate direction.
- Cache and fallback policy.

This is approval-gated if it changes cost, licensing, privacy, or G3 semantics.

Tests and checks:

- Symbol mapping across exchanges and currencies.
- Split/adjustment behavior.
- Missing, stale, outlier, and provider-disagreement cases.

### 5.2 Ledger and snapshot engine

Deliverables:

- Position and cash reconstruction under approved semantics.
- Immutable end-of-day snapshot creation.
- Superseding correction flow.
- Snapshot lineage back to source records, prices, and FX observations.

Tests and checks:

- Property tests for quantity/cash conservation and idempotency.
- Golden multi-broker portfolios.
- Same input and valuation cutoff produce the same snapshot.

### 5.3 Performance and attribution

Deliverables:

- Daily P&L and approved return measures.
- Realized/unrealized breakdown.
- Income, fees, taxes, external cash flow, market movement, and FX attribution.
- Broker, account, asset class, geography, sector, currency, and instrument grouping.
- Benchmark comparison if approved data is available.

Tests and checks:

- Independently calculated expected cases.
- Cross-currency deposits and withdrawals.
- Non-trading days and mismatched exchange calendars.
- Missing prices and partial broker coverage.
- Performance regression benchmarks for representative datasets.

Exit criteria:

- Every displayed aggregate can be traced to inputs and formulas.
- Unsupported calculations return an explicit unavailable result, not a plausible-looking number.

## 14. Phase 6 — API and browser dashboard

Goal: expose approved information safely in a responsive, accessible browser experience.

### 6.1 Information architecture and report specification

Propose and obtain G8 approval for:

- Overview dashboard.
- Holdings explorer.
- Performance and attribution views.
- Broker/account health and reconciliation.
- Daily report archive and report detail.
- Collection history and settings.
- Ask-your-portfolio interface placeholder.
- Mobile navigation and accessibility behavior.

Provide wireframes using synthetic data before production UI implementation.

### 6.2 REST API contracts

After G5 approval, implement versioned resources for:

- Portfolio summary and allocation.
- Holdings and transactions.
- Performance series and attribution.
- Daily reports and revisions.
- Connector status, collection runs, and reconciliation.
- Job requests and status.
- User-safe settings and exports.

Tests and checks:

- OpenAPI snapshot and compatibility tests.
- Authorization and cross-tenant denial.
- Cursor pagination, filtering, stable error envelopes, decimal serialization, and timezones.
- Bounded query and response sizes.

### 6.3 Web application foundation

Deliverables:

- Authenticated application shell.
- Generated API client.
- Design tokens, accessible components, currency/date formatting, and status vocabulary.
- Loading, empty, stale, partial, error, and unauthorized states.

Tests and checks:

- Type-check, lint, component tests, accessibility checks, and production build.
- No secret or server-only dependency in client bundles.

### 6.4 Overview and holdings

Deliverables:

- Combined net worth and daily change.
- Broker allocation and health.
- Asset/geography/sector/currency allocation.
- Contributor/detractor summaries.
- Searchable, sortable, filterable holdings table.
- Native and reporting-currency values.
- Visible source, freshness, and reconciliation state.

Browser tests:

- Desktop and mobile critical paths.
- Keyboard navigation and screen-reader labels.
- Large portfolio pagination/virtualization behavior if needed.
- Partial broker failure and stale Zerodha state.

### 6.5 Performance and daily reports

Deliverables:

- Portfolio value and return charts.
- Cash flow, income, fee, and FX attribution views.
- Permanent `/reports/<date>` pages.
- Structured report metadata and revision history.
- Markdown and JSON exports; PDF follows its own render/visual verification increment.

Browser tests:

- Cross-timezone date behavior.
- Text alternatives for charts.
- Export content matches the structured report.
- Visual regression at selected viewports after design stabilizes.

Exit criteria:

- A user can understand both portfolio performance and data limitations without reading logs.
- The critical dashboard and report flows pass Playwright against a production build.

## 15. Phase 7 — Assistant and MCP

Goal: answer questions using narrow, auditable, deterministic read-only tools.

### 7.1 Tool contract proposal

Propose tools such as:

- `get_portfolio_summary`
- `get_holdings`
- `get_performance`
- `explain_daily_change`
- `compare_accounts`
- `get_allocation`
- `get_income_and_fees`
- `get_data_quality`
- `get_report`

Each proposal defines scope, authorization, parameters, bounds, output schema, provenance, and failure behavior.

Approval gate:

- G9 before exposing real portfolio data to an LLM or MCP client.

### 7.2 Deterministic application tools

Deliverables:

- Provider-independent application services implementing approved tools.
- Stable schemas and limits.
- Calculation/source references in every result.

Tests and checks:

- Golden tool outputs.
- Authorization, tenant isolation, date and result bounds.
- No arbitrary SQL or raw document access.

### 7.3 Browser assistant

Deliverables:

- Provider configuration with explicit data-sharing disclosure.
- Tool-calling orchestration.
- Answer citations to reports, dates, and freshness.
- AI-disabled and provider-failure behavior.

Security tests:

- Prompt injection from document text and instrument metadata.
- Attempts to obtain secrets, other tenants' data, unrestricted raw records, or unsupported advice.
- Hallucinated numeric claims are rejected or unsupported by tool results.

### 7.4 MCP server

Deliverables:

- Read-only MCP transport over the same application services.
- Authentication and local/remote deployment guidance.
- Tool discovery schemas and compatibility tests.

Tests and checks:

- MCP conformance and end-to-end client test.
- Browser assistant and MCP return equivalent structured results for identical authorized queries.
- Cancellation, timeout, oversized query, and unauthorized client cases.

Exit criteria:

- The assistant cannot change portfolio state.
- Answers cite deterministic outputs and make incomplete data obvious.
- Core product works with AI disabled.

## 16. Phase 8 — Operational hardening and open-source release

Goal: make installation, upgrades, recovery, and public collaboration safe.

### 8.1 Docker Compose distribution

Deliverables:

- Pinned, non-root production images.
- Health/readiness checks.
- Persistent PostgreSQL and object-storage configuration.
- Explicit secret injection and first-run setup.
- Resource guidance for a personal installation.

Tests and checks:

- Clean-machine smoke test.
- Restart during collection.
- Upgrade from the previous release candidate.
- No default credentials in production configuration.

### 8.2 Backup, restore, export, and deletion

Deliverables:

- Consistent PostgreSQL plus object-store backup procedure.
- Restore verification and version compatibility.
- User data export.
- Approved deletion and retention workflow.

Approval gate:

- G10 before declaring release readiness.

Tests and checks:

- Automated backup/restore drill with checksum comparison.
- Deleted tenant is inaccessible and scheduled for artifact cleanup according to approved retention semantics.
- Encryption-key recovery and rotation procedures are documented and tested safely.

### 8.3 Observability and supportability

Deliverables:

- OpenTelemetry traces and metrics for API, collection, parsing, snapshots, reports, and tools.
- Structured redacted logs and correlation IDs.
- Health dashboard/runbook for common broker failures.
- Privacy-preserving diagnostic bundle.

Tests and checks:

- Inject representative failures and verify actionable diagnostics.
- Automated scan confirms test secrets and sensitive fields are redacted.

### 8.4 Supply-chain and release security

Deliverables:

- Dependency, secret, static-analysis, and container scans.
- SBOM and provenance for releases.
- Signed tags/images where supported.
- Vulnerability disclosure and patch policy.
- License/notice review for optional connectors and market-data providers.

### 8.5 Documentation and demonstration

Deliverables:

- Architecture, installation, configuration, upgrade, backup, and troubleshooting guides.
- Connector-authoring guide and compliance test suite documentation.
- Synthetic demo mode with a compelling browser report.
- Known limitations, data-quality semantics, and financial-methodology documentation.

Exit criteria:

- A new user can install and explore the synthetic demo without broker credentials.
- A contributor can add a synthetic connector using documented interfaces.
- Release checklist passes from a clean checkout.

## 17. Phase 9 — Optional increments after the first stable release

These do not block the core release:

- Vested CSV/statement connector.
- DriveWealth/Vested-to-IBKR ACATS reconciliation: link independently sourced account sides, retain one-sided transfers as incomplete, and reconcile transferred lots when IBKR cost-basis evidence arrives.
- Email connector for supported broker documents after a separate privacy/security approval.
- PDF daily report delivery.
- Notification channels.
- Helm chart and multi-replica deployment.
- Temporal evaluation if workflow durability requirements outgrow Dramatiq.
- TimescaleDB evaluation if measured price-history workloads justify it.
- Additional brokers through the connector SDK.
- Tax-lot and jurisdiction-specific export modules, explicitly not tax advice.

Each optional increment receives its own scoped plan, threat review, and approval gates.

## 18. Cross-phase test gates

No phase is complete until all applicable gates pass:

| Gate | Required evidence |
|---|---|
| Format/lint | Canonical formatter and linters pass without unexplained ignores |
| Types | Strict Python and TypeScript checks pass for changed production code |
| Unit | Domain and boundary unit tests pass |
| Property | Relevant invariants pass over generated cases |
| Integration | Real PostgreSQL/Redis/object storage paths pass where relevant |
| Contract | OpenAPI, connector, and MCP schemas pass compatibility checks |
| Migration | Empty and supported upgrade paths pass |
| Browser | Critical Playwright flows pass against a production build |
| Accessibility | Automated checks plus documented keyboard/manual verification |
| Security | Authorization, tenant, secret, upload, and injection checks pass as applicable |
| Performance | Agreed dataset sizes meet documented budgets without unbounded queries |
| Recovery | Relevant retry, crash, backup, or restore scenario passes |
| Documentation | User/admin/contributor docs reflect the delivered behavior |
| Approval | Required ADRs show explicit user approval |

Tests should run in layers: fast checks on every branch update, affected integration tests before review, full suite before integration when feasible, and post-merge verification on `main`.

## 19. User-assisted integration test checkpoints

The agent must ask for user help at these points because real credentials must remain under user control:

### Zerodha

- Complete the official interactive login locally.
- Run the connector smoke test during the token's valid session.
- Compare summarized holdings, positions, and funds with the official interface.
- Run document parsers locally on representative source files and share only sanitized discrepancies.

### IBKR

- Create/confirm the approved Flex query configuration.
- Store the token only in the user's local secret backend.
- Run the provided integration command locally.
- Confirm account/asset coverage and provide sanitized failures if any.

### Market data and FX

- Supply provider credentials locally if the approved provider requires them.
- Confirm licensing and expected exchange coverage for the user's instruments.

### Release validation

- Perform one end-to-end daily run in the intended deployment environment.
- Confirm timezone, cutoff, report totals, and data-quality labels.
- Participate in backup/restore acceptance before relying on the system.

Agents must never ask the user to paste broker secrets, TOTP seeds, raw cookies, full statements, or unredacted account information into chat, issues, commits, or fixtures.

## 20. Definition of done

A task is done when:

- Its prerequisite approvals and dependencies are complete.
- Acceptance criteria and failure behavior are implemented.
- Relevant automated and manual tests pass.
- Security, privacy, migration, observability, and compatibility effects are addressed.
- Documentation, ADRs, generated contracts, and the progress ledger are updated.
- The branch is rebased, reviewed, integrated into `main`, and verified after integration.
- Its worktree is safely retired.

A phase is done only when all required tasks meet this definition and its exit criteria are demonstrated. Passing happy-path tests or producing a screenshot is not sufficient.

## 21. Immediate next actions

These are the next sequential actions after the user approves this plan:

1. Initialize Git and create the `main` baseline.
2. Exercise the worktree workflow with a documentation-only change.
3. Propose G0 and G1 ADRs; do not implement architecture before approval.
4. Bootstrap minimal Python/frontend tooling on separate, non-overlapping worktree branches after G1.
5. Draft the G2 canonical data model and G3 financial semantics with worked examples.
6. Request explicit user approval before creating production domain models or database migrations.

## 22. Progress summary

| Phase | Status | Approval state | Notes |
|---|---|---|---|
| 0. Repository and governance | in progress | G0/G1 approved | Apache-2.0 and modular boundaries recorded; contributor/security setup remains |
| 1. Security and domain foundations | in progress | G2/G4 approved; G3 pending | No real financial data before approved controls are implemented |
| 2. Synthetic vertical slice | planned | G5 pending | Must pass before real broker integration |
| 3. Zerodha | in progress | G7 approved | Connector foundation follows approved hybrid source policy |
| 4. IBKR | planned | G6 approved | Begins after Zerodha exit criteria; user-assisted integration expected |
| 5. Analytics | planned | G3 plus provider decision pending | Deterministic calculations only |
| 6. API and browser | planned | G5/G8 pending | Responsive, accessible dashboard |
| 7. Assistant and MCP | planned | G9 pending | Read-only tools; AI optional |
| 8. Release hardening | planned | G10 pending | Backup/restore and supply chain required |
| 9. Optional increments | backlog | per-feature | Includes Vested |
