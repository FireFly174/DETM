# Lambda-T Sweep

This sweep varies only `lambda_t`, the coupling from structural suppression to
the local readiness rate `v`, while keeping the high-`beta` baseline fixed.

Fixed coefficients:

- `beta = 0.9`
- `gamma = 0.1`
- `kappa = 0.1`
- `alpha = 0.3`
- `activation_threshold = 2.0`

Swept axes:

- seeds: `22222`, `44444`, `66666`
- equilibrium energies: `0.5`, `0.7`
- `lambda_t`: `0.5`, `1.0`, `1.5`, `2.0`, `2.5`

Observation window:

- checkpoints: `150, 300, 600, 900, 1200, 1600, 2000`
- max steps: `2000`

Run:

```powershell
.\.venv\Scripts\python.exe -m experiments.crystallization_protocol --config experiments/08_tau_viscosity/config.json
```

Outputs:

- `runs/08_tau_viscosity/catalog.json`
- `runs/08_tau_viscosity/summary.csv`
- one directory per run with:
  - `metrics.csv`
  - `summary.json`
  - `state_snapshots.npz`
  - `quicklook.png`

Current readout:

- In this late, high-`beta` regime, changing `lambda_t` does not materially
  change `final_structure_score` or `final_energy_var`; the aggregate
  `final_structure_score` remains about `7.59e-09` across the whole sweep.
- The parameter does still shift `final_internal_time_mean`, from about `1.93`
  at `lambda_t = 0.5` down to about `1.64` at `lambda_t = 2.5`.
- As currently configured, this sweep is most useful as a negative control on
  late morphology and as evidence that `lambda_t` affects the readiness field
  more clearly than it affects the final residual geometry.
