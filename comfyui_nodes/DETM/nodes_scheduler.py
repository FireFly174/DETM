from __future__ import annotations

# важно: ensure_detm_on_path() если он у тебя в common.py
from .common import ensure_detm_on_path
#ensure_detm_on_path()

import time
# ХЕЛПЕРЫ из core.py
from .core import *  # noqa: F401,F403

# дальше твои обычные импорты
import json
from typing import Any, Dict
class DETMConfigNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "backend": (["torch", "numpy"], {"default": "torch"}),
                "device": ("STRING", {"default": "cuda"}),
                "width": ("INT", {"default": 24, "min": 4, "max": 2048}),
                "height": ("INT", {"default": 24, "min": 4, "max": 2048}),
                "boundary": (["periodic", "open"], {"default": "periodic"}),
                "initial_noise": ("FLOAT", {"default": 0.08, "min": 0.0, "max": 1.0, "step": 0.01}),
                "dynamics_overrides_json": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("config_json",)
    FUNCTION = "run"
    CATEGORY = "DETM/Scheduler"

    def run(
        self,
        backend: str,
        device: str,
        width: int,
        height: int,
        boundary: str,
        initial_noise: float,
        dynamics_overrides_json: str,
    ):
        config = _build_config(
            backend=backend,
            device=device,
            width=width,
            height=height,
            boundary=boundary,
            initial_noise=initial_noise,
            dynamics_overrides_json=dynamics_overrides_json,
        )
        config_json = _config_json_from_config(config)
        return (config_json,)

class DETMSchedulerTickNode:
    @classmethod
    def IS_CHANGED(cls, **_kwargs):  # type: ignore[override]
        return time.time()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "session_id": ("STRING", {"default": "default"}),
                "reset": (["no", "yes"], {"default": "no"}),
                "tick_step": ("INT", {"default": 1, "min": 1, "max": 1_000_000}),
            }
        }

    RETURN_TYPES = ("STRING", "INT", "STRING")
    RETURN_NAMES = ("session_id", "tick", "due_events_json")
    FUNCTION = "run"
    CATEGORY = "DETM/Scheduler"

    def run(self, session_id: str, reset: str, tick_step: int):
        session = _get_session(session_id)
        if reset == "yes":
            session["tick"] = 0
            session["last_run_tick"] = -1
            session["state_b64"] = ""
            session["series"] = {}
            session["frames"] = []
            session["events"] = []
        else:
            session["tick"] = int(session.get("tick", 0)) + int(max(1, tick_step))

        tick = int(session.get("tick", 0))
        events = session.get("events", [])
        due, future = _events_due_for_tick(events if isinstance(events, list) else [], tick)
        session["events"] = future
        due_json = json.dumps(due, ensure_ascii=False)
        return (str(session_id or "default"), int(tick), due_json)

class DETMBusPublishNode:
    @classmethod
    def IS_CHANGED(cls, **_kwargs):  # type: ignore[override]
        return time.time()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "session_id": ("STRING", {"default": "default"}),
                "tick": ("INT", {"default": 0, "min": 0, "max": 1_000_000_000}),
                "events_json": ("STRING", {"default": "[]"}),
                "default_due_offset": ("INT", {"default": 1, "min": 0, "max": 1_000_000}),
            }
        }

    RETURN_TYPES = ("INT", "STRING")
    RETURN_NAMES = ("published_count", "bus_size")
    FUNCTION = "run"
    CATEGORY = "DETM/Scheduler"

    def run(self, session_id: str, tick: int, events_json: str, default_due_offset: int):
        session = _get_session(session_id)
        items = _parse_json_list(events_json)
        published = 0
        for item in items:
            if not isinstance(item, dict):
                continue
            if "due_tick" not in item:
                item["due_tick"] = int(tick) + int(max(0, default_due_offset))
            session.setdefault("events", []).append(item)
            published += 1
        size = len(session.get("events", [])) if isinstance(session.get("events", []), list) else 0
        return (int(published), str(size))

class DETMMakeInfluenceEventNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "symbol_id": ("STRING", {"default": "pulse"}),
                "amplitude": ("FLOAT", {"default": 0.15, "min": -2.0, "max": 2.0, "step": 0.01}),
                "phase": ("FLOAT", {"default": 0.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                "seed": ("INT", {"default": -1, "min": -1, "max": 2**31 - 1}),
                "region_cx": ("INT", {"default": 0, "min": -4096, "max": 4096}),
                "region_cy": ("INT", {"default": 0, "min": -4096, "max": 4096}),
                "region_radius": ("INT", {"default": 0, "min": 0, "max": 4096}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("events_json",)
    FUNCTION = "run"
    CATEGORY = "DETM/Scheduler"

    def run(
        self,
        symbol_id: str,
        amplitude: float,
        phase: float,
        seed: int,
        region_cx: int,
        region_cy: int,
        region_radius: int,
    ):
        ev = {
            "kind": "influence",
            "symbol_id": str(symbol_id),
            "amplitude": float(amplitude),
            "phase": float(phase),
            "seed": int(seed),
            "region_cx": int(region_cx),
            "region_cy": int(region_cy),
            "region_radius": int(region_radius),
        }
        return (json.dumps([ev], ensure_ascii=False),)

