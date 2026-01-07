from __future__ import annotations

import base64
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Tuple
from typing import TYPE_CHECKING
from typing import cast
from typing import overload
from typing import Union

from .common import ensure_detm_on_path  # noqa: F401

import numpy as np  # noqa: E402

from detm.runtime import api  # noqa: E402
from detm.runtime.config import DETMConfig  # noqa: E402
from detm.runtime.diagnostics.attractors import stability_metrics  # noqa: E402
from detm.runtime.influence import DETMInfluence  # noqa: E402
from detm.runtime.serialization import deserialize_state, serialize_state  # noqa: E402
from detm.runtime.symbols import list_symbols, make_symbol  # noqa: E402


_SESSIONS: Dict[str, Dict[str, Any]] = {}


def _get_session(session_id: str) -> Dict[str, Any]:
    sid = str(session_id or "default").strip() or "default"
    session = _SESSIONS.get(sid)
    if session is None:
        session = {
            "tick": 0,
            "last_run_tick": -1,
            "state_b64": "",
            "config_json": "",
            "seed": None,
            "series": {},
            "frames": [],
            "events": [],
        }
        _SESSIONS[sid] = session
    return session


def _to_numpy(array: Any) -> np.ndarray:
    try:
        import torch  # type: ignore
    except ModuleNotFoundError:
        torch = None
    if torch is not None and isinstance(array, torch.Tensor):
        return array.detach().to("cpu").numpy()
    return np.asarray(array)


def _field_to_comfy_image(field_2d: np.ndarray):
    """Return a ComfyUI IMAGE tensor (B,H,W,C) in [0,1]."""

    import torch  # type: ignore

    arr = np.asarray(field_2d, dtype=np.float32)
    if arr.ndim != 2:
        arr = arr.reshape(arr.shape[-2], arr.shape[-1])
    arr = np.clip(arr, 0.0, 1.0)
    t = torch.from_numpy(arr)[None, :, :, None]
    return t.repeat(1, 1, 1, 3)


def _normalize_scalar_field(
    field_2d: np.ndarray,
    *,
    mode: str,
    percentile_low: float = 1.0,
    percentile_high: float = 99.0,
) -> np.ndarray:
    arr = np.asarray(field_2d, dtype=np.float32)
    if arr.ndim != 2:
        arr = arr.reshape(arr.shape[-2], arr.shape[-1])

    if mode == "clamp01":
        return np.clip(arr, 0.0, 1.0)

    if mode == "percentile":
        lo = float(np.percentile(arr, float(percentile_low)))
        hi = float(np.percentile(arr, float(percentile_high)))
    else:  # minmax
        lo = float(np.min(arr))
        hi = float(np.max(arr))

    if not np.isfinite(lo) or not np.isfinite(hi) or abs(hi - lo) < 1e-12:
        return np.zeros_like(arr, dtype=np.float32)

    out = (arr - lo) / (hi - lo)
    return np.clip(out, 0.0, 1.0)


def _apply_turbo_colormap(norm_2d: np.ndarray) -> np.ndarray:
    x = np.asarray(norm_2d, dtype=np.float32)
    if x.ndim != 2:
        x = x.reshape(x.shape[-2], x.shape[-1])
    x = np.clip(x, 0.0, 1.0)

    # Polynomial approximation of Google's Turbo colormap.
    # Coefficients from the public-domain reference implementation.
    r = (
        0.13572138
        + x * (4.61539260 + x * (-42.66032258 + x * (132.13108234 + x * (-152.94239396 + x * 59.28637943))))
    )
    g = (
        0.09140261
        + x * (2.19418839 + x * (4.84296658 + x * (-14.18503333 + x * (4.27729857 + x * 2.82956604))))
    )
    b = (
        0.10667330
        + x * (12.64194608 + x * (-60.58204836 + x * (110.36276771 + x * (-89.90310912 + x * 27.34824973))))
    )

    rgb = np.stack([r, g, b], axis=-1)
    return np.clip(rgb, 0.0, 1.0).astype(np.float32)


