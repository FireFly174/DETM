# Golden Baseline: 00

This folder fixes one reproducible baseline run for quick smoke-checks and
cross-machine comparison.

## Run

```bash
python -m experiments.marker_protocol --config experiments/00_baseline/config.json
```

## Expected outputs

After a successful run, the folder `runs/00_baseline/` contains:

- `catalog.json` (index of runs)
- `seed_0007/metrics.csv` (time-series readout)
- `seed_0007/final_state.npz` (final lattice snapshot + marker mask)
- `seed_0007/summary.json` (aggregated metrics for this seed)

## Why this is the "golden" baseline

- single fixed seed (`7`) and fixed dynamics parameters;
- deterministic scenario with marker perturbation;
- compact artifact set compatible with `docs/rus/50_experiments/metrics.md`.
