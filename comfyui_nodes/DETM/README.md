# DETM ComfyUI nodes (MVP)

This folder exposes DETM as ComfyUI custom nodes.

## Install (recommended: symlink)

1) In your ComfyUI repo, create a symlink (Windows, admin PowerShell):

```powershell
cd <COMFYUI_ROOT>\custom_nodes
cmd /c mklink /D DETM "<PATH_TO_DETM_REPO>\comfyui_nodes\DETM"
```

2) Restart ComfyUI.

## Nodes

Recommended (scheduler-style MVP):
- `DETM: Config (json)`
- `DETM: Scheduler Tick`
- `DETM: Run`
- `DETM: Bus Publish (events)`
- `DETM: Make Influence Event`
- `DETM: State -> Image`
- `DETM: Series Buffer (state->windows)`
- `DETM: Frame Buffer (state->frames)`
- `DETM: Detect Attractors`
- `DETM: Save GIF (frames)`

Legacy (kept for reference):
- `DETM: Run (legacy)`
- `DETM: Init (legacy)`
- `DETM: Step (legacy)`
- `DETM: Random Search (legacy)`
- `DETM: TimeSeries Analyze (windows)`

## What you get (scheduler-style)

- A global `tick` (from `DETM: Scheduler Tick`) and a persistent per-`session_id` simulation state advanced by `DETM: Run`.
- `state_b64` every scheduler tick, and `snapshot_b64` only every `snapshot_every` ticks (empty string on other ticks).
- Separate nodes to sample state into time-series windows and/or frames for GIF export.

## Minimal workflow (recommended MVP)

This mode splits concerns:
- Scheduler generates a global tick.
- DETM advances exactly once per scheduler tick and publishes its state.
- Other nodes subscribe to `tick` and run on their own cadence.

1) `DETM: Config (json)` -> `config_json`
2) `DETM: Scheduler Tick` -> `session_id`, `tick`, `due_events_json`
3) `DETM: Run`
   - `session_id` <- (2)
   - `tick` <- (2)
   - `config_json` <- (1)
   - `due_events_json` <- (2)
4) Preview:
   - `state_b64` -> `DETM: State -> Image` -> ComfyUI `Preview Image`
5) Time-series windows:
   - `state_b64` (or `snapshot_b64`) -> `DETM: Series Buffer (state->windows)`
   - `tick` <- (2)
6) GIF:
   - `state_b64` (or `snapshot_b64`) -> `DETM: Frame Buffer (state->frames)`
   - `tick` <- (2)
   - `frames` -> `DETM: Save GIF (frames)` (set `write=no` while stepping; switch to `write=yes` to write)

To advance time: use ComfyUI Queue `batch_count` (each queued execution increments the scheduler tick).

## Influence scheduling (optional)

To schedule an influence for future ticks:
1) `DETM: Make Influence Event` -> `events_json` (a JSON list of events without `due_tick`)
2) `DETM: Bus Publish (events)` (sets `due_tick` using `default_due_offset` and stores it in the session bus)
3) Next tick(s), `DETM: Scheduler Tick` will emit it via `due_events_json`, and `DETM: Run` will apply it.
