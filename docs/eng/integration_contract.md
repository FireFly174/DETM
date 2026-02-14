# DETM Integration Contract

This document defines the minimal stable API and reproducibility requirements needed to integrate DETM into external runtimes (ACGS Scheduler, ComfyUI, etc.).

DETM is **pure L0 dynamics**. It does **not** depend on a scheduler or UI. External systems interact only through:
- the runtime API (`reset/step/digest/serialize/deserialize`)
- typed influences
- returned observables (signatures/metrics/events)

---

## Core API (L0)

Canonical implementation: `detm/runtime/api/*`.

- `reset(config: DETMConfig, seed: int) -> DETMState`
- `step(state: DETMState, influence: DETMInfluence | None, n_ticks: int, rng: np.random.Generator | None = None) -> (DETMState, Observables)`
- `digest(state: DETMState) -> DETMSignature`
- `serialize_state(state: DETMState) -> bytes`
- `deserialize_state(blob: bytes) -> DETMState`
- `get_schema_versions() -> dict[str, str]`

`serialize(state)` / `deserialize(blob)` aliases are allowed but must behave identically.

### UML-style sketch

```mermaid
classDiagram
  class DETMConfig
  class DETMState
  class DETMInfluence
  class Observables
  DETMConfig --> DETMState : reset()
  DETMState --> Observables : step()
  DETMState --> DETMSignature : digest()
```

---

## Determinism / reproducibility

- **Single RNG mechanism**: all stochastic operations must use the provided `rng` (or `state.rng_state`). No hidden `np.random` / `torch.rand`.
- **Same inputs → same outputs**: same seed + same config + same influence sequence must produce the same `digest` / signatures.

---

## Config

`DETMConfig` defines:
- lattice (`width/height/boundary`)
- runtime backend (`backend`: `"torch"` preferred, `"numpy"` reference/fallback)
- device (`device`: `"cpu"`, `"cuda"`, `"cuda:0"`, etc.)
- dynamics parameters (`dynamics`: `alpha/beta/gamma/kappa/lambda_t/...`)

Schema versions are part of the contract:
- config/state/signature versions are returned by `get_schema_versions()`.

---

## State

All mutable L0 state lives in one object: `DETMState`:
- fields (`energy`, `entropy`, `internal_time`) in `DETMFieldState`
- tick counter (`step_count`)
- deterministic RNG snapshot (`rng_state`)
- config snapshot (`config`) for persistence

Numeric arrays are backend-owned:
- `numpy.ndarray` (CPU)
- `torch.Tensor` (CPU/CUDA)

Backends must not “convert” state representations; they only advance them.

---

## Serialization

- `serialize_state(state) -> bytes`
- `deserialize_state(blob) -> DETMState`

Requirement: forward-compatible via `state_version`.

---

## Influence API

`DETMInfluence` describes external influence:
- `symbol_id: str`
- `amplitude: float`
- optional: `phase`, `seed`
- optional: `mask` or `region`
- optional: `duration`
- optional: `external_features: np.ndarray | dict[str,float]` (generic external features)
- optional: `dynamics_overrides: dict[str,float]` (temporary parameter overrides)

Symbol library:
- `detm/runtime/symbols.py`: `make_symbol()`, `list_symbols()`

---

## Step semantics and observables

`step()` uses integer ticks (`n_ticks: int`), so orchestrators can remain tick-driven.

`Observables` includes:
- `signature` (short summary vector)
- `field_summaries` (minimal stats)
- `events` (e.g. attractors, applied influence)
- `cost` (time/ops/memory proxies)
- `quality` (signature-level proxies)

---

## Headless harness (no UI)

Supported:
- `main.py` launcher (`python main.py headless ...`) backed by `detm_app.runner.headless`
- `tools/headless_runner.py` (simple integration harness)

---

## Visualization boundary (pluggable sink)

Visualization is not part of L0. It is a separate consumer of serialized state frames.

Implemented modes:
- `embedded`: in-process rendering (no sockets)
- `tcp`: state frames streamed to a headless daemon; viewers subscribe

---

## Runtime bridge (optional)

For systems that want session management, `detm/integrations/runtime_bridge.py` provides an in-process bridge:
- `create_session(config, seed) -> session_id`
- `session_step(session_id, influence, n_ticks) -> (signature, observables, state_digest)`
- `session_get_state_blob(session_id)`
