# DETM: One Pager (EN)

## What it is

DETM (Discrete Entropy-Time Model) is a research runtime for lattice-based discrete dynamics.
Focus: emergence of stable localized structures (invariants) from local transfer, suppression, and internal-time rules.

## What it is not

- not a physics theory;
- not an out-of-the-box AGI system;
- not a claim of universal laws.

It is an engineering/research platform for reproducible self-organization experiments.

## Canonical layers

- `detm/*`: L0 core and runtime/API contracts.
- `detm_app/*`: orchestration, UI, transport, subscribers.
- `docs/rus/*`: canonical source documentation.
- `docs/eng/*`: synchronized translation.

## Minimal run

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py --mode shell --steps 200 --size 128
```

## Readout artifacts

- `trace.jsonl`
- `metrics.csv`
- `summary.json`
- `final_state.msgpack`

## Where to continue

1. `docs/eng/00_overview/README.md`
2. `docs/eng/10_model/model_core.md`
3. `docs/eng/20_mechanisms/*`
4. `docs/eng/40_experiments/*`
5. `docs/rus/ROADMAP.md` (source roadmap)

