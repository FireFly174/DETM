# DETM Architecture (EN)

This document describes the *current* architecture and integration interfaces of DETM.
It corresponds to the Russian version: `docs/rus/architecture.md`.

DETM is **pure L0 dynamics**. It does not know about Scheduler/ComfyUI/UI.
External systems interact with it via the runtime API contract and observables.

```mermaid
flowchart LR
  UI[UI/CLI] --> Runner[TickRunner]
  Runner --> Session[DetmSession (L0)]
  Runner --> Bus[EventBus]
  Bus --> Sub1[Trace/History subscribers]
  Bus --> Sub2[Diagnostics/Invariant subscribers]
  Bus --> Viz[Viz subscriber]
  Viz -->|embedded| Canvas[Canvas/Panel]
  Viz -->|tcp| Daemon[TCP daemon] --> Viewer[Viewer/Panel]
```

---

## 1) Runtime Contract (L0 API)

Canonical API: `detm/runtime/api.py`:

- `reset(config: DETMConfig, seed: int) -> DETMState`
- `step(state: DETMState, influence: DETMInfluence | None, n_ticks: int, rng: np.random.Generator | None = None) -> (DETMState, Observables)`
- `digest(state: DETMState) -> DETMSignature`
- `serialize_state(state: DETMState) -> bytes`
- `deserialize_state(blob: bytes) -> DETMState`
- `get_schema_versions() -> dict[str, str]`

Notes:
- `n_ticks` is an **integer tick count** (tick-driven time model).
- determinism: all stochastic operations use `rng` or `state.rng_state`.
- `step()` returns **observables** without any UI dependencies.

---

## 2) Backends (Torch/Numpy) and state representation

Compute backends: `detm/runtime/backends/`:
- `TorchBackend` (CPU/CUDA, optional dependency)
- `NumpyBackend` (reference + fallback)

Rule: **a backend must not convert the state**.
It only performs the transition in the representation already present in `DETMState`:
- tensor-state → tensor-state (TorchBackend)
- numpy-state → numpy-state (NumpyBackend)

Any conversion/comparison/transformation is done *outside* the backend (in analyzers / plugins / runtime glue).

---

## 3) Influence API (“alphabet”)

`DETMInfluence` is the external port for acting on L0.

Symbol library: `detm/runtime/symbols.py`:
- `make_symbol(symbol_id, **params) -> DETMInfluence`
- `list_symbols() -> list[str]`

Influence application: `detm/runtime/influence.py`:
- `apply_influence(field_state, influence, rng) -> InfluenceApplication`

`external_features` is a generic vector/dict of parameters without binding to the source (mouse/keyboard/sensor).

---

## 4) EventBus, subscribers, Scheduler, and invariant ticks

`detm/run/bus.py`: a minimal synchronous EventBus used to attach:
- loggers / traces
- serialization of artifacts
- viz streaming
- invariant tick streams (coarsening timekeepers)
- external listeners (ACGS can plug in its own)

Scheduler: `detm/run/scheduler.py`:
- `TickScheduler` publishes `tick`/`signal`
- `TickRunner` binds `DetmSession` and the Scheduler

`TickRunner` semantics:
1) on each global tick, applies all due influences **without advancing time**
2) performs exactly **1** L0 tick

Invariant ticks: `detm/run/coarsening.py`:
- streams are defined by a rational dt relative to L0 (e.g. `1/10`, `4/25`)
- the coarsener **does not accumulate** values; it only emits `invariant_tick`
- JSON / persistence is handled by separate subscribers

---

## 5) Entrypoints and a single config

`python main.py`:
- opens the UI by default
- uses a local `config.example.py` (if missing, copies from `detm/presets/config.default.py`)

Headless CLI: `detm/cli.py`:
- single runs and batch runs
- optional viz streaming

---

## 6) Visualization: embedded vs TCP

Visualization is a **subscriber/consumer** of state frames, not part of L0.

Modes:
1) `embedded`: render in the same process (no sockets)
2) `tcp`: DETM sends state blobs to a headless daemon, and UI subscribes + renders

TCP daemon: `detm/viz/daemon.py` (headless hub):
- producer: `{type:"state", ...}`
- viewer: `{type:"subscribe"}` → stream of `state` messages
