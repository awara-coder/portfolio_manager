# ADR 0003: Canonical portfolio data model

- Status: proposed
- Date: 2026-08-05
- Gate: G2
- Approved by: pending

## Context

Broker APIs expose a mixture of economic history and current-state observations. Neither is complete enough to replace the other. The canonical model must preserve source evidence, support corrected imports, represent multiple currencies and instrument types, and produce both consolidated and broker-scoped views without inventing missing values.

## Options considered

1. Store only current broker snapshots. Simple, but cannot reliably explain changes, returns, corrections, or historical reports.
2. Reconstruct all state from a normalized event ledger. Auditable, but falsely implies completeness when a broker supplies only holdings or limited history.
3. Keep immutable activities and immutable observations, then derive versioned snapshots. More model surface, but preserves what happened separately from what a source claimed at a point in time.

## Decision

Choose option 3. Use a broker-neutral, tenant-owned model with four layers:

1. **Evidence:** collection runs, raw artifacts, source records, normalized batches, and data-coverage declarations preserve the input and processing lineage.
2. **Economic activity:** immutable activities with typed legs represent trades, cash movements, income, fees, taxes, transfers, corporate actions, and corrections.
3. **Observations:** immutable position, cash-balance, price, FX, benchmark, and optional tax-lot observations record source claims with an `as_of` time.
4. **Derived products:** reproducible portfolio snapshots and report revisions reference the exact input set and calculation-policy version used.

### Ownership and scope

- A tenant owns broker connections, broker accounts, external cash accounts, evidence, activities, observations, snapshots, and reports.
- A user-to-tenant relationship is settled by G4; G2 does not assume one user per tenant.
- Every portfolio query uses an explicit scope: consolidated tenant, institution, broker connection, broker account, or selected account set.
- Consolidated and broker-specific results use the same calculation path and differ only by scope.

### Identity

- Internal entities use opaque UUID identifiers and never expose database sequence meaning.
- External identifiers are stored with their namespace and scope, such as broker connection plus account plus source entity type. An external value alone is never globally unique.
- `Instrument` represents an economic instrument; `Listing` represents a venue/currency/trading-symbol occurrence; broker instrument mappings retain the broker's identifier and validity interval.
- Strong identifiers such as ISIN are attributes, not universal primary keys: they may be absent, reused across listings, or changed by corporate actions.
- Source records have a connector-defined stable key when available and a versioned canonical fingerprint otherwise.

### Activities and corrections

- An activity is an immutable economic occurrence with one or more typed legs. Legs carry an instrument or currency, exact quantity or amount, and a semantic role.
- Activity kinds initially include trade, deposit, withdrawal, dividend, interest, fee, tax, transfer, FX conversion, and corporate action. Unknown source kinds remain preserved as unsupported evidence rather than coerced.
- Type-specific invariants validate leg combinations. Values in different currencies or units are not added merely to force artificial accounting balance.
- Corrections create a new activity that explicitly supersedes an earlier activity. Imported rows and normalized activities are never updated in place.
- A transfer may link withdrawal and deposit sides. If only one side is known, it remains an incomplete transfer rather than becoming income or expense.
- Corporate actions use explicit action and leg roles. A split changes quantity without fabricating cash; mergers, spin-offs, and return-of-capital events can carry multiple instrument and cash legs.
- Fees and taxes use typed legs and retain both the source label and normalized category. Initial categories include brokerage, platform, exchange/regulatory, bank, FX, withholding tax, and tax collected at source (TCS); unknown charges remain unclassified rather than disappearing into net cash.
- TCS is stored separately from fees so later tax treatment can distinguish a potentially creditable tax from investment cost. Its jurisdiction-specific calculation and reporting remain outside G2.

### Time semantics

