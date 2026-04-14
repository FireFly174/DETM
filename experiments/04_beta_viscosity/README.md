# Beta Viscosity Sweep

This sweep isolates the DETM hypothesis that `beta` acts like an effective
medium viscosity: higher `beta` should accelerate transport and push the field
toward crystallization faster when the other coefficients are fixed.

Fixed coefficients:

- `gamma = 0.1`
- `kappa = 0.1`
- `alpha = 0.3`
- `lambda_t = 1.5`
- `activation_threshold = 2.0`

Swept axes:

- seeds: `12345`, `22222`, `54321`
- equilibrium energies: `0.6`, `0.65`, `0.7`
- `beta`: `0.3`, `0.45`, `0.6`, `0.75`, `0.9`

Observation window:

- checkpoints: `150, 300, 600, 900, 1200, 1600, 2000`
- max steps: `2000`

This configuration is intentionally longer than the UI-family runs because the
user-observed `seed = 22222`, `beta = 0.9` regime approaches near-complete
crystallization around tick `2000`.

Run:

```powershell
.\.venv\Scripts\python.exe -m experiments.crystallization_protocol --config experiments/04_beta_viscosity/config.json
```

Outputs:

- `runs/04_beta_viscosity/catalog.json`
- `runs/04_beta_viscosity/summary.csv`
- one directory per run with:
  - `metrics.csv`
  - `summary.json`
  - `state_snapshots.npz`
  - `quicklook.png`
