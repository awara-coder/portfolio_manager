# ADR 0002: Modular-monolith boundaries

- Status: approved
- Date: 2026-08-05
- Gate: G1
- Approved by: product owner

## Decision

Use one versioned codebase with separately runnable API, worker, web, and optional MCP processes. Keep broker-neutral domain rules independent; orchestrate use cases in an application module; implement broker, persistence, job, and external-provider ports in adapters.

All portfolio queries must accept an explicit scope so the same calculation path supports consolidated, broker-specific, account-specific, and dimensional views.

## Enforcement

Dependency direction is declared in `architecture.toml` and checked by CI. Changes to boundaries, enforcement, security policy, schemas, or workflows require designated-owner review through protected-branch settings and `CODEOWNERS`.

## Consequences

Modules share PostgreSQL initially but cannot bypass application/repository contracts. A service may be extracted only for a measured scaling, failure-isolation, security, residency, or independent-release need and requires a new approved ADR.
