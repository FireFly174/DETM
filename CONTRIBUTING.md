# Contributing

Thanks for considering a contribution to DETM.

## Licensing of Contributions

By submitting a contribution (PR, patch, or commit) you agree that your
contribution is provided under the project's licensing model:

- source-available non-commercial: `PolyForm-Noncommercial-1.0.0`
- commercial: additional commercial licensing by the copyright holder

You confirm that you have the right to submit the code/content you contribute.

## Scope

- `detm/*` is the library core (L0 runtime and model contracts).
- `detm_app/*` is orchestration, UI, and integration layer.
- Docs are in `docs/` (`rus/` is canonical, `eng/` is translation track).

## Development Setup

```bash
python -m venv .venv
# Windows:
.venv\\Scripts\\activate
# Linux/macOS:
# source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

## Validate Before PR

```bash
pytest -q
python -m ruff check .
python -m black --check .
python -m mypy detm tests
```

Lint/type checks are currently non-blocking in CI, but please run them locally when possible.

## Branch and PR Guidelines

1. If you do not have write access, fork the repository and create a branch in your fork.
2. If you have write access, create a branch from `dev/main` (not from `main`).
3. Keep PRs focused (one concern per PR when possible).
4. Target regular PRs to `dev/main`.
5. Use PRs from `dev/main` to `main` only for release-ready merges.
6. Add or update tests for behavioral changes.
7. Update docs if API, runtime semantics, or architecture changed.
8. Include a short validation section in the PR description (what you ran).

## Commit Style

Use clear imperative commit messages, for example:
- `Refactor session step flow into package`
- `Fix TCP transport auth race in relay registration`
- `Update UML and roadmap after runtime split`

## Reporting Issues

Use GitHub Issues with a minimal reproduction:
- expected behavior
- actual behavior
- environment (`python --version`, OS)
- command used
- logs/trace excerpt

For security-sensitive reports, use `SECURITY.md` instead of public issues.
