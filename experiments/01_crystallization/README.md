# Long-Run Crystallization Sweep

This protocol is for long deterministic runs over multiple seeds and parameter
combinations, with early stopping when a simple operational crystallization
heuristic is reached.

## What it sweeps

- seeds, including the preferred comparison pair `12345` and `54321`;
- initial equilibrium energy;
- dynamics coefficients `alpha`, `beta`, `gamma`, `kappa`, `lambda_t`;
- fixed lattice size and boundary condition unless overridden from the CLI.

## What "crystallization" means here

This is a reproducible experiment heuristic, not a final theoretical claim.
A run is marked as crystallized when, on a rolling window:

- mean absolute energy delta is small;
- energy variance is stable;
- structure score (mean gradient magnitude) is stable;
- structure score stays above a small floor, so a flat freeze does not count.

## Run

```powershell
.\.venv\Scripts\python.exe -m experiments.crystallization_protocol --config experiments/01_crystallization/config.json
```

## Outputs

Under `runs/01_crystallization/` the sweep writes:

- `catalog.json`
- `summary.csv`
- one folder per run combination containing:
  - `metrics.csv`
  - `state_snapshots.npz`
  - `quicklook.png`
  - `summary.json`

For the current `24x24` starter config, the quicklook artifact is biased toward
mid-run structure rather than the eventual flattening tail:

- snapshots at steps `150`, `300`, `600`, `900`, `1200`;
- total run horizon capped at `1200`.

The `quicklook.png` artifact is intended for fast visual comparison of initial
and checkpoint energy fields across seeds and parameter settings.
Each panel uses robust local color autocalibration around the run's
equilibrium-energy level, so weak structures do not wash out into a nearly
flat global colormap.
