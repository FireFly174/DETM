from __future__ import annotations

import base64
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _ensure_detm_on_path() -> None:
    try:
        import detm  # noqa: F401
        return
    except Exception:
        pass

    # If this pack lives inside the DETM repo (recommended), the repo root is:
    # `<repo>/comfyui_nodes/DETM/nodes.py` -> parents[2] == `<repo>`.
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))


_ensure_detm_on_path()

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
    if not raw:
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
    if not raw:
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
            due_tick_int = int(due_tick)
        except Exception:
            due_tick_int = None
        if due_tick_int is None or due_tick_int <= tick:
            due.append(ev)
        else:
            future.append(ev)
    return due, future


class DETMInitNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "seed": ("INT", {"default": 1, "min": 0, "max": 2**31 - 1}),
                "backend": (["torch", "numpy"], {"default": "torch"}),
                "device": ("STRING", {"default": "cuda"}),
                "width": ("INT", {"default": 24, "min": 4, "max": 2048}),
                "height": ("INT", {"default": 24, "min": 4, "max": 2048}),
                "boundary": (["periodic", "open"], {"default": "periodic"}),
                "initial_noise": ("FLOAT", {"default": 0.08, "min": 0.0, "max": 1.0, "step": 0.01}),
                "dynamics_overrides_json": ("STRING", {"default": ""}),
                "emit_image_field": (["energy", "entropy", "internal_time"], {"default": "energy"}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "IMAGE")
    RETURN_NAMES = ("state_b64", "diag_json", "image")
    FUNCTION = "run"
    CATEGORY = "DETM/Legacy"

    def run(
        self,
        seed: int,
        backend: str,
        device: str,
        width: int,
        height: int,
        boundary: str,
        initial_noise: float,
        dynamics_overrides_json: str,
        emit_image_field: str,
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
        state = api.reset(config, int(seed))
        sig = api.digest(state)

        lattice = state.lattice
        energy = _to_numpy(state.field_state.energy).reshape(lattice.height, lattice.width)
        entropy = _to_numpy(state.field_state.entropy).reshape(lattice.height, lattice.width)
        internal_time = _to_numpy(state.field_state.internal_time).reshape(lattice.height, lattice.width)
        field_map = {"energy": energy, "entropy": entropy, "internal_time": internal_time}
        image = _field_to_comfy_image(field_map.get(str(emit_image_field), energy))

        blob = serialize_state(state)
        state_b64 = base64.b64encode(blob).decode("ascii")

        diag: Dict[str, Any] = {
            "kind": "detm_init",
            "seed": int(seed),
            "config": config.to_dict(),
            "step_count": int(state.step_count),
            "signature": sig.as_dict(),
            "field_summaries": {
                "energy": sig.summary.get("energy_mean"),
                "entropy": sig.summary.get("entropy_mean"),
                "internal_time": sig.summary.get("internal_time_mean"),
            },
        }
        diag_json = json.dumps(_diag_to_jsonable(diag), ensure_ascii=False)
        return (state_b64, diag_json, image)


class DETMStepNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "state_b64": ("STRING", {"default": ""}),
                "n_ticks": ("INT", {"default": 16, "min": 1, "max": 1_000_000}),
                "diag_every": ("INT", {"default": 1, "min": 1, "max": 1_000_000}),
                "apply_mode": (["once", "each_tick", "none"], {"default": "once"}),
                "symbol_id": ("STRING", {"default": "pulse"}),
                "amplitude": ("FLOAT", {"default": 0.15, "min": -2.0, "max": 2.0, "step": 0.01}),
                "phase": ("FLOAT", {"default": 0.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                "influence_seed": ("INT", {"default": -1, "min": -1, "max": 2**31 - 1}),
                "region_cx": ("INT", {"default": 0, "min": -4096, "max": 4096}),
                "region_cy": ("INT", {"default": 0, "min": -4096, "max": 4096}),
                "region_radius": ("INT", {"default": 0, "min": 0, "max": 4096}),
                "external_features_json": ("STRING", {"default": ""}),
                "dynamics_overrides_json": ("STRING", {"default": ""}),
                "emit_image_field": (["energy", "entropy", "internal_time"], {"default": "energy"}),
                "frame_every": ("INT", {"default": 4, "min": 1, "max": 1_000_000}),
                "max_frames": ("INT", {"default": 120, "min": 1, "max": 10_000}),
                "frame_field": (["energy", "entropy", "internal_time"], {"default": "energy"}),
                "include_initial_frame": (["no", "yes"], {"default": "no"}),
                "save_dir": ("STRING", {"default": ""}),
                "save_tag": ("STRING", {"default": "detm"}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "IMAGE", "IMAGE")
    RETURN_NAMES = ("state_b64", "diag_json", "image", "frames")
    FUNCTION = "run"
    CATEGORY = "DETM/Legacy"

    def run(
        self,
        state_b64: str,
        n_ticks: int,
        diag_every: int,
        apply_mode: str,
        symbol_id: str,
        amplitude: float,
        phase: float,
        influence_seed: int,
        region_cx: int,
        region_cy: int,
        region_radius: int,
        external_features_json: str,
        dynamics_overrides_json: str,
        emit_image_field: str,
        frame_every: int,
        max_frames: int,
        frame_field: str,
        include_initial_frame: str,
        save_dir: str,
        save_tag: str,
    ):
        blob = base64.b64decode(state_b64.encode("ascii")) if state_b64.strip() else b""
        if not blob:
            raise ValueError("state_b64 is empty; use the DETM Init node first")

        state = deserialize_state(blob)
        _upgrade_state_to_torch_if_possible(state)
        config = DETMConfig.from_dict(state.config) if state.config else DETMConfig()

        influence = _make_influence(
            symbol_id=symbol_id,
            amplitude=amplitude,
            phase=phase,
            seed=influence_seed,
            cx=region_cx,
            cy=region_cy,
            radius=region_radius,
            external_features_json=external_features_json,
            dynamics_overrides_json=dynamics_overrides_json,
        )
        if str(apply_mode) == "none":
            influence = None

        n_ticks = int(n_ticks)
        diag_every = max(1, int(diag_every))
        frame_every = max(1, int(frame_every))
        max_frames = max(1, int(max_frames))

        history: List[Dict[str, Any]] = []
        signatures: List[np.ndarray] = []
        last_obs = None
        frames: List[Any] = []

        start_tick = int(state.step_count)
        wall_start = time.perf_counter()

        if include_initial_frame == "yes" and len(frames) < max_frames:
            lattice0 = state.lattice
            field0 = _to_numpy(getattr(state.field_state, str(frame_field))).reshape(lattice0.height, lattice0.width)
            frames.append(_field_to_comfy_image(field0))

        for local_tick in range(1, n_ticks + 1):
            state, obs = api.step(state, influence, n_ticks=1, rng=None)
            last_obs = obs

            if (local_tick % frame_every) == 0 or local_tick == n_ticks:
                if len(frames) < max_frames:
                    lattice_f = state.lattice
                    field_f = _to_numpy(getattr(state.field_state, str(frame_field))).reshape(
                        lattice_f.height, lattice_f.width
                    )
                    frames.append(_field_to_comfy_image(field_f))

            if (local_tick % diag_every) == 0 or local_tick == n_ticks:
                row = {
                    "tick": int(state.step_count),
                    "signature": obs.signature.as_dict(),
                    "events": obs.events,
                    "cost": obs.cost,
                    "quality": obs.quality,
                    "field_summaries": {
                        "energy": obs.field_summaries.energy,
                        "entropy": obs.field_summaries.entropy,
                        "internal_time": obs.field_summaries.internal_time,
                    },
                }
                history.append(row)
                signatures.append(np.asarray(obs.signature.vector, dtype=float))

            if str(apply_mode) == "once":
                influence = None

        wall_elapsed_ms = (time.perf_counter() - wall_start) * 1000.0

        if last_obs is None:
            raise RuntimeError("No observables produced")

        lattice = state.lattice
        energy = _to_numpy(state.field_state.energy).reshape(lattice.height, lattice.width)
        entropy = _to_numpy(state.field_state.entropy).reshape(lattice.height, lattice.width)
        internal_time = _to_numpy(state.field_state.internal_time).reshape(lattice.height, lattice.width)
        field_map = {"energy": energy, "entropy": entropy, "internal_time": internal_time}
        image = _field_to_comfy_image(field_map.get(str(emit_image_field), energy))
        frames_batch = _stack_image_batch(frames, fallback=image)

        sig = api.digest(state)
        stability = stability_metrics(signatures)

        symbol_int = None
        try:
            symbol_int = int(symbol_id)  # allow numeric symbols for ACGS parity
        except Exception:
            symbol_int = None

        diag: Dict[str, Any] = {
            "kind": "detm_step",
            "config": config.to_dict(),
            "start_tick": start_tick,
            "end_tick": int(state.step_count),
            "n_ticks": int(n_ticks),
            "diag_every": int(diag_every),
            "signature_final": sig.as_dict(),
            "history": history,
            "stability": asdict(stability),
            "acgs": {
                "signature": _compute_acgs_signature(symbol_int, sig.vector, lattice.width, lattice.height),
                "cost_proxy": float(last_obs.cost.get("cpu_time_ms", 0.0)),
            },
            "timing": {"wall_time_ms": float(wall_elapsed_ms)},
        }

        blob_out = serialize_state(state)
        state_b64_out = base64.b64encode(blob_out).decode("ascii")
        diag_json = json.dumps(_diag_to_jsonable(diag), ensure_ascii=False)

        if save_dir.strip():
            _write_artifacts(
                out_dir=save_dir,
                tag=str(save_tag or "detm"),
                config=config,
                seed=-1,
                state_blob=blob_out,
                history=history,
                extra={"start_tick": start_tick, "end_tick": int(state.step_count), "wall_time_ms": wall_elapsed_ms},
            )

        return (state_b64_out, diag_json, image, frames_batch)


class DETMRunNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "seed": ("INT", {"default": 1, "min": 0, "max": 2**31 - 1}),
                "backend": (["torch", "numpy"], {"default": "torch"}),
                "device": ("STRING", {"default": "cuda"}),
                "width": ("INT", {"default": 24, "min": 4, "max": 2048}),
                "height": ("INT", {"default": 24, "min": 4, "max": 2048}),
                "boundary": (["periodic", "open"], {"default": "periodic"}),
                "initial_noise": ("FLOAT", {"default": 0.08, "min": 0.0, "max": 1.0, "step": 0.01}),
                "config_dynamics_overrides_json": ("STRING", {"default": ""}),
                "n_ticks": ("INT", {"default": 64, "min": 1, "max": 1_000_000}),
                "diag_every": ("INT", {"default": 1, "min": 1, "max": 1_000_000}),
                "apply_mode": (["once", "each_tick", "none"], {"default": "once"}),
                "symbol_id": ("STRING", {"default": "pulse"}),
                "amplitude": ("FLOAT", {"default": 0.15, "min": -2.0, "max": 2.0, "step": 0.01}),
                "phase": ("FLOAT", {"default": 0.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                "influence_seed": ("INT", {"default": -1, "min": -1, "max": 2**31 - 1}),
                "region_cx": ("INT", {"default": 0, "min": -4096, "max": 4096}),
                "region_cy": ("INT", {"default": 0, "min": -4096, "max": 4096}),
                "region_radius": ("INT", {"default": 0, "min": 0, "max": 4096}),
                "external_features_json": ("STRING", {"default": ""}),
                "dynamics_overrides_json": ("STRING", {"default": ""}),
                "emit_image_field": (["energy", "entropy", "internal_time"], {"default": "energy"}),
                "frame_every": ("INT", {"default": 4, "min": 1, "max": 1_000_000}),
                "max_frames": ("INT", {"default": 120, "min": 1, "max": 10_000}),
                "frame_field": (["energy", "entropy", "internal_time"], {"default": "energy"}),
                "include_initial_frame": (["no", "yes"], {"default": "no"}),
                "save_dir": ("STRING", {"default": ""}),
                "save_tag": ("STRING", {"default": "detm"}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "IMAGE", "IMAGE")
    RETURN_NAMES = ("state_b64", "diag_json", "image", "frames")
    FUNCTION = "run"
    CATEGORY = "DETM/Legacy"

    def run(
        self,
        seed: int,
        backend: str,
        device: str,
        width: int,
        height: int,
        boundary: str,
        initial_noise: float,
        config_dynamics_overrides_json: str,
        n_ticks: int,
        diag_every: int,
        apply_mode: str,
        symbol_id: str,
        amplitude: float,
        phase: float,
        influence_seed: int,
        region_cx: int,
        region_cy: int,
        region_radius: int,
        external_features_json: str,
        dynamics_overrides_json: str,
        emit_image_field: str,
        frame_every: int,
        max_frames: int,
        frame_field: str,
        include_initial_frame: str,
        save_dir: str,
        save_tag: str,
    ):
        config = _build_config(
            backend=backend,
            device=device,
            width=width,
            height=height,
            boundary=boundary,
            initial_noise=initial_noise,
            dynamics_overrides_json=config_dynamics_overrides_json,
        )
        state = api.reset(config, int(seed))
        blob = serialize_state(state)
        state_b64 = base64.b64encode(blob).decode("ascii")

        step_node = DETMStepNode()
        return step_node.run(
            state_b64=state_b64,
            n_ticks=n_ticks,
            diag_every=diag_every,
            apply_mode=apply_mode,
            symbol_id=symbol_id,
            amplitude=amplitude,
            phase=phase,
            influence_seed=influence_seed,
            region_cx=region_cx,
            region_cy=region_cy,
            region_radius=region_radius,
            external_features_json=external_features_json,
            dynamics_overrides_json=dynamics_overrides_json,
            emit_image_field=emit_image_field,
            frame_every=frame_every,
            max_frames=max_frames,
            frame_field=frame_field,
            include_initial_frame=include_initial_frame,
            save_dir=save_dir,
            save_tag=save_tag,
        )


class DETMTimeSeriesAnalyzeNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "diag_json": ("STRING", {"default": ""}),
                "series_key": (
                    [
                        "energy_mean",
                        "energy_var",
                        "entropy_mean",
                        "tau_mean",
                        "center_x",
                        "center_y",
                    ],
                    {"default": "energy_mean"},
                ),
                "window": ("INT", {"default": 32, "min": 2, "max": 8192}),
                "stride": ("INT", {"default": 8, "min": 1, "max": 8192}),
                "normalize": (["no", "yes"], {"default": "no"}),
                "plot_width": ("INT", {"default": 512, "min": 64, "max": 2048}),
                "plot_height": ("INT", {"default": 256, "min": 64, "max": 2048}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "IMAGE")
    RETURN_NAMES = ("windows_json", "summary_json", "plot_image")
    FUNCTION = "run"
    CATEGORY = "DETM/Analysis"

    def run(
        self,
        diag_json: str,
        series_key: str,
        window: int,
        stride: int,
        normalize: str,
        plot_width: int,
        plot_height: int,
    ):
        diag = _parse_json_dict(diag_json)
        series = _extract_series_from_diag(diag, str(series_key))
        windows = _window_series(series, window=int(window), stride=int(stride), normalize=(normalize == "yes"))
        dom = _dominant_frequency(series)
        summary = {
            "series_key": str(series_key),
            "n_points": int(len(series)),
            "n_windows": int(len(windows)),
            "dominant_frequency": dom,
            "stability": diag.get("stability"),
            "timing": diag.get("timing"),
            "acgs": diag.get("acgs"),
        }
        windows_json = json.dumps(windows, ensure_ascii=False)
        summary_json = json.dumps(_diag_to_jsonable(summary), ensure_ascii=False)
        plot = _plot_series_as_image(series, width=int(plot_width), height=int(plot_height))
        return (windows_json, summary_json, plot)


class DETMSaveGifNode:
    OUTPUT_NODE = True

    @classmethod
    def IS_CHANGED(cls, **_kwargs):  # type: ignore[override]
        return time.time()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE", {}),
                "out_path": ("STRING", {"default": "runs/out/gifs"}),
                "fps": ("INT", {"default": 12, "min": 1, "max": 240}),
                "loop": ("INT", {"default": 0, "min": 0, "max": 1000}),
                "max_frames": ("INT", {"default": 300, "min": 1, "max": 10_000}),
                "write": (["no", "yes"], {"default": "yes"}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("gif_path",)
    FUNCTION = "run"
    CATEGORY = "DETM/Output"

    def run(self, images, out_path: str, fps: int, loop: int, max_frames: int, write: str):
        if write != "yes":
            return ("",)
        gif_path = _save_gif_from_image_batch(
            images, out_path=str(out_path), fps=int(fps), loop=int(loop), max_frames=int(max_frames)
        )
        return (gif_path,)


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
        return (_config_json_from_config(config),)


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
                "config_json": ("STRING", {"default": "None"}),
                "seed": ("INT", {"default": 1, "min": 0, "max": 2**31 - 1}),
                "n_ticks_per_tick": ("INT", {"default": 1, "min": 0, "max": 1_000_000}),
                "due_events_json": ("STRING", {"default": "None"}),
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


class DETMRandomSearchNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "trials": ("INT", {"default": 16, "min": 1, "max": 10_000}),
                "seed0": ("INT", {"default": 1, "min": 0, "max": 2**31 - 1}),
                "objective": (
                    [
                        "dominant_power",
                        "oscillation_std",
                        "center_drift",
                        "min_stability_delta",
                        "max_stability_delta",
                    ],
                    {"default": "dominant_power"},
                ),
                "score_series_key": (
                    [
                        "energy_mean",
                        "energy_var",
                        "entropy_mean",
                        "tau_mean",
                        "center_x",
                        "center_y",
                    ],
                    {"default": "energy_mean"},
                ),
                "param_ranges_json": ("STRING", {"default": "{\"kappa\":[0.02,0.3],\"lambda_t\":[0.1,3.0]}"}),
                # Base config
                "backend": (["torch", "numpy"], {"default": "torch"}),
                "device": ("STRING", {"default": "cuda"}),
                "width": ("INT", {"default": 24, "min": 4, "max": 2048}),
                "height": ("INT", {"default": 24, "min": 4, "max": 2048}),
                "boundary": (["periodic", "open"], {"default": "periodic"}),
                "initial_noise": ("FLOAT", {"default": 0.08, "min": 0.0, "max": 1.0, "step": 0.01}),
                "config_dynamics_overrides_json": ("STRING", {"default": ""}),
                # Episode settings
                "n_ticks": ("INT", {"default": 128, "min": 1, "max": 1_000_000}),
                "diag_every": ("INT", {"default": 4, "min": 1, "max": 1_000_000}),
                "apply_mode": (["once", "each_tick", "none"], {"default": "once"}),
                "symbol_id": ("STRING", {"default": "pulse"}),
                "amplitude": ("FLOAT", {"default": 0.15, "min": -2.0, "max": 2.0, "step": 0.01}),
                "phase": ("FLOAT", {"default": 0.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                "influence_seed": ("INT", {"default": -1, "min": -1, "max": 2**31 - 1}),
                "region_cx": ("INT", {"default": 0, "min": -4096, "max": 4096}),
                "region_cy": ("INT", {"default": 0, "min": -4096, "max": 4096}),
                "region_radius": ("INT", {"default": 0, "min": 0, "max": 4096}),
                "external_features_json": ("STRING", {"default": ""}),
                "dynamics_overrides_json": ("STRING", {"default": ""}),
                # Best-run rendering
                "emit_image_field": (["energy", "entropy", "internal_time"], {"default": "energy"}),
                "frame_every": ("INT", {"default": 4, "min": 1, "max": 1_000_000}),
                "max_frames": ("INT", {"default": 120, "min": 1, "max": 10_000}),
                "frame_field": (["energy", "entropy", "internal_time"], {"default": "energy"}),
                "include_initial_frame": (["no", "yes"], {"default": "no"}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "FLOAT", "STRING", "IMAGE", "IMAGE")
    RETURN_NAMES = ("best_state_b64", "best_diag_json", "best_score", "best_config_json", "best_image", "best_frames")
    FUNCTION = "run"
    CATEGORY = "DETM/Legacy"

    def run(
        self,
        trials: int,
        seed0: int,
        objective: str,
        score_series_key: str,
        param_ranges_json: str,
        backend: str,
        device: str,
        width: int,
        height: int,
        boundary: str,
        initial_noise: float,
        config_dynamics_overrides_json: str,
        n_ticks: int,
        diag_every: int,
        apply_mode: str,
        symbol_id: str,
        amplitude: float,
        phase: float,
        influence_seed: int,
        region_cx: int,
        region_cy: int,
        region_radius: int,
        external_features_json: str,
        dynamics_overrides_json: str,
        emit_image_field: str,
        frame_every: int,
        max_frames: int,
        frame_field: str,
        include_initial_frame: str,
    ):
        base_config = _build_config(
            backend=backend,
            device=device,
            width=width,
            height=height,
            boundary=boundary,
            initial_noise=initial_noise,
            dynamics_overrides_json=config_dynamics_overrides_json,
        )

        ranges = _parse_json_dict(param_ranges_json)
        allowed = {
            "equilibrium_energy",
            "beta",
            "gamma",
            "kappa",
            "alpha",
            "lambda_t",
            "activation_threshold",
        }
        for k, v in list(ranges.items()):
            if k not in allowed:
                raise ValueError(f"Unsupported range key: {k}")
            if not (isinstance(v, list) and len(v) == 2 and all(isinstance(x, (int, float)) for x in v)):
                raise ValueError(f"Range for {k} must be [min,max]")

        def sample_overrides(rng: np.random.Generator) -> Dict[str, float]:
            out: Dict[str, float] = {}
            for k, v in ranges.items():
                lo = float(v[0])
                hi = float(v[1])
                if hi < lo:
                    lo, hi = hi, lo
                out[k] = float(rng.uniform(lo, hi))
            return out

        def eval_score(diag: Dict[str, Any]) -> float:
            series = _extract_series_from_diag(diag, str(score_series_key))
            if objective == "dominant_power":
                return float(_dominant_frequency(series)["power"])
            if objective == "oscillation_std":
                return float(np.std(series)) if series else 0.0
            if objective == "center_drift":
                xs = _extract_series_from_diag(diag, "center_x")
                ys = _extract_series_from_diag(diag, "center_y")
                if xs and ys and len(xs) == len(ys) and len(xs) >= 2:
                    dx = float(xs[-1] - xs[0])
                    dy = float(ys[-1] - ys[0])
                    return float((dx * dx + dy * dy) ** 0.5)
                return 0.0
            stability = diag.get("stability", {})
            delta = float(stability.get("delta", 0.0)) if isinstance(stability, dict) else 0.0
            if objective == "min_stability_delta":
                return -delta
            if objective == "max_stability_delta":
                return delta
            return 0.0

        def run_once(
            *,
            config: DETMConfig,
            seed: int,
            render: bool,
        ) -> Tuple[str, Dict[str, Any], Any, Any]:
            state = api.reset(config, int(seed))
            influence = _make_influence(
                symbol_id=symbol_id,
                amplitude=amplitude,
                phase=phase,
                seed=influence_seed,
                cx=region_cx,
                cy=region_cy,
                radius=region_radius,
                external_features_json=external_features_json,
                dynamics_overrides_json=dynamics_overrides_json,
            )
            if str(apply_mode) == "none":
                influence = None

            history: List[Dict[str, Any]] = []
            signatures: List[np.ndarray] = []
            frames: List[Any] = []
            n_ticks_i = int(n_ticks)
            diag_every_i = max(1, int(diag_every))
            frame_every_i = max(1, int(frame_every))
            max_frames_i = max(1, int(max_frames))

            if render and include_initial_frame == "yes" and len(frames) < max_frames_i:
                lattice0 = state.lattice
                field0 = _to_numpy(getattr(state.field_state, str(frame_field))).reshape(lattice0.height, lattice0.width)
                frames.append(_field_to_comfy_image(field0))

            start_tick = int(state.step_count)
            wall_start = time.perf_counter()
            last_obs = None
            for local_tick in range(1, n_ticks_i + 1):
                state, obs = api.step(state, influence, n_ticks=1, rng=None)
                last_obs = obs

                if render and ((local_tick % frame_every_i) == 0 or local_tick == n_ticks_i):
                    if len(frames) < max_frames_i:
                        lattice_f = state.lattice
                        field_f = _to_numpy(getattr(state.field_state, str(frame_field))).reshape(
                            lattice_f.height, lattice_f.width
                        )
                        frames.append(_field_to_comfy_image(field_f))

                if (local_tick % diag_every_i) == 0 or local_tick == n_ticks_i:
                    row = {
                        "tick": int(state.step_count),
                        "signature": obs.signature.as_dict(),
                        "events": obs.events,
                        "cost": obs.cost,
                        "quality": obs.quality,
                        "field_summaries": {
                            "energy": obs.field_summaries.energy,
                            "entropy": obs.field_summaries.entropy,
                            "internal_time": obs.field_summaries.internal_time,
                        },
                    }
                    history.append(row)
                    signatures.append(np.asarray(obs.signature.vector, dtype=float))

                if str(apply_mode) == "once":
                    influence = None

            wall_elapsed_ms = (time.perf_counter() - wall_start) * 1000.0
            if last_obs is None:
                raise RuntimeError("No observables produced")

            lattice = state.lattice
            energy = _to_numpy(state.field_state.energy).reshape(lattice.height, lattice.width)
            entropy = _to_numpy(state.field_state.entropy).reshape(lattice.height, lattice.width)
            internal_time = _to_numpy(state.field_state.internal_time).reshape(lattice.height, lattice.width)
            field_map = {"energy": energy, "entropy": entropy, "internal_time": internal_time}
            image = _field_to_comfy_image(field_map.get(str(emit_image_field), energy))

            sig = api.digest(state)
            stability = stability_metrics(signatures)
            symbol_int = None
            try:
                symbol_int = int(symbol_id)
            except Exception:
                symbol_int = None

            diag: Dict[str, Any] = {
                "kind": "detm_search_run",
                "config": config.to_dict(),
                "start_tick": start_tick,
                "end_tick": int(state.step_count),
                "n_ticks": int(n_ticks_i),
                "diag_every": int(diag_every_i),
                "signature_final": sig.as_dict(),
                "history": history,
                "stability": asdict(stability),
                "acgs": {
                    "signature": _compute_acgs_signature(symbol_int, sig.vector, lattice.width, lattice.height),
                    "cost_proxy": float(last_obs.cost.get("cpu_time_ms", 0.0)),
                },
                "timing": {"wall_time_ms": float(wall_elapsed_ms)},
            }

            blob_out = serialize_state(state)
            state_b64_out = base64.b64encode(blob_out).decode("ascii")
            frames_batch = _stack_image_batch(frames, fallback=image) if render else image
            return state_b64_out, diag, image, frames_batch

        rng = np.random.default_rng(int(seed0))
        best_score = -float("inf")
        best_overrides: Dict[str, float] = {}
        best_seed = int(seed0)

        for i in range(int(trials)):
            overrides = sample_overrides(rng)
            cfg_dict = base_config.to_dict()
            dyn = cfg_dict.get("dynamics", {})
            if not isinstance(dyn, dict):
                dyn = {}
            dyn.update({k: float(v) for k, v in overrides.items()})
            cfg_dict["dynamics"] = dyn
            config_i = DETMConfig.from_dict(cfg_dict)

            _, diag_i, _, _ = run_once(config=config_i, seed=int(seed0) + i, render=False)
            score_i = float(eval_score(diag_i))
            if score_i > best_score:
                best_score = score_i
                best_overrides = overrides
                best_seed = int(seed0) + i

        cfg_dict = base_config.to_dict()
        dyn = cfg_dict.get("dynamics", {})
        if not isinstance(dyn, dict):
            dyn = {}
        dyn.update({k: float(v) for k, v in best_overrides.items()})
        cfg_dict["dynamics"] = dyn
        best_config = DETMConfig.from_dict(cfg_dict)

        best_state_b64, best_diag, best_image, best_frames = run_once(config=best_config, seed=best_seed, render=True)
        best_diag["search"] = {
            "trials": int(trials),
            "objective": str(objective),
            "score_series_key": str(score_series_key),
            "best_score": float(best_score),
            "best_seed": int(best_seed),
            "best_overrides": {k: float(v) for k, v in best_overrides.items()},
        }

        return (
            best_state_b64,
            json.dumps(_diag_to_jsonable(best_diag), ensure_ascii=False),
            float(best_score),
            json.dumps(best_config.to_dict(), ensure_ascii=False),
            best_image,
            best_frames,
        )


NODE_CLASS_MAPPINGS = {
    "DETM Run": DETMRunPubNode,
    "DETM Run (legacy init+step)": DETMRunNode,
    "DETM Init (legacy)": DETMInitNode,
    "DETM Step (legacy)": DETMStepNode,
    "DETM TimeSeries Analyze": DETMTimeSeriesAnalyzeNode,
    "DETM Save GIF": DETMSaveGifNode,
    "DETM Random Search (legacy)": DETMRandomSearchNode,
    "DETM Config": DETMConfigNode,
    "DETM Scheduler Tick": DETMSchedulerTickNode,
    "DETM Bus Publish": DETMBusPublishNode,
    "DETM Make Influence Event": DETMMakeInfluenceEventNode,
    "DETM State To Image": DETMStateToImageNode,
    "DETM Series Buffer": DETMSeriesBufferNode,
    "DETM Frame Buffer": DETMFrameBufferNode,
    "DETM Detect Attractors": DETMDetectAttractorsNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DETM Run": "DETM: Run",
    "DETM Run (legacy init+step)": "DETM: Run (legacy)",
    "DETM Init (legacy)": "DETM: Init (legacy)",
    "DETM Step (legacy)": "DETM: Step (legacy)",
    "DETM TimeSeries Analyze": "DETM: TimeSeries Analyze (windows)",
    "DETM Save GIF": "DETM: Save GIF (frames)",
    "DETM Random Search (legacy)": "DETM: Random Search (legacy)",
    "DETM Config": "DETM: Config (json)",
    "DETM Scheduler Tick": "DETM: Scheduler Tick",
    "DETM Bus Publish": "DETM: Bus Publish (events)",
    "DETM Make Influence Event": "DETM: Make Influence Event",
    "DETM State To Image": "DETM: State -> Image",
    "DETM Series Buffer": "DETM: Series Buffer (state->windows)",
    "DETM Frame Buffer": "DETM: Frame Buffer (state->frames)",
    "DETM Detect Attractors": "DETM: Detect Attractors",
}
