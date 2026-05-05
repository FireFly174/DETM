# Public Visual Presets

This folder fixes a small public preset pack for README/docs demos.

All presets use `experiments.marker_protocol` because it produces the compact
artifact contract required for public reproducibility:

- `catalog.json`
- `seed_*/metrics.csv`
- `seed_*/summary.json`
- `seed_*/final_state.npz`

These presets are for visual/readout packaging only. They do not add new
runtime mechanics and must not be treated as final architecture.

## Presets

### classic_coarsing

Low marker footprint, moderate smoothing, compact lattice.

```powershell
.\.venv\Scripts\python.exe -m experiments.marker_protocol --config experiments/12_public_visual_presets/classic_coarsing.json
```

Expected output root:

- `runs/pub02_classic_coarsing`

### stable_object

Centered marker perturbation with conservative dynamics, intended as a stable
object-like contrast run.

```powershell
.\.venv\Scripts\python.exe -m experiments.marker_protocol --config experiments/12_public_visual_presets/stable_object.json
```

Expected output root:

- `runs/pub02_stable_object`

### channel_tunnel

Off-center marker perturbation with higher coupling. This is a bounded visual
stress preset for local perturbation transfer/readout, not a new channel
mechanic and not a final tunnel architecture.

```powershell
.\.venv\Scripts\python.exe -m experiments.marker_protocol --config experiments/12_public_visual_presets/channel_tunnel.json
```

Expected output root:

- `runs/pub02_channel_tunnel`

## Smoke All

```powershell
.\.venv\Scripts\python.exe -m experiments.marker_protocol --config experiments/12_public_visual_presets/classic_coarsing.json
.\.venv\Scripts\python.exe -m experiments.marker_protocol --config experiments/12_public_visual_presets/stable_object.json
.\.venv\Scripts\python.exe -m experiments.marker_protocol --config experiments/12_public_visual_presets/channel_tunnel.json
```

