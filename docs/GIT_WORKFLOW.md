# Git and Worktree Workflow

This project uses trunk-based development. `main` stays releasable, while each task is implemented on a short-lived branch in its own worktree.

The repository-wide rules in `AGENTS.md` take precedence over this operational guide.

## Before starting a task

1. Confirm that prerequisite approval gates in `docs/IMPLEMENTATION_PLAN.md` are complete.
2. Confirm that the task does not overlap another active worktree.
3. Add the task to the plan's worktree ledger with its owner, dependency, and intended branch.
4. Update local `main` without rewriting shared history.

## Create a task worktree

From the primary repository, choose an explicit branch and path:

```sh
git worktree add -b docs/worktree-smoke ../portfolio_manager-worktrees/docs-worktree-smoke main
```

Use branch prefixes defined in `AGENTS.md`. Never build paths from untrusted or unresolved input. Inspect existing worktrees before choosing a location:

```sh
git worktree list
```

## Work and verify

- Change only the claimed scope.
- Commit small, independently understandable increments.
- Run the checks required by the task and record any user-assisted verification.
- Update relevant documentation and the plan ledger in the same branch.
- Check the diff for secrets, real financial data, generated caches, and unrelated changes before integration.

## Integrate

Only one branch is integrated into `main` at a time.

1. Ensure the worktree is clean.
2. Rebase the branch onto the latest local `main`.
3. Rerun affected checks after the rebase.
4. Review the final diff and commit list.
5. Fast-forward `main` to the verified branch when repository policy and history permit it.
6. Rerun affected checks from `main` because parallel branches may interact after integration.
7. Mark the task done in the ledger.

Do not resolve conflicts with destructive checkout or reset commands. Preserve both owners' intent and request coordination when the correct resolution is unclear.

## Retire a worktree

After integration and ledger update, confirm the exact worktree path and branch before removal. Worktree cleanup must not discard uncommitted files. Prune only stale administrative entries after verifying that their directories no longer contain work.

## Parallel work

Parallel branches are appropriate for disjoint implementations against an approved contract. Examples include a connector fixture suite and browser component primitives. They are inappropriate when branches would independently define a shared schema, migration parent, or API response.

Keep branches short-lived. A feature larger than roughly two working days should be decomposed into safe increments or protected by an inactive feature flag.

## Baseline verification

The workflow was exercised on 2026-08-05 with the documentation-only `docs/worktree-smoke` branch in a disposable worktree. The branch was created from `main`, changed only planning documentation, passed staged-diff checks, and was integrated serially before the worktree was retired.
