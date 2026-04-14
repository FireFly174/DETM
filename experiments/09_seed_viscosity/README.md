# Seed Sweep

This sweep keeps the high-`beta` baseline fixed and varies only the random
seed. The purpose is to measure how much late-state spread remains when the
coefficients are held constant.

Fixed coefficients:

- `beta = 0.9`
- `gamma = 0.1`
- `kappa = 0.1`
- `alpha = 0.3`
- `lambda_t = 1.5`
- `activation_threshold = 2.0`

Swept axes:

- seeds: `11111`, `22222`, `33333`, `44444`, `55555`, `66666`, `77777`,
  `88888`, `99999`
- equilibrium energies: `0.5`, `0.7`

Observation window:

- checkpoints: `150, 300, 600, 900, 1200, 1600, 2000`
- max steps: `2000`

Run:

```powershell
.\.venv\Scripts\python.exe -m experiments.crystallization_protocol --config experiments/09_seed_viscosity/config.json
```

Outputs:

- `runs/09_seed_viscosity/catalog.json`
- `runs/09_seed_viscosity/summary.csv`
- one directory per run with:
  - `metrics.csv`
  - `summary.json`
  - `state_snapshots.npz`
  - `quicklook.png`

Current readout:

- Seeds do matter, but they do not appear to create completely different late
  families in this configuration.
- Aggregate `final_structure_score` spans about one order of magnitude, from
  `1.34e-09` to `1.24e-08`.
- This makes the seed sweep useful for robustness/error-bar reporting and for
  testing translation-equivalent residual families under periodic boundaries.
- It is better suited to supplement or uncertainty reporting than to a central
  main-text figure.
