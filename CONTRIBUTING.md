# Contributing

Thanks for considering a contribution to DETM.

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

1. Create a branch from `main`.
2. Keep PRs focused (one concern per PR when possible).
3. Add or update tests for behavioral changes.
4. Update docs if API, runtime semantics, or architecture changed.
5. Include a short validation section in the PR description (what you ran).

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
