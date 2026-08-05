# Development

## Prerequisites

- `uv` 0.12 or newer within the supported minor series.
- Git with worktree support.
- Node.js tooling is added with the web workspace.

`uv` installs the pinned Python 3.13 interpreter when it is not already available.

## Setup

```sh
uv sync --all-packages --locked
uv run pre-commit install
```

Do not install project dependencies into the system Python environment.

## Verification

Fast checks:

```sh
uv run ruff format --check .
uv run ruff check .
python3 scripts/check_architecture.py --root .
```

Complete Python checks:

```sh
uv run mypy
uv run lint-imports
uv run pytest
```

Build every package before changing packaging or workspace configuration:

```sh
for package in packages/* apps/api apps/worker apps/mcp; do
  uv build "$package"
done
```

Generated build output belongs in ignored `dist/` directories and must not be committed.

## Dependency changes

Use `uv add` or edit the owning package metadata, then regenerate `uv.lock`. Declare internal dependencies only where the architecture policy permits them. The shared workspace environment can make undeclared imports appear to work locally, so Import Linter and architecture checks remain mandatory.