def _to_comfy_image(rgb_or_scalar: np.ndarray) -> Any:
    import torch  # type: ignore

    arr = np.asarray(rgb_or_scalar, dtype=np.float32)
    if arr.ndim == 2:
        arr = np.stack([arr, arr, arr], axis=-1)
    if arr.ndim != 3 or arr.shape[-1] != 3:
        raise ValueError("Expected (H,W) or (H,W,3) array")
    arr = np.clip(arr, 0.0, 1.0)
    return torch.from_numpy(arr)[None, :, :, :]


def _overlay_text_top_left(image_rgb01: np.ndarray, text: str) -> np.ndarray:
    try:
        from PIL import Image, ImageDraw  # type: ignore
    except ModuleNotFoundError:
        return image_rgb01

    arr = np.asarray(image_rgb01, dtype=np.float32)
    arr = np.clip(arr, 0.0, 1.0)
    img = Image.fromarray((arr * 255.0).astype(np.uint8), mode="RGB")
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, max(1, int(img.width * 0.55)), 14], fill=(0, 0, 0))
    draw.text((2, 1), str(text), fill=(255, 255, 255))
    out = np.asarray(img, dtype=np.uint8).astype(np.float32) / 255.0
    return out


def _safe_int(value: int, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _safe_float(value: float, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _parse_json_dict(text: str) -> Dict[str, Any]:
    raw = (text or "").strip()
    if (not raw) or (raw.lower() in {"none", "null"}):
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("JSON must be an object/dict")
    return parsed



def _parse_json_list(text: str) -> List[Any]:
    raw = (text or "").strip()
    if (not raw) or (raw.lower() in {"none", "null"}):
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc
    if not isinstance(parsed, list):
        raise ValueError("JSON must be a list")
    return parsed


def _build_config(
    *,
    backend: str,
    device: str,
    width: int,
    height: int,
    boundary: str,
    initial_noise: float,
    dynamics_overrides_json: str,
) -> DETMConfig:
    overrides = _parse_json_dict(dynamics_overrides_json)
    config = DETMConfig(
        backend=str(backend),
        device=str(device),
        width=int(width),
        height=int(height),
        boundary=str(boundary),
        initial_noise=float(initial_noise),
    )
    if overrides:
        data = config.to_dict()
        dyn = data.get("dynamics", {})
        if not isinstance(dyn, dict):
            dyn = {}
        dyn.update(overrides)
        data["dynamics"] = dyn
        config = DETMConfig.from_dict(data)
    return config


def _make_influence(
    *,
    symbol_id: str,
    amplitude: float,
    phase: float,
    seed: int,
    cx: int,
    cy: int,
    radius: int,
    external_features_json: str,
    dynamics_overrides_json: str,
) -> DETMInfluence | None:
    sid = (symbol_id or "").strip()
    if not sid or sid.lower() in {"none", "null", "off", "-"}:
        return None

    # ACGS-style numeric symbol: map to DETM symbol alphabet.
    resolved_id = sid
    try:
        numeric = int(sid)
        alphabet_ids = list_symbols()
        if alphabet_ids:
            resolved_id = alphabet_ids[numeric % len(alphabet_ids)]
    except Exception:
        resolved_id = sid

    params: Dict[str, Any] = {}
    params["amplitude"] = float(amplitude)
    if abs(float(phase)) > 1e-12:
        params["phase"] = float(phase)
    if int(seed) >= 0:
        params["seed"] = int(seed)
    if int(radius) > 0:
        params["region"] = (int(cx), int(cy), int(radius))

    if external_features_json.strip():
        ext = _parse_json_dict(external_features_json)
        params["external_features"] = {str(k): float(v) for k, v in ext.items()}

    if dynamics_overrides_json.strip():
        dyn = _parse_json_dict(dynamics_overrides_json)
        params["dynamics_overrides"] = {str(k): float(v) for k, v in dyn.items()}

    # Use symbol template defaults when available.
    try:
        return make_symbol(resolved_id, **params)
    except Exception:
        return DETMInfluence(symbol_id=resolved_id, **params)


def _make_influence_from_dict(payload: Dict[str, Any]) -> DETMInfluence | None:
    sid = str(payload.get("symbol_id", "")).strip()
    if not sid:
        return None

    def g(name: str, default: Any = None) -> Any:
        return payload[name] if name in payload else default

    return _make_influence(
        symbol_id=sid,
        amplitude=_safe_float(g("amplitude", 1.0), 1.0),
        phase=_safe_float(g("phase", 0.0), 0.0),
        seed=_safe_int(g("seed", -1), -1),
        cx=_safe_int(g("region_cx", g("cx", 0)), 0),
        cy=_safe_int(g("region_cy", g("cy", 0)), 0),
        radius=_safe_int(g("region_radius", g("radius", 0)), 0),
        external_features_json=json.dumps(g("external_features", {})) if isinstance(g("external_features", {}), dict) else "",
        dynamics_overrides_json=json.dumps(g("dynamics_overrides", {})) if isinstance(g("dynamics_overrides", {}), dict) else "",
    )


def _diag_to_jsonable(diag: Dict[str, Any]) -> Dict[str, Any]:
    def convert(v: Any) -> Any:
        if isinstance(v, (str, int, float, bool)) or v is None:
            return v
        if isinstance(v, (list, tuple)):
            return [convert(x) for x in v]
        if isinstance(v, dict):
            return {str(k): convert(val) for k, val in v.items()}
        if hasattr(v, "as_dict") and callable(getattr(v, "as_dict")):
            return convert(v.as_dict())
        if hasattr(v, "__dict__"):
            return convert(vars(v))
        return str(v)

    return convert(diag)


def _compute_acgs_signature(symbol: int | None, detm_signature_vector: List[float], width: int, height: int) -> List[float]:
    if symbol is None or symbol < 0:
        return [0.0, 0.0, 0.0, 0.0, 0.0]
    angle = 2.0 * float(np.pi) * (int(symbol) % 10) / 10.0
    sin_v = float(np.sin(angle))
    cos_v = float(np.cos(angle))
    center_x = float(detm_signature_vector[7]) if len(detm_signature_vector) > 7 else 0.0
    center_y = float(detm_signature_vector[8]) if len(detm_signature_vector) > 8 else 0.0
    w = float(max(1, width - 1))
    h = float(max(1, height - 1))
    tx = (center_x / w) * 2.0 - 1.0
    ty = (center_y / h) * 2.0 - 1.0
    return [sin_v, cos_v, float(tx), float(ty), 1.0]


def _stack_image_batch(images: List[Any], *, fallback: Any):
    import torch  # type: ignore

    if not images:
        return fallback
    try:
        return torch.cat(images, dim=0)
    except Exception:
        return fallback


def _plot_series_as_image(series: List[float], *, width: int = 512, height: int = 256):
    import torch  # type: ignore

    w = int(max(32, width))
    h = int(max(32, height))
    img = np.zeros((h, w, 3), dtype=np.float32)

    if not series:
        return torch.from_numpy(img)[None, :, :, :]

    y = np.asarray(series, dtype=np.float32)
    y = np.nan_to_num(y, nan=0.0, posinf=0.0, neginf=0.0)
    ymin = float(y.min())
    ymax = float(y.max())
    if abs(ymax - ymin) < 1e-9:
        ymax = ymin + 1e-9

    xs = np.linspace(0, w - 1, num=len(y), dtype=np.float32)
    ys = (1.0 - (y - ymin) / (ymax - ymin)) * (h - 1)

    for i in range(1, len(y)):
        x0 = int(round(xs[i - 1]))
        y0 = int(round(ys[i - 1]))
        x1 = int(round(xs[i]))
        y1 = int(round(ys[i]))
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for s in range(steps + 1):
            t = s / float(steps)
            xi = int(round(x0 + (x1 - x0) * t))
            yi = int(round(y0 + (y1 - y0) * t))
            if 0 <= xi < w and 0 <= yi < h:
                img[yi, xi, :] = 1.0

    img[0, :, :] = 0.25
    img[-1, :, :] = 0.25
    img[:, 0, :] = 0.25
    img[:, -1, :] = 0.25

    return torch.from_numpy(img)[None, :, :, :]


def _extract_series_from_diag(diag: Dict[str, Any], key: str) -> List[float]:
    history = diag.get("history", [])
    if not isinstance(history, list):
        return []

    key = str(key)
    vec_idx_map = {
        "energy_mean": 0,
        "energy_var": 1,
        "energy_min": 2,
        "energy_max": 3,
        "entropy_mean": 4,
        "entropy_var": 5,
        "tau_mean": 6,
        "center_x": 7,
        "center_y": 8,
    }

    out: List[float] = []
    for item in history:
        if not isinstance(item, dict):
            continue
        sig = item.get("signature", {})
        if isinstance(sig, dict):
            summary = sig.get("summary")
            if isinstance(summary, dict) and key in summary:
                try:
                    out.append(float(summary[key]))
                    continue
                except Exception:
                    pass
            vector = sig.get("vector")
            if isinstance(vector, list):
                idx = vec_idx_map.get(key)
                if idx is not None and idx < len(vector):
                    try:
                        out.append(float(vector[idx]))
                        continue
                    except Exception:
                        pass
        fs = item.get("field_summaries", {})
        if isinstance(fs, dict) and key.endswith("_mean"):
            field_name = key.replace("_mean", "")
            field_obj = fs.get(field_name)
            if isinstance(field_obj, dict) and "mean" in field_obj:
                try:
                    out.append(float(field_obj["mean"]))
                    continue
                except Exception:
                    pass
    return out


def _dominant_frequency(series: List[float]) -> Dict[str, float]:
    arr = np.asarray(series, dtype=float)
    if arr.size < 4:
        return {"freq": 0.0, "power": 0.0}
    arr = arr - float(arr.mean())
    spectrum = np.fft.rfft(arr)
    power = spectrum.real**2 + spectrum.imag**2
    if power.shape[0] <= 1:
        return {"freq": 0.0, "power": 0.0}
    idx = 1 + int(np.argmax(power[1:]))
    freqs = np.fft.rfftfreq(arr.size, d=1.0)
    return {"freq": float(freqs[idx]), "power": float(power[idx])}


def _window_series(series: List[float], *, window: int, stride: int, normalize: bool) -> List[List[float]]:
    w = int(max(1, window))
    s = int(max(1, stride))
    if len(series) < w:
        return []
    windows: List[List[float]] = []
    for start in range(0, len(series) - w + 1, s):
        chunk = [float(v) for v in series[start : start + w]]
        if normalize:
            mean = float(np.mean(chunk))
            std = float(np.std(chunk)) + 1e-9
            chunk = [(v - mean) / std for v in chunk]
        windows.append(chunk)
    return windows


def _save_gif_from_image_batch(images, *, out_path: str, fps: int, loop: int, max_frames: int) -> str:
    try:
        from PIL import Image
    except Exception as exc:
        raise RuntimeError("Pillow (PIL) is required to save GIFs") from exc

    arr = _to_numpy(images)
    if arr.ndim != 4 or arr.shape[-1] != 3:
        raise ValueError("Expected IMAGE batch with shape [B,H,W,3]")

    b = int(arr.shape[0])
    limit = int(max(1, max_frames))
    b = min(b, limit)
    arr = np.clip(arr[:b] * 255.0, 0.0, 255.0).astype(np.uint8)

    frames = [Image.fromarray(arr[i], mode="RGB") for i in range(b)]
    duration_ms = int(round(1000.0 / float(max(1, int(fps)))))

    out = Path(out_path).expanduser()
    if not str(out).lower().endswith(".gif"):
        out.mkdir(parents=True, exist_ok=True)
        out = out / f"detm_{time.strftime('%Y%m%d_%H%M%S')}.gif"
    else:
        out.parent.mkdir(parents=True, exist_ok=True)

    frames[0].save(
        out,
        save_all=True,
        append_images=frames[1:],
        duration=duration_ms,
        loop=int(max(0, loop)),
        optimize=False,
    )
    return str(out.resolve())


def _upgrade_state_to_torch_if_possible(state) -> None:
    """Convert deserialized numpy fields back to torch tensors if config requests torch.

    DETM serialization is portable and stores arrays as numpy; in ComfyUI we
    usually want to execute steps on torch backend again (CPU/CUDA).
    """

    try:
        import torch  # type: ignore
    except ModuleNotFoundError:
        return

    config = DETMConfig.from_dict(state.config) if state.config else DETMConfig()
    if str(config.backend) != "torch":
        return

    lattice = state.lattice
    device_spec = str(config.device or "cpu")
    try:
        device = torch.device(device_spec)
        if device.type == "cuda" and not torch.cuda.is_available():
            device = torch.device("cpu")
    except Exception:
        device = torch.device("cpu")
    dtype = torch.float64

    energy = _to_numpy(state.field_state.energy).reshape(lattice.height, lattice.width).astype(np.float64, copy=False)
    entropy = _to_numpy(state.field_state.entropy).reshape(lattice.height, lattice.width).astype(np.float64, copy=False)
    internal_time = (
        _to_numpy(state.field_state.internal_time)
        .reshape(lattice.height, lattice.width)
        .astype(np.float64, copy=False)
    )
    state.field_state.energy = torch.tensor(energy, device=device, dtype=dtype)
    state.field_state.entropy = torch.tensor(entropy, device=device, dtype=dtype)
    state.field_state.internal_time = torch.tensor(internal_time, device=device, dtype=dtype)


def _write_artifacts(
    *,
    out_dir: str,
    tag: str,
    config: DETMConfig,
    seed: int,
    state_blob: bytes,
    history: List[Dict[str, Any]],
    extra: Dict[str, Any],
) -> str:
    root = Path(out_dir).expanduser().resolve()
    run_id = f"{time.strftime('%Y%m%d_%H%M%S')}_{tag}"
    run_dir = root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    (run_dir / "config.json").write_text(json.dumps(config.to_dict(), indent=2), encoding="utf-8")
    (run_dir / "meta.json").write_text(
        json.dumps({"seed": int(seed), **extra}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (run_dir / "history.jsonl").write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in history) + ("\n" if history else ""),
        encoding="utf-8",
    )
    (run_dir / "state.msgpack").write_bytes(state_blob)
    return str(run_dir)


def _config_json_from_config(config: DETMConfig) -> str:
    return json.dumps(config.to_dict(), ensure_ascii=False)


def _config_from_config_json(config_json: str) -> DETMConfig:
    raw = (config_json or "").strip()
    if not raw:
        return DETMConfig()
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("config_json must be a JSON object")
    return DETMConfig.from_dict(payload)


def _events_due_for_tick(events: List[Dict[str, Any]], tick: int) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    due: List[Dict[str, Any]] = []
    future: List[Dict[str, Any]] = []
    for ev in events:
        if not isinstance(ev, dict):
            continue
        due_tick = ev.get("due_tick")
        try:
            due_tick_int = int(due_tick) # type: ignore
        except Exception:
            due_tick_int = None
        if due_tick_int is None or due_tick_int <= tick:
            due.append(ev)
        else:
            future.append(ev)
    return due, future

# -----------------------------------------------------------------------------
# Star-import support
# -----------------------------------------------------------------------------
# Python's `from module import *` skips names that start with '_' unless the
# module defines __all__. Our ComfyUI nodes intentionally import helpers with
# underscore-prefixes (e.g. _get_session, _build_config) from this module.
# Defining __all__ makes those helpers available.

__all__ = [
    "DETMConfig",
    "_get_session",
    "_to_numpy",
    "_field_to_comfy_image",
    "_normalize_scalar_field",
    "_apply_turbo_colormap",
    "_to_comfy_image",
    "_overlay_text_top_left",
    "_safe_int",
    "_safe_float",
    "_parse_json_dict",
    "_parse_json_list",
    "_build_config",
    "_make_influence",
    "_make_influence_from_dict",
    "_diag_to_jsonable",
    "_compute_acgs_signature",
    "_stack_image_batch",
    "_plot_series_as_image",
    "_extract_series_from_diag",
    "_dominant_frequency",
    "_window_series",
    "_save_gif_from_image_batch",
    "_upgrade_state_to_torch_if_possible",
    "_write_artifacts",
    "_config_json_from_config",
    "_config_from_config_json",
    "_events_due_for_tick",
]
