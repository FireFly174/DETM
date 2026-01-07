from __future__ import annotations
import json
from typing import Any, Dict, List

import numpy as np

from detm.runtime.diagnostics.attractors import detect_attractors

from .core import *  # noqa: F401,F403
import base64
import time
from detm.runtime import api
from detm.runtime.serialization import deserialize_state, serialize_state

class DETMStateToImageNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "state_b64": ("STRING", {"default": ""}),
                "mode": (["single", "triptych"], {"default": "single"}),
                "field": (["energy", "entropy", "internal_time"], {"default": "energy"}),
                "normalize": (["minmax", "percentile", "clamp01"], {"default": "minmax"}),
                "percentile_low": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 49.0, "step": 0.5}),
                "percentile_high": ("FLOAT", {"default": 99.0, "min": 51.0, "max": 100.0, "step": 0.5}),
                "colormap": (["turbo", "gray"], {"default": "turbo"}),
                "overlay_step": (["no", "yes"], {"default": "yes"}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "run"
    CATEGORY = "DETM"

    def run(
        self,
        state_b64: str,
        mode: str,
        field: str,
        normalize: str,
        percentile_low: float,
        percentile_high: float,
        colormap: str,
        overlay_step: str,
    ):
        if not state_b64.strip():
            # Return a minimal black image to keep graph stable.
            import torch  # type: ignore

            return (torch.zeros((1, 16, 16, 3), dtype=torch.float32),)

        blob = base64.b64decode(state_b64.encode("ascii"))
        state = deserialize_state(blob)
        lattice = state.lattice

        def render_field(name: str) -> np.ndarray:
            raw = _to_numpy(getattr(state.field_state, str(name))).reshape(lattice.height, lattice.width)
            norm = _normalize_scalar_field(
                raw,
                mode=str(normalize),
                percentile_low=float(percentile_low),
                percentile_high=float(percentile_high),
            )
            if str(colormap) == "gray":
                return np.stack([norm, norm, norm], axis=-1).astype(np.float32)
            return _apply_turbo_colormap(norm)

        if str(mode) == "triptych":
            img_a = render_field("energy")
            img_b = render_field("entropy")
            img_c = render_field("internal_time")
            sep = np.ones((img_a.shape[0], 2, 3), dtype=np.float32) * 0.05
            rgb = np.concatenate([img_a, sep, img_b, sep, img_c], axis=1)
        else:
            rgb = render_field(str(field))

        if overlay_step == "yes":
            rgb = _overlay_text_top_left(rgb, f"step={int(getattr(state, 'step_count', 0))}")

        return (_to_comfy_image(rgb),)

class DETMSeriesBufferNode:
    @classmethod
    def IS_CHANGED(cls, **_kwargs):  # type: ignore[override]
        return time.time()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "session_id": ("STRING", {"default": "default"}),
                "tick": ("INT", {"default": 0, "min": 0, "max": 1_000_000_000}),
                "state_b64": ("STRING", {"default": ""}),
                "sample_every": ("INT", {"default": 1, "min": 1, "max": 1_000_000}),
                "series_key": (
                    ["energy_mean", "energy_var", "entropy_mean", "tau_mean", "center_x", "center_y"],
                    {"default": "energy_mean"},
                ),
                "max_points": ("INT", {"default": 2048, "min": 16, "max": 1_000_000}),
                "window": ("INT", {"default": 64, "min": 2, "max": 8192}),
                "stride": ("INT", {"default": 16, "min": 1, "max": 8192}),
                "normalize": (["no", "yes"], {"default": "no"}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "IMAGE")
    RETURN_NAMES = ("series_json", "windows_json", "summary_json", "plot_image")
    FUNCTION = "run"
    CATEGORY = "DETM/Analysis"

    def run(
        self,
        session_id: str,
        tick: int,
        state_b64: str,
        sample_every: int,
        series_key: str,
        max_points: int,
        window: int,
        stride: int,
        normalize: str,
    ):
        session = _get_session(session_id)
        key = str(series_key)
        tick = int(tick)
        sample_every = int(max(1, sample_every))

        series_store = session.setdefault("series", {})
        if not isinstance(series_store, dict):
            series_store = {}
            session["series"] = series_store

        series = series_store.get(key)
        if not isinstance(series, list):
            series = []
            series_store[key] = series

        if state_b64.strip() and (tick % sample_every == 0):
            blob = base64.b64decode(state_b64.encode("ascii"))
            state = deserialize_state(blob)
            lattice = state.lattice
            energy = _to_numpy(state.field_state.energy).reshape(lattice.height, lattice.width)
            entropy = _to_numpy(state.field_state.entropy).reshape(lattice.height, lattice.width)
            internal_time = _to_numpy(state.field_state.internal_time).reshape(lattice.height, lattice.width)
            sig = api.digest(state)  # already in numpy for digest

            value = None
            summary = sig.summary or {}
            if key == "tau_mean":
                value = float(summary.get("internal_time_mean", 0.0))
            elif key == "center_x":
                value = float(summary.get("center_of_mass_x", 0.0))
            elif key == "center_y":
                value = float(summary.get("center_of_mass_y", 0.0))
            elif key in summary:
                value = float(summary[key])
            else:
                vec = sig.vector or []
                idx_map = {
                    "energy_mean": 0,
                    "energy_var": 1,
                    "entropy_mean": 4,
                    "tau_mean": 6,
                    "center_x": 7,
                    "center_y": 8,
                }
                idx = idx_map.get(key)
                if idx is not None and idx < len(vec):
                    value = float(vec[idx])
            if value is None:
                value = 0.0
            series.append(float(value))

        limit = int(max(16, max_points))
        if len(series) > limit:
            series[:] = series[-limit:]

        windows = _window_series(series, window=int(window), stride=int(stride), normalize=(normalize == "yes"))
        dom = _dominant_frequency(series)
        summary = {
            "series_key": key,
            "n_points": int(len(series)),
            "n_windows": int(len(windows)),
            "dominant_frequency": dom,
        }
        series_json = json.dumps(series, ensure_ascii=False)
        windows_json = json.dumps(windows, ensure_ascii=False)
        summary_json = json.dumps(_diag_to_jsonable(summary), ensure_ascii=False)
        plot = _plot_series_as_image(series, width=512, height=256)
        return (series_json, windows_json, summary_json, plot)

class DETMFrameBufferNode:
    @classmethod
    def IS_CHANGED(cls, **_kwargs):  # type: ignore[override]
        return time.time()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "session_id": ("STRING", {"default": "default"}),
                "tick": ("INT", {"default": 0, "min": 0, "max": 1_000_000_000}),
                "state_b64": ("STRING", {"default": ""}),
                "sample_every": ("INT", {"default": 1, "min": 1, "max": 1_000_000}),
                "field": (["energy", "entropy", "internal_time"], {"default": "energy"}),
                "max_frames": ("INT", {"default": 240, "min": 1, "max": 10_000}),
                "reset_frames": (["no", "yes"], {"default": "no"}),
            }
        }

    RETURN_TYPES = ("IMAGE", "INT")
    RETURN_NAMES = ("frames", "frame_count")
    FUNCTION = "run"
    CATEGORY = "DETM/Analysis"

    def run(
        self,
        session_id: str,
        tick: int,
        state_b64: str,
        sample_every: int,
        field: str,
        max_frames: int,
        reset_frames: str,
    ):
        import torch  # type: ignore

        session = _get_session(session_id)
        frames = session.get("frames")
        if not isinstance(frames, list):
            frames = []
            session["frames"] = frames

        if reset_frames == "yes":
            frames.clear()

        tick = int(tick)
        sample_every = int(max(1, sample_every))
        max_frames = int(max(1, max_frames))

        if state_b64.strip() and (tick % sample_every == 0) and len(frames) < max_frames:
            blob = base64.b64decode(state_b64.encode("ascii"))
            state = deserialize_state(blob)
            lattice = state.lattice
            arr = _to_numpy(getattr(state.field_state, str(field))).reshape(lattice.height, lattice.width)
            frames.append(_field_to_comfy_image(arr))

        frames_batch = _stack_image_batch(frames, fallback=torch.zeros((1, 16, 16, 3), dtype=torch.float32))
        return (frames_batch, int(len(frames)))

