# Module Boundaries

`architecture.toml` is the executable source of truth for allowed internal dependencies. ADR 0002 records the decision; this document explains its operation.

## Enforcement layers

1. Each backend module becomes a separate `uv` workspace package with only approved internal dependencies declared in its `pyproject.toml`.
2. The local pre-commit hook runs the architecture checker before every ordinary commit.
3. Import Linter validates package contracts once the Python workspace is bootstrapped.
4. CI reruns all contracts and is required by the protected `main` branch.
5. `CODEOWNERS` requires human approval for policy, security, domain, application, schema, migration, and workflow changes.
6. Runtime credentials and database roles limit what each process can access even if code boundaries fail.

Local hooks provide fast feedback but are bypassable. Protected-branch CI and human code-owner review are the authoritative merge controls.

## Data scope

Analytics and query use cases accept an explicit portfolio scope rather than implementing separate broker calculations. A scope may select all accessible accounts or filter by broker, account, instrument, asset class, geography, sector, currency, and time range.

The consolidated, Zerodha, and IBKR dashboards are different saved views over the same approved calculations. Every response retains contributing accounts, source coverage, freshness, and reconciliation status.

## Runtime ownership

- API and browser processes do not receive broker credentials.
- A connector worker receives only the secrets required for its connector.
- MCP and assistant processes call read-only application queries and receive no broker secrets.
- Document parsing runs without broker credentials and with resource limits.
- Database roles are process-specific; production application roles cannot run schema migrations.
- Migration credentials are short-lived and used only by the deployment workflow.

## Protected ownership

`@awara-coder` is the designated human owner in `.github/CODEOWNERS`. Repository rules must require code-owner approval after the latest push, dismiss stale approvals, require architecture and security checks, prohibit force pushes, and grant no bypass permission to agents or automation.

At minimum, human ownership covers:

- `AGENTS.md`
- `architecture.toml`
- `.github/`
- `.pre-commit-config.yaml`
- `docs/decisions/`
- `scripts/check_architecture.py`
- Domain and application packages
- Database schemas and migrations
- Security and secret-management code

`CODEOWNERS` becomes enforceable only after the repository is hosted on GitHub and branch rules require code-owner review. Its presence in a local repository does not prevent direct commits or merges.

## Changing a boundary

Boundary changes require a proposed ADR when they alter architectural direction. The change must update the machine policy, tests, package metadata, documentation, and ownership rules together. An agent may prepare the change but cannot supply the required human approval.
