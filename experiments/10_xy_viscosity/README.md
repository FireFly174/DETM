# Size Sweep

This sweep keeps the high-`beta` baseline fixed and varies only the lattice
size. The goal is to test whether the strong flattening seen on `24x24` is a
true regime property or partly a finite-size effect.

Fixed coefficients:

- `beta = 0.9`
- `gamma = 0.1`
- `kappa = 0.1`
- `alpha = 0.3`
- `lambda_t = 1.5`
- `activation_threshold = 2.0`
- equilibrium energy: `0.5`
- initial noise: `0.1`

Swept axes:

- sizes: `24`, `48`, `72`, `96`, `120`, `144`, `168`, `192`
- seeds: `22222`, `77777`

Observation window:

- checkpoints: `150, 300, 600, 900, 1200, 1600, 2000`
- max steps: `2000`

Run:

```powershell
.\.venv\Scripts\python.exe -m experiments.crystallization_protocol --config experiments/10_xy_viscosity/config.json
```

Outputs:

- `runs/10_xy_viscosity/catalog.json`
- `runs/10_xy_viscosity/summary.csv`
- one directory per run with:
  - `metrics.csv`
  - `summary.json`
  - `state_snapshots.npz`
  - `quicklook.png`

Current readout:

- This sweep shows a strong finite-size effect.
- On `24x24`, the aggregate `final_structure_score` is only about `1.04e-08`.
- On `48x48`, it jumps to about `2.70e-05`, and for `72` through `192` it stays
  in the `5e-05` to `7e-05` range.
- This is one of the strongest paper-worthy results in the current experiment
  set because it shows that the strong flattening regime on small lattices does
  not simply extrapolate to larger spatial domains.
