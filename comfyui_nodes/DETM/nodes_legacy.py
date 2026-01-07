from __future__ import annotations

from .core import *  # noqa: F401,F403
from .nodes_scheduler import (
    DETMConfigNode,
    DETMSchedulerTickNode,
    DETMBusPublishNode,
    DETMMakeInfluenceEventNode,
)
from .nodes_runtime import DETMRunPubNode
from .nodes_analysis import (
    DETMStateToImageNode,
    DETMSeriesBufferNode,
    DETMFrameBufferNode,
    DETMDetectAttractorsNode,
)

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