- Preserve `trade_date`, `settlement_date`, source `effective_at`, source `as_of`, and system `observed_at`/`ingested_at` separately when applicable.
- Track contractual settlement date, actual settlement observation, and funds-availability observation separately. A trade can therefore remain unsettled across one or more business days without being treated as missing cash.
- Settlement offsets are policy data keyed by market, instrument, and effective interval, not a hard-coded T+1 or T+2 assumption. Dates are resolved with versioned exchange and banking calendars.
- Unknown dates remain null with a quality issue; one timestamp is never copied into another merely to satisfy a field.
- Store instants in UTC and retain the source timezone or market-date context needed to reproduce daily cutoffs.

### Numeric and currency semantics

- Persist quantities, prices, money, FX rates, multipliers, and strike values as exact decimals, never binary floating point.
- Preserve source precision and native currency. Account-base and user-reporting currency values are derived with an identified FX observation and policy version.
- Preserve both quoted FX rates and actual bank/broker conversions. A conversion records source amount, destination amount, currencies, execution time, explicit fees, and the resulting effective rate.
- Historical INR results use the FX evidence applicable to each cash flow or the approved historical-rate fallback. They never revalue historical cost with today's FX rate.
- Realized reporting separates security-price return, FX effect, explicit fees, and taxes. The exact attribution, lot matching, remittance treatment, and display formula require G3 approval.
- Fractional and negative quantities are supported. A negative position represents a short; sign is not encoded in a separate flag.
- Derivative instruments can carry multiplier, underlying, expiry, strike, and option right. Fields not applicable to an instrument remain absent.
- Detailed precision, rounding, valuation, and return rules remain gated by G3.

### Observations and missing data

- Each observation records source, subject, value, `as_of`, ingestion time, and quality metadata.
- Absence is represented as unknown, not zero. A confirmed zero requires an explicit observation or a justified derived result.
- Observations are append-only. A later observation can supersede a source error without erasing the original claim.
- Tax lots distinguish broker-reported observations from lots derived under a named policy.

### Source coverage, freshness, and settlement

- Each source batch declares the period it claims to cover, the source-generated time, retrieval time, expected availability lag, and whether the period is provisional or final.
- Freshness is measured from the source's `data_through` or `as_of` boundary, not merely from the successful download time. A newly downloaded report can therefore still be stale.
- Daily reports carry per-source freshness and coverage. If Zerodha reporting lags by a day, the affected snapshot remains provisional and visibly stale rather than presenting yesterday's positions as current.
- Later source data creates a new normalized batch and report revision. It reconciles the provisional day without rewriting the earlier published report.
- Expected report lag and escalation thresholds are connector policy settled by G7; G2 stores the facts needed to enforce that policy.

### Bank-statement ingestion and reconciliation

- A bank-statement connector accepts an explicitly selected account, date range, file, or supported read-only feed. It can extract only relevant rows and fields; unrelated narrations and balances need not enter the canonical model.
- External cash accounts use pseudonymous internal identifiers. Display labels and masked account suffixes are optional sensitive metadata governed by G4.
- A statement entry preserves booking date, value date, signed amount, currency, source reference, counterparty hint, narration-derived classification, and provenance. Raw narration is sensitive and is not logged.
- Reconciliation links are many-to-many and confidence-bearing because one bank debit can fund several broker credits, or one withdrawal can arrive net of fees.
- Matching uses amount, currency, date windows, references, and counterparty hints. Automatic matches require an approved threshold; ambiguous matches remain reviewable and never silently merge records.
- Bank, FX, platform, brokerage, regulatory, and tax charges become separate typed activity legs when explicitly reported or reliably extracted. Implied FX spread is a derived metric, not fabricated as an explicit fee.
- Parser output retains source classification separately from normalized classification and user corrections, so reprocessing does not erase review decisions.
- Raw statement retention, encryption, redaction, consent, deletion, and least-privilege access require G4 approval before real statements are imported.

### Provenance and quality

- Every imported activity and observation traces to a source record, normalized batch, raw artifact, collection run, connector name, and connector schema version.
- Raw artifacts are immutable, content-addressed, encrypted according to G4, and may have multiple source records.
- Quality is structured rather than a single vague score: authority (`authoritative`, `reconstructed`, `estimated`), completeness (`complete`, `partial`, `unknown`), coverage interval, freshness, settlement state, and zero or more issue codes.
- Reconciliation compares activities, observations, and derived state without silently rewriting any of them.

