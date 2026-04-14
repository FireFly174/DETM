# UI-Family Sweep

This sweep expands the last useful `ui_run` regime into a small neighborhood rather
than a broad blind search.

Use it when you want additional mid-run structures that stay visually close to the
reference UI behavior but differ by seed and coefficient choices.

Baseline center:

- `size = 24`
- `boundary = periodic`
- `equilibrium_energy ~= 1.0`
- `initial_noise = 0.1`
- `beta = 0.8`
- `gamma = 0.1`
- `kappa = 0.1`
- `alpha = 0.3`
- `lambda_t = 1.5`

Sweep axes:

- seeds: `12345`, `54321`
- equilibrium energies: `0.95`, `0.999999`
- noise: `0.08`, `0.1`
- `beta`: `0.8`, `1.0`
- `gamma`: `0.1`, `0.2`
- `kappa`: `0.1`, `0.15`
- `alpha`: `0.2`, `0.3`
- `lambda_t`: `1.5`, `2.0`

Observation window:

- checkpoints: `25, 50, 75, 100, 150, 200, 300, 500`
- max steps: `500`

Run:

```powershell
.\.venv\Scripts\python.exe -m experiments.crystallization_protocol --config experiments/03_ui_family/config.json
```

Outputs:

- `runs/03_ui_family/catalog.json`
- `runs/03_ui_family/summary.csv`
- one directory per run with:
  - `metrics.csv`
  - `summary.json`
  - `state_snapshots.npz`
  - `quicklook.png`
