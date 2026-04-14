# Beta x Kappa Phase Map

This sweep varies `beta` and `kappa` jointly on the same compact lattice to
prepare a paper-facing two-parameter regime map.

Execution backend:

- `backend = torch`
- `device = cuda`
- if CUDA is unavailable, the protocol falls back to the NumPy CPU backend and
  records the resolved backend/device in each run summary

Fixed coefficients:

- `gamma = 0.1`
- `alpha = 0.3`
- `lambda_t = 1.5`
- `activation_threshold = 2.0`

Swept axes:

- seeds: `12345`, `22222`, `54321`
- equilibrium energy: `0.65`
- `beta`: `0.3`, `0.45`, `0.6`, `0.75`, `0.9`
- `kappa`: `0.1`, `0.13`, `0.15`, `0.2`

Observation window:

- checkpoints: `150, 300, 600, 900, 1200, 1600, 2000`
- max steps: `2000`

Run:

```powershell
.\.venv\Scripts\python.exe -m experiments.crystallization_protocol --config experiments/11_beta_kappa_phase_map/config.json
```

Outputs:

- `runs/11_beta_kappa_phase_map/catalog.json`
- `runs/11_beta_kappa_phase_map/summary.csv`
- one directory per run with:
  - `metrics.csv`
  - `summary.json`
  - `state_snapshots.npz`
  - `quicklook.png`

Intended use:

- build a paper figure showing where `beta`-driven flattening still dominates
  and where larger `kappa` reintroduces persistent residual structure;
- compare late-state metrics with a common mid-run residual field at tick 300;
- test whether the `kappa` threshold stays visible across a broader `beta`
  range rather than only at `beta = 0.9`.
