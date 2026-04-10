# DETM: One Pager (EN)

## What it is

DETM (Discrete Entropy-Time Model) is a research runtime for lattice-based discrete dynamics.
The project focuses on stable localized structures, coarsening, asynchrony, and internal time emerging from local transfer and suppression rules.

## What it is not

- not a physics theory;
- not an out-of-the-box AGI system;
- not a claim of universal laws.

It is an engineering/research platform for reproducible self-organization experiments.

## Canonical layers

- `detm/*`: L0 core and runtime/API contracts.
- `detm_app/*`: orchestration, UI, transport, subscribers, analytics read-model.
- `docs/rus/*`: canonical source documentation.
- `docs/eng/*`: synchronized translation.

## Current status

- Verified local snapshot (2026-04-10): `python main.py --help`, `pytest -q -> 439 passed in 16.51s`
- Closed baselines: fabric production baseline, phase-F code contour, bounded N-D migration
- Current open focus: `G-RND-01`, `MSC-02`, public packaging (`PUB-01..03`), residual P1 structural debt
- Current runtime `coarsening` is an invariant/coarse-time stream layer; full object-level `L0 -> L1` coarsening remains a research track

## Minimal run

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
python main.py headless --seed 7 --steps 64 --batch 1 --out runs/out/quickstart --no-viz
```

UI path:

```powershell
python main.py napari --interactive
```

## Minimal run artifacts

- `runs/out/quickstart/catalog.json`
- `runs/out/quickstart/seed_0000/config.json`
- `runs/out/quickstart/seed_0000/digest.json`
- `runs/out/quickstart/seed_0000/state.msgpack`
- `runs/out/quickstart/seed_0000/trace.jsonl`

## Where to continue

1. `README.md`
2. `docs/eng/00_overview/README.md`
3. `docs/eng/10_model/model_core.md`
4. `docs/eng/00_overview/roadmap_snapshot.md`
5. `docs/rus/ROADMAP.md` (source roadmap)