class DETMDetectAttractorsNode:
    @classmethod
    def IS_CHANGED(cls, **_kwargs):  # type: ignore[override]
        return time.time()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "tick": ("INT", {"default": 0, "min": 0, "max": 1_000_000_000}),
                "state_b64": ("STRING", {"default": ""}),
                "every": ("INT", {"default": 10, "min": 1, "max": 1_000_000}),
                "threshold": ("FLOAT", {"default": 0.8, "min": 0.0, "max": 10.0, "step": 0.01}),
                "top_k": ("INT", {"default": 4, "min": 1, "max": 1000}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("attractors_json", "events_json")
    FUNCTION = "run"
    CATEGORY = "DETM/Analysis"

    def run(self, tick: int, state_b64: str, every: int, threshold: float, top_k: int):
        tick = int(tick)
        every = int(max(1, every))
        if not state_b64.strip() or (tick % every != 0):
            return ("[]", "[]")

        blob = base64.b64decode(state_b64.encode("ascii"))
        state = deserialize_state(blob)
        lattice = state.lattice
        energy = _to_numpy(state.field_state.energy).reshape(lattice.height, lattice.width)
        attractors = detect_attractors(energy, threshold=float(threshold), top_k=int(top_k))

        out = [
            {
                "tick": tick,
                "position": [int(a.position[0]), int(a.position[1])],
                "strength": float(a.strength),
                "stability_score": float(a.stability_score),
                "period_estimate": a.period_estimate,
            }
            for a in attractors
        ]

        # Simple scheduler hint: if we see strong attractors, request more frequent probes.
        events: List[Dict[str, Any]] = []
        if out:
            best = max(out, key=lambda r: float(r.get("stability_score", 0.0)))
            if float(best.get("stability_score", 0.0)) >= 1.0:
                events.append(
                    {
                        "due_tick": tick + 1,
                        "kind": "hint",
                        "hint": {"probe_every": max(1, every // 2)},
                    }
                )

        return (json.dumps(out, ensure_ascii=False), json.dumps(events, ensure_ascii=False))

class DETMStateToImageEveryNNode:
    """Same as `DETM State -> Image`, but recomputes only every N scheduler ticks.

    On skipped ticks it returns the last cached image for the given session+params,
    so downstream nodes (Preview/Save) stay stable.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "session_id": ("STRING", {"default": "default"}),
                "tick": ("INT", {"default": 0}),
                "every_n": ("INT", {"default": 1, "min": 1, "max": 1000000}),
                "state_b64": ("STRING", {"default": ""}),
                "mode": (["single", "triptych"], {"default": "single"}),
                "field": (["energy", "entropy", "internal_time"], {"default": "energy"}),
                "normalize": (["none", "minmax", "percentile"], {"default": "minmax"}),
                "percentile_low": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 100.0, "step": 0.1}),
                "percentile_high": ("FLOAT", {"default": 99.0, "min": 0.0, "max": 100.0, "step": 0.1}),
                "colormap": (["turbo", "gray"], {"default": "turbo"}),
                "overlay_step": (["yes", "no"], {"default": "yes"}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "run"
    CATEGORY = "DETM"

    def run(
        self,
        session_id: str,
        tick: int,
        every_n: int,
        state_b64: str,
        mode: str,
        field: str,
        normalize: str,
        percentile_low: float,
        percentile_high: float,
        colormap: str,
        overlay_step: str,
    ):
        session = _get_session(str(session_id))
        cache = session.setdefault("cache", {})
        key = (
            f"state2img:{mode}:{field}:{normalize}:"
            f"{float(percentile_low):.4f}:{float(percentile_high):.4f}:{colormap}:{overlay_step}"
        )

        def get_black():
            import torch  # type: ignore
            return (torch.zeros((1, 16, 16, 3), dtype=torch.float32),)

        # If no state yet, stay stable.
        if not str(state_b64).strip():
            return cache.get(key, get_black())

        tick_i = int(tick) if tick is not None else 0
        every_i = max(1, int(every_n))

        should_compute = (tick_i % every_i) == 0 or key not in cache
        if not should_compute:
            return (cache[key],)

        blob = base64.b64decode(state_b64.encode("ascii"))
        state = deserialize_state(blob)
        lattice = state.lattice

        def render_field(name: str) -> np.ndarray:
            raw = _to_numpy(getattr(state.field_state, str(name))).reshape(lattice.height, lattice.width)
            norm = _normalize_scalar_field(
                raw,
                mode=str(normalize),
                percentile_low=float(percentile_low),
                percentile_high=float(percentile_high),
            )
            if str(colormap) == "gray":
                return np.stack([norm, norm, norm], axis=-1).astype(np.float32)
            return _apply_turbo_colormap(norm)

        if str(mode) == "triptych":
            img_a = render_field("energy")
            img_b = render_field("entropy")
            img_c = render_field("internal_time")
            sep = np.ones((img_a.shape[0], 2, 3), dtype=np.float32) * 0.05
            rgb = np.concatenate([img_a, sep, img_b, sep, img_c], axis=1)
        else:
            rgb = render_field(str(field))

        if str(overlay_step) == "yes":
            step_val = getattr(state, 'step', None)
            if step_val is None:
                step_val = getattr(state, 'step_count', None)
            if step_val is None:
                step_val = tick
            rgb = _overlay_text_top_left(rgb, f"tick={int(step_val)}")

        image = _to_comfy_image(rgb)
        cache[key] = image
        return (image,)