### Idempotency and versioning

- Ingestion uniqueness is tenant-scoped and connector-version-aware.
- Re-importing the same source record produces no second effective activity or observation.
- A changed record with the same stable source identity creates a new revision and supersession relationship.
- Normalization and calculation policy versions are stored with their outputs so historical reports remain reproducible after code changes.
- Reports are immutable revisions. Regeneration creates a new revision rather than changing a previously published daily report.

## Representative cases

| Case | Canonical representation | Important result |
|---|---|---|
| Buy with brokerage and tax | Trade activity with security, cash, fee, and tax legs | Native amounts and dates remain explainable |
| Partial sell | Trade activity with negative security quantity and cash/fee legs | Lot matching is separate and policy-versioned |
| Dividend | Income activity with cash, gross income, withholding-tax, and optional receivable legs | Net cash is not mistaken for gross income |
| Deposit or withdrawal | Cash-movement activity | External flows remain distinct from performance |
| Stock split | Corporate-action activity with old/new quantity relationship | No fabricated cash flow or gain |
| Account transfer | Linked transfer sides, or one incomplete side | Not classified as income when the peer is missing |
| Option position | Instrument terms plus signed quantity and multiplier | Exposure can be derived without flattening contract identity |
| Holdings-only import | Position observations with no invented trades | Reports disclose incomplete history |
| Corrected broker row | New source-record revision and superseding activity | Audit history and idempotency are both preserved |
| Missing cash response | No observation plus a quality issue | Missing data never appears as zero cash |
| Fresh download containing yesterday's data | Batch with current retrieval time but stale `data_through` | Dashboard and report remain provisional and visibly stale |
| Trade awaiting settlement | Trade activity plus contractual settlement date and later settlement/funds observations | Pending cash or stock is not treated as a discrepancy |
| USD buy and sell funded from INR | Security legs, linked INR/USD conversions, historical FX evidence, and external cash flows | INR result can separate asset return, FX effect, fees, and taxes |
| Bank debit containing remittance charges and TCS | Statement entry reconciled to conversion/funding activity with bank-fee and TCS legs | Net debit is not mistaken for invested principal |
| One bank transfer funding several broker credits | One statement entry with multiple reconciliation links | Matching remains auditable without duplicating cash flow |

## Rejected shortcuts

- Broker-specific tables as the reporting model: they prevent consistent consolidated analytics.
- Mutable transaction rows: they destroy correction history and report reproducibility.
- ISIN or ticker as a universal instrument key: neither is universally present nor globally unambiguous.
- One timestamp or one base-currency amount per record: both discard information needed for settlement, cutoff, and FX attribution.
- Treating download time as data freshness: a newly generated or retrieved broker report may still cover only an earlier day.
- Treating bank debit, broker credit, or sale proceeds as a single net amount: this hides FX, TCS, and explicit charges.
- JSON-only canonical financial records: flexible ingestion evidence may use JSON, but query-critical canonical fields require typed columns and constraints.

## Security and privacy effect

Tenant ownership is mandatory on all sensitive aggregate roots and repository operations. Bank statements and raw broker evidence may contain substantially more personal data than normalized records and must use stricter access, encryption, minimization, retention, export, and deletion controls defined by G4. Logs and identifiers must not expose raw payloads, account numbers, narrations, or credentials.

## Compatibility and migration effect

Connectors translate broker payloads into this model and may retain unsupported fields in source evidence. New activity kinds, quality issue codes, and instrument attributes must be additive where possible. Constraint or semantic changes require a new ADR, versioned normalization, and an explicit migration/reprocessing plan.

## Consequences

The model is more explicit than snapshot-only storage and requires reconciliation logic. In return, it supports audited history, incomplete broker feeds, broker-specific and consolidated views, deterministic reprocessing, and future connectors without leaking their payload shapes into the domain.

Approval authorizes domain and schema design against this revision; it does not approve G3 financial calculations, G4 security implementation, or G7 Zerodha source policy.
