# DETM: One Pager (EN)

## What It Is

DETM (Discrete Entropy-Time Model) is a research runtime for lattice-based
discrete dynamics. The project studies when local transport and suppression
rules produce stable localized structures, coarsening, asynchrony, and internal
time.

Practically, this is a reproducible research workspace: code, run scenarios,
artifacts, and documentation are tied together so a result can be repeated and
checked from files, not only from prose.

## What It Is Not

- not a physics theory;
- not a model of the real universe;
- not an AGI system;
- not proof of universal laws;
- not the final architecture for multilevel coarsening.

External analogies are allowed only as interpretation. The project canon is the
local dynamics, run artifacts, trace/readout, and explicitly documented limits.

## Layer Model

- `detm/*` - library core and runtime contracts.
- `detm_app/*` - orchestration, UI, transport, subscribers, analytics read-model.
- `experiments/*` - reproducible scenarios and public preset/config packs.
- `docs/rus/*` - canonical documentation and roadmap source-of-truth.
- `docs/eng/*` - derivative English translation layer.
- `docs/media/*` - curated public preview/readout artifacts.

External observation remains artifact-first: `System Trace`, `Watch Trace`,
`OuterFields`, `trace_ref`, summary/readout files. The SQLite analytics
read-model is a derived layer over raw artifacts, not a replacement for the
source-of-truth.

## Current Status

- Verified baseline: `python main.py --help`, `pytest -> 439 passed`.
- Closed: fabric production baseline, phase-F code contour, bounded N-D migration.
- Closed public packaging baseline: `PUB-01` media readouts, `PUB-02` visual presets, `PUB-03` one-page overview.
- Open focus: `G-RND-01`, `MSC-02`, analytics/outerfields retention follow-up, residual P1 structural debt.
- Transition layers must not be treated as final architecture: current multiscale catalog, analytics read-model, visual presets, and the `channel_tunnel` preset remain bounded readout/packaging layers.

## Quick Start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
python main.py headless --seed 7 --steps 64 --batch 1 --out runs/out/quickstart --no-viz
```

Expected artifacts:

- `runs/out/quickstart/catalog.json`
- `runs/out/quickstart/seed_0000/config.json`
- `runs/out/quickstart/seed_0000/digest.json`
- `runs/out/quickstart/seed_0000/state.msgpack`
- `runs/out/quickstart/seed_0000/trace.jsonl`

Interactive UI:

```powershell
python main.py napari --interactive
```

## Public Readouts and Presets

Curated media:

- `docs/media/png/beta_kappa_phase_map.png`
- `docs/media/png/beta_viscosity_readout.png`
- `docs/media/png/kappa_viscosity_readout.png`

Regenerate:

```powershell
python -m experiments.11_beta_kappa_phase_map.analyze
python -m experiments.pub01_media_assets
```

Visual presets:

- `experiments/12_public_visual_presets/classic_coarsing.json`
- `experiments/12_public_visual_presets/stable_object.json`
- `experiments/12_public_visual_presets/channel_tunnel.json`

Example run:

```powershell
python -m experiments.marker_protocol --config experiments/12_public_visual_presets/stable_object.json
```

## Where To Continue

1. `README.md` - repository entrypoint.
2. `docs/eng/README.md` - English docs index.
3. `docs/rus/ROADMAP_HUMAN.md` - compact roadmap.
4. `docs/rus/ROADMAP.md` - engineering source-of-truth for statuses and dependencies.
5. `experiments/README.md` - reproducible scenario list.
6. `docs/media/README.md` - public preview/readout artifacts.

