# Kappa Sweep

This sweep varies only `kappa`, the transport coefficient, while keeping the
high-`beta` baseline fixed. It is designed to test whether the system shows a
threshold-like transition between near-complete flattening and persistent
residual structure.

Fixed coefficients:

- `beta = 0.9`
- `gamma = 0.1`
- `alpha = 0.3`
- `lambda_t = 1.5`
- `activation_threshold = 2.0`

Swept axes:

- seeds: `22222`, `44444`, `66666`
- equilibrium energies: `0.5`, `0.7`
- `kappa`: `0.1`, `0.11`, `0.12`, `0.13`, `0.15`, `0.2`

Observation window:

- checkpoints: `150, 300, 600, 900, 1200, 1600, 2000`
- max steps: `2000`

Run:

```powershell
.\.venv\Scripts\python.exe -m experiments.crystallization_protocol --config experiments/07_kappa_viscosity/config.json
```

Outputs:

- `runs/07_kappa_viscosity/catalog.json`
- `runs/07_kappa_viscosity/summary.csv`
- one directory per run with:
  - `metrics.csv`
  - `summary.json`
  - `state_snapshots.npz`
  - `quicklook.png`

Current readout:

- This is the strongest single-parameter effect after the `beta` sweep.
- For `kappa = 0.10` to `0.13`, the system still ends near the flattened regime:
  aggregate `final_structure_score` drops from about `7.59e-09` to
  `1.82e-10`.
- At `kappa = 0.15`, the regime changes sharply: aggregate
  `final_structure_score` jumps to about `4.36e-04`.
- At `kappa = 0.20`, the residual structure is even stronger, reaching about
  `1.05e-03`.
- This sweep is a strong candidate for a paper figure because it looks like a
  threshold or bifurcation rather than a smooth cosmetic variation.
