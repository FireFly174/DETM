# UI Reference Sweep

This config mirrors the last useful `runs/out/ui_run` profile as a reproducible
experiment baseline.

## Why this exists

The UI run shows the regime of interest, but only in the mid-run window.
For this parameter set the field eventually relaxes toward a nearly uniform
state, so long tails hide the transient structures we actually want to compare.

## Mirrored parameters

- size: `24x24`
- boundary: `periodic`
- initial noise: `0.1`
- equilibrium energy: `0.999999`
- `beta = 0.8`
- `gamma = 0.1`
- `kappa = 0.1`
- `alpha = 0.3`
- `lambda_t = 1.5`
- `activation_threshold = 2.0`

## Recommended observation window

For this profile, inspect checkpoint snapshots rather than the very end:

- `25`, `50`, `75`, `100`
- `150`, `200`, `300`
- `500` as the late checkpoint

This reproduces the part of the UI run where structure is still visible before
the trajectory washes out into a nearly flat field.

## Run

```powershell
.\.venv\Scripts\python.exe -m experiments.crystallization_protocol --config experiments/02_ui_reference/config.json
```
