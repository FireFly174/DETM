# Branching Strategy

This repository uses two primary branch roles:

- `main`: release branch (stable snapshots and tags)
- `dev/main`: integration branch for ongoing work

## Rules

1. Do not develop directly in `main`.
2. Create feature branches from `dev/main` (`dev/<topic>`).
3. Merge feature branches into `dev/main`.
4. Merge `dev/main` into `main` only when a release-ready state is reached.
5. Create version tags from `main` only.

## Recommended GitHub ruleset layout

- For `main`:
  - require pull request before merging
  - require status checks (`lint-and-test`, `torch-tests`)
  - block force pushes and deletion
- For `dev/*`:
  - allow branch creation and updates
  - do not require mandatory checks (optional CI is fine)

## Typical flow

```bash
git switch dev/main
git pull --ff-only origin dev/main
git switch -c dev/my-change
# work, commit
git push -u origin dev/my-change
```

Then open PR:
- `dev/my-change` -> `dev/main`

Release PR:
- `dev/main` -> `main`
