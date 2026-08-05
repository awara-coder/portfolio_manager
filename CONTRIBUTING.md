# Contributing

Thank you for improving Portfolio Manager. Read `AGENTS.md` and the relevant ADRs before starting.

## Before coding

1. Check `docs/IMPLEMENTATION_PLAN.md` for dependencies and approval gates.
2. Open or reference an issue describing the intended outcome.
3. Obtain product-owner approval before implementing a gated decision.
4. Claim a short-lived branch and worktree in the plan ledger.
5. Confirm that the scope does not overlap another active branch.

## Development workflow

- Branch from current `main` using an approved prefix.
- Keep each branch independently testable and normally under two working days.
- Use synthetic data. Never commit real account data, statements, tokens, cookies, or credentials.
- Add tests for success, failure, retry, and data-quality behavior as applicable.
- Run local pre-commit and affected verification before pushing.
- Open a pull request and complete every applicable checklist item.
- Do not merge until required checks pass and `@awara-coder` approves code-owned changes.

See `docs/GIT_WORKFLOW.md` for worktree commands and integration details.

## Major decisions

Use a concise ADR for decisions that alter architecture, financial meaning, security boundaries, public contracts, deployment, retention, or external integrations. Copy `docs/decisions/template.md`, explain the decision and essential consequences, and leave it `proposed` until the product owner approves it.

## Testing real integrations

Real broker tests run only in the contributor's local environment. Store credentials in the approved local secret backend and share only sanitized structural results. Do not paste secrets, TOTP seeds, cookies, full statements, account numbers, or raw broker responses into issues, pull requests, chat, recordings, or fixtures.

If a test needs the project owner's account, document the exact local command, expected safe output, and required broker setup. Ask the owner to run it rather than requesting credentials.

## Commits and pull requests

- Write focused commits with imperative messages.
- Explain behavior and trade-offs in the pull request, not routine mechanics in code comments.
- Call out migrations, compatibility changes, new permissions, external data sharing, and operational effects.
- Resolve review comments with new commits; do not rewrite a branch another contributor is using.
- Update documentation, ADRs, and progress state with the implementation.

By contributing, you agree that your contributions are licensed under Apache License 2.0.
