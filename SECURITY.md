# Security Policy

## Supported versions

Security fixes are provided for the latest released version. Until the first release, fixes target `main`.

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability. Use GitHub's private vulnerability reporting for this repository. If that channel is unavailable, contact the maintainer through the private contact method listed on the maintainer's GitHub profile without including secrets in the initial message.

Include affected versions, impact, reproduction steps using synthetic data, and any suggested mitigation. Remove credentials, account identifiers, portfolio values, statements, logs containing personal data, and broker responses.

## Handling expectations

The maintainer will acknowledge a report as soon as practical, assess severity and affected versions, coordinate remediation privately, and publish an advisory when users need to act. Timelines depend on severity, exploitability, and broker or dependency coordination.

## Security boundaries

- The product is read-only and must not automate broker passwords or TOTP.
- Broker credentials belong only in approved secret backends.
- API, browser, assistant, and MCP processes receive no broker credentials.
- Financial documents and raw payloads are sensitive data.
- AI providers receive only explicitly permitted, minimized information.
- Logs and diagnostic bundles must redact secrets and personal financial data.

See `AGENTS.md` and `docs/architecture/MODULE_BOUNDARIES.md` for mandatory engineering controls.

The proposed application threat model is maintained in [`docs/security/THREAT_MODEL.md`](docs/security/THREAT_MODEL.md). Controls in a proposed ADR are not considered implemented until their verification tests pass.
