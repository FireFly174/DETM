# Alpha Sweep

This sweep keeps the high-`beta` crystallization regime fixed and varies only
`alpha` to test whether transport attenuation changes the late-state morphology
once the medium is already strongly driven toward flattening.

Fixed coefficients:

- `beta = 0.9`
- `gamma = 0.1`
- `kappa = 0.1`
- `lambda_t = 1.5`
- `activation_threshold = 2.0`

Swept axes:

- seeds: `22222`, `44444`, `66666`
- equilibrium energies: `0.5`, `0.7`
- `alpha`: `0.3`, `0.45`, `0.6`, `0.75`, `0.9`

Observation window:

- checkpoints: `150, 300, 600, 900, 1200, 1600, 2000`
- max steps: `2000`

Run:

```powershell
.\.venv\Scripts\python.exe -m experiments.crystallization_protocol --config experiments/05_alpha_viscosity/config.json
```

Outputs:

- `runs/05_alpha_viscosity/catalog.json`
- `runs/05_alpha_viscosity/summary.csv`
- one directory per run with:
  - `metrics.csv`
  - `summary.json`
  - `state_snapshots.npz`
  - `quicklook.png`

Current readout:

- In this late, high-`beta` regime, varying `alpha` from `0.3` to `0.9` has
  almost no effect on `final_structure_score` or `final_energy_var`.
- Aggregate `final_structure_score` stays near `7.59e-09` across the whole
  sweep.
- This makes the sweep useful mainly as a negative control: under strong
  flattening, `alpha` is not the parameter that determines whether residual
  structure survives to tick `2000`.
