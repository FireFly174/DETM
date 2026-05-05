# Model Media Artifacts

This directory stores curated media artifacts for README/docs demos.

## Folder Layout

- `docs/media/source/video_*.mp4` - source captures
- `docs/media/gif/video_*.gif` - short GIF previews
- `docs/media/png/video_*/*.png` - extracted frames (start/middle/end + intermediate)

## Numbering

- `video_000` is a legacy demo capture (no source mp4 in repo).
- `video_001..video_008` are numbered source recordings migrated from dated filenames.
- source filename mapping is stored in `docs/media/source/mapping.json`.

## Quick Embed

```md
![DETM demo](gif/video_001.gif)
```

## Curated Artifacts

| Artifact | Source scenario | Local source data | Readout |
| --- | --- | --- | --- |
| `png/beta_kappa_phase_map.png` | `../../experiments/11_beta_kappa_phase_map/` | `../../runs/11_beta_kappa_phase_map/summary.csv` | Two-axis `beta x kappa` regime screen, size 24, 3 seeds |
| `png/beta_viscosity_readout.png` | `../../experiments/04_beta_viscosity/` | `../../runs/04_beta_viscosity/summary.csv` | One-axis beta flattening readout, size 24, 3 seeds, eq 0.5/0.7 |
| `png/kappa_viscosity_readout.png` | `../../experiments/07_kappa_viscosity/` | `../../runs/07_kappa_viscosity/summary.csv` | One-axis kappa threshold readout at beta 0.9, size 24, 3 seeds, eq 0.5/0.7 |

Regenerate reproducible curated artifacts from existing sweep outputs:

```powershell
.\.venv\Scripts\python.exe -m experiments.11_beta_kappa_phase_map.analyze
.\.venv\Scripts\python.exe -m experiments.pub01_media_assets
```

Manual captures:

- `gif/video_001.gif`
- `gif/video_009.gif`

These GIFs were recorded manually and are kept as supplementary visual captures,
not as canonical reproducible readout artifacts.
