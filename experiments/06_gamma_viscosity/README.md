# Gamma Sweep

This sweep fixes the high-`beta` regime and varies only `gamma` to test how
collective suppression from neighboring cells affects the late-state readout.

Fixed coefficients:

- `beta = 0.9`
- `kappa = 0.1`
- `alpha = 0.3`
- `lambda_t = 1.5`
- `activation_threshold = 2.0`

Swept axes:

- seeds: `22222`, `44444`, `66666`
- equilibrium energies: `0.5`, `0.7`
- `gamma`: `0.3`, `0.45`, `0.6`, `0.75`, `0.9`

Observation window:

- checkpoints: `150, 300, 600, 900, 1200, 1600, 2000`
- max steps: `2000`

Run:

```powershell
.\.venv\Scripts\python.exe -m experiments.crystallization_protocol --config experiments/06_gamma_viscosity/config.json
```

Outputs:

- `runs/06_gamma_viscosity/catalog.json`
- `runs/06_gamma_viscosity/summary.csv`
- one directory per run with:
  - `metrics.csv`
  - `summary.json`
  - `state_snapshots.npz`
  - `quicklook.png`

Current readout:

- `gamma` has only a weak effect on the late morphology in this setup.
- Aggregate `final_structure_score` shifts only slightly, from about
  `7.59e-09` at `gamma = 0.3` to about `7.15e-09` at `gamma = 0.9`.
- The clearer effect is on `final_internal_time_mean`, which drops from about
  `1.65` to `1.27` as `gamma` increases.
- At the current horizon, this sweep is better interpreted as a control on the
  latency/readiness field than as a strong morphology-generating axis.
