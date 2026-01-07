from __future__ import annotations
import base64
import time
from detm.runtime import api
from detm.runtime.serialization import deserialize_state, serialize_state

from .core import *  # noqa: F401,F403
from .core import _config_from_config_json, _make_influence_from_dict


from .core import _config_json_from_config
from .core import _get_session
from .core import _upgrade_state_to_torch_if_possible
from .core import _parse_json_list


class DETMRunPubNode:
    @classmethod
    def IS_CHANGED(cls, **_kwargs):  # type: ignore[override]
        return time.time()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "session_id": ("STRING", {"default": "default"}),
                "tick": ("INT", {"default": 1, "min": 0, "max": 1_000_000_000}),
                "config_json": ("STRING", {"default": ""}),
                "seed": ("INT", {"default": 1, "min": 0, "max": 2**31 - 1}),
                "n_ticks_per_tick": ("INT", {"default": 1, "min": 0, "max": 1_000_000}),
                "due_events_json": ("STRING", {"default": "[]"}),
                "snapshot_every": ("INT", {"default": 1, "min": 1, "max": 1_000_000}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("state_b64", "snapshot_b64")
    FUNCTION = "run"
    CATEGORY = "DETM/Scheduler"

    def run(
        self,
        session_id: str,
        tick: int,
        config_json: str,
        seed: int,
        n_ticks_per_tick: int,
        due_events_json: str,
        snapshot_every: int,
    ):
        session = _get_session(session_id)
        tick = int(tick)

        config = _config_from_config_json(config_json) if (config_json or "").strip() else DETMConfig()
        cfg_key = _config_json_from_config(config)

        needs_reset = False
        if session.get("config_json") != cfg_key:
            needs_reset = True
        if session.get("seed") != int(seed):
            needs_reset = True
        if tick == 0:
            needs_reset = True

        if needs_reset or not session.get("state_b64"):
            state = api.reset(config, int(seed))
            blob = serialize_state(state)
            session["state_b64"] = base64.b64encode(blob).decode("ascii")
            session["config_json"] = cfg_key
            session["seed"] = int(seed)
            session["last_run_tick"] = -1

        last_run_tick = int(session.get("last_run_tick", -1))
        state_b64 = str(session.get("state_b64", ""))
        if tick <= last_run_tick:
            snapshot_b64 = state_b64 if (tick % int(max(1, snapshot_every)) == 0) else ""
            return (state_b64, snapshot_b64)

        state = deserialize_state(base64.b64decode(state_b64.encode("ascii")))
        _upgrade_state_to_torch_if_possible(state)

        # Apply due events (simple scheduler I/O).
        events = _parse_json_list(due_events_json)
        for item in events:
            if not isinstance(item, dict):
                continue
            if str(item.get("kind", "influence")) != "influence":
                continue
            due_tick = item.get("due_tick")
            try:
                due_tick = int(due_tick) if due_tick is not None else tick
            except Exception:
                due_tick = tick
            if due_tick > tick:
                continue
            infl = _make_influence_from_dict(item)
            if infl is None:
                continue
            state, _ = api.step(state, infl, n_ticks=0, rng=None)

        # Advance by configured amount of L0 ticks for this scheduler tick.
        state, _ = api.step(state, None, n_ticks=int(max(0, n_ticks_per_tick)), rng=None)

        blob_out = serialize_state(state)
        state_b64_out = base64.b64encode(blob_out).decode("ascii")
        session["state_b64"] = state_b64_out
        session["last_run_tick"] = tick

        snapshot_b64 = state_b64_out if (tick % int(max(1, snapshot_every)) == 0) else ""
        return (state_b64_out, snapshot_b64)
