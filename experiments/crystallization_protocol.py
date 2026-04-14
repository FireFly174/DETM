"""Long-run crystallization sweeps for DETM core dynamics.

The protocol runs deterministic long trajectories over seeds and parameter
combinations, stops early when a simple crystallization heuristic is met, and
emits compact artifacts suitable for visual/manual comparison:

- per-step metrics CSV,
- final state + crystallization snapshot in ``.npz``,
- quicklook PNG with initial / crystallization / final energy fields,
- per-run JSON summaries and a batch catalog.

The crystallization heuristic is intentionally operational rather than
theoretical. A run is considered crystallized when, on a rolling window:

- mean absolute energy delta is sufficiently small,
- energy variance and structure score are stable,
- structure score stays above a small floor, so a flat frozen field does not
  trivially count as a crystal.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import colors

from detm.core.entropy import DynamicsParameters
from detm.core.fields import Lattice
from detm.runtime.backends import Backend, NumpyBackend, TorchBackend
from detm.runtime.diagnostics.attractors import detect_attractors
from detm.runtime.state import DETMFieldState
from experiments.configuration import load_structured_config, pick


@dataclass(frozen=True)
class InitialStateConfig:
    equilibrium_energy: float
    noise: float
    marker_radius: int = 0
    marker_energy: float | None = None
    marker_center: tuple[int, int] | None = None


@dataclass(frozen=True)
class CrystallizationConfig:
    window: int = 96
    min_steps: int = 256
    max_steps: int = 1200
    delta_mean_threshold: float = 0.0012
    energy_var_std_threshold: float = 0.00025
    structure_std_threshold: float = 0.0008
    min_structure_score: float = 0.015
    snapshot_steps: tuple[int, ...] = (150, 300, 600, 900, 1200)


@dataclass(frozen=True)
class RunCombo:
    seed: int
    size: int
    boundary: str
    initial: InitialStateConfig
    dynamics: DynamicsParameters


@dataclass(frozen=True)
class ExecutionConfig:
    backend: str = "numpy"
    device: str = "cpu"


def _sequence(value: Any, default: Sequence[Any]) -> list[Any]:
    if value is None:
        return list(default)
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _float_sequence(value: Any, default: Sequence[float]) -> list[float]:
    return [float(item) for item in _sequence(value, default)]


def _int_sequence(value: Any, default: Sequence[int]) -> list[int]:
    return [int(item) for item in _sequence(value, default)]


def _build_combos(
    config: Mapping[str, Any], args: argparse.Namespace
) -> tuple[list[RunCombo], CrystallizationConfig, Path, ExecutionConfig]:
    size_values = _int_sequence(pick(config, args.sizes, "sizes", [24]), [24])
    seed_values = _int_sequence(pick(config, args.seeds, "seeds", [12345, 54321]), [12345, 54321])
    boundary = str(pick(config, args.boundary, "boundary", "periodic"))
    out_dir = Path(pick(config, args.out, "out", "runs/crystallization_protocol"))
    execution_cfg = config.get("execution", {}) if isinstance(config.get("execution"), Mapping) else {}
    execution = ExecutionConfig(
        backend=str(pick(execution_cfg, args.backend, "backend", "numpy")).strip().lower() or "numpy",
        device=str(pick(execution_cfg, args.device, "device", "cpu")).strip() or "cpu",
    )

    initial_cfg = config.get("initial", {}) if isinstance(config.get("initial"), Mapping) else {}
    eq_values = _float_sequence(
        initial_cfg.get("equilibrium_energies") if args.equilibrium_energies is None else args.equilibrium_energies,
        [0.45, 0.5, 0.55],
    )
    noise_values = _float_sequence(initial_cfg.get("noise_levels") if args.noises is None else args.noises, [0.08])
    marker_radius = int(initial_cfg.get("marker_radius", 0 if args.marker_radius is None else args.marker_radius))
    marker_energy = (
        float(initial_cfg.get("marker_energy", args.marker_energy))
        if (initial_cfg.get("marker_energy", args.marker_energy) is not None)
        else None
    )
    marker_center_raw = initial_cfg.get("marker_center")
    marker_center = None
    if args.center is not None:
        marker_center = (int(args.center[0]), int(args.center[1]))
    elif isinstance(marker_center_raw, Sequence):
        marker_center = (int(marker_center_raw[0]), int(marker_center_raw[1]))

    dynamics_cfg = config.get("dynamics", {}) if isinstance(config.get("dynamics"), Mapping) else {}
    beta_values = _float_sequence(dynamics_cfg.get("beta") if args.beta is None else args.beta, [0.3, 1.0])
    gamma_values = _float_sequence(dynamics_cfg.get("gamma") if args.gamma is None else args.gamma, [0.1, 0.3])
    kappa_values = _float_sequence(dynamics_cfg.get("kappa") if args.kappa is None else args.kappa, [0.08, 0.15])
    alpha_values = _float_sequence(dynamics_cfg.get("alpha") if args.alpha is None else args.alpha, [0.2, 0.3])
    lambda_values = _float_sequence(dynamics_cfg.get("lambda_t") if args.lambda_t is None else args.lambda_t, [0.2, 0.5])
    activation_threshold = float(pick(dynamics_cfg, args.activation_threshold, "activation_threshold", 4.0))
    energy_bounds_raw = dynamics_cfg.get("energy_bounds", [0.0, 1.0])
    energy_bounds = None if args.no_energy_bounds else tuple(float(v) for v in energy_bounds_raw)

    crystal_cfg = config.get("crystallization", {}) if isinstance(config.get("crystallization"), Mapping) else {}
    crystallization = CrystallizationConfig(
        snapshot_steps=tuple(
            sorted(
                {
                    int(step)
                    for step in _int_sequence(
                        crystal_cfg.get("snapshot_steps") if args.snapshot_steps is None else args.snapshot_steps,
                        [150, 300, 600, 900, 1200],
                    )
                    if int(step) > 0
                }
            )
        ),
        window=int(pick(crystal_cfg, args.window, "window", 96)),
        min_steps=int(pick(crystal_cfg, args.min_steps, "min_steps", 256)),
        max_steps=int(
            pick(
                crystal_cfg,
                args.max_steps,
                "max_steps",
                max(
                    _int_sequence(
                        crystal_cfg.get("snapshot_steps") if args.snapshot_steps is None else args.snapshot_steps,
                        [150, 300, 600, 900, 1200],
                    )
                ),
            )
        ),
        delta_mean_threshold=float(
            pick(crystal_cfg, args.delta_mean_threshold, "delta_mean_threshold", 0.0012)
        ),
        energy_var_std_threshold=float(
            pick(crystal_cfg, args.energy_var_std_threshold, "energy_var_std_threshold", 0.00025)
        ),
        structure_std_threshold=float(
            pick(crystal_cfg, args.structure_std_threshold, "structure_std_threshold", 0.0008)
        ),
        min_structure_score=float(
            pick(crystal_cfg, args.min_structure_score, "min_structure_score", 0.015)
        ),
    )

    combos: list[RunCombo] = []
    for size, seed, eq, noise, beta, gamma, kappa, alpha, lambda_t in itertools.product(
        size_values,
        seed_values,
        eq_values,
        noise_values,
        beta_values,
        gamma_values,
        kappa_values,
        alpha_values,
        lambda_values,
    ):
        combos.append(
            RunCombo(
                seed=seed,
                size=size,
                boundary=boundary,
                initial=InitialStateConfig(
                    equilibrium_energy=eq,
                    noise=noise,
                    marker_radius=marker_radius,
                    marker_energy=marker_energy,
                    marker_center=marker_center,
                ),
                dynamics=DynamicsParameters(
                    equilibrium_energy=eq,
                    beta=beta,
                    gamma=gamma,
                    kappa=kappa,
                    alpha=alpha,
                    lambda_t=lambda_t,
                    activation_threshold=activation_threshold,
                    energy_bounds=energy_bounds,
                ),
            )
        )

    return combos, crystallization, out_dir, execution


def _circular_mask(lattice: Lattice, radius: int, center: tuple[int, int] | None) -> np.ndarray:
    cx, cy = center or (lattice.width // 2, lattice.height // 2)
    y, x = np.ogrid[: lattice.height, : lattice.width]
    return (x - cx) ** 2 + (y - cy) ** 2 <= radius**2


def _resolve_backend(execution: ExecutionConfig, lattice: Lattice) -> Backend:
    if execution.backend == "torch":
        try:
            backend = TorchBackend(device=execution.device)
        except RuntimeError:
            return NumpyBackend()
        if backend.supports(lattice):
            return backend
    return NumpyBackend()


def _build_initial_state(
    combo: RunCombo,
    *,
    execution: ExecutionConfig,
) -> tuple[DETMFieldState, np.ndarray | None, str, str]:
    lattice = Lattice(width=combo.size, height=combo.size, boundary=combo.boundary)
    rng = np.random.default_rng(combo.seed)
    energy_values = rng.normal(
        loc=combo.initial.equilibrium_energy,
        scale=combo.initial.noise,
        size=(lattice.height, lattice.width),
    ).astype(float, copy=False)
    if combo.dynamics.energy_bounds is not None:
        lo, hi = combo.dynamics.energy_bounds
        energy_values = np.clip(energy_values, lo, hi)

    marker_mask: np.ndarray | None = None
    if combo.initial.marker_radius > 0 and combo.initial.marker_energy is not None:
        marker_mask = _circular_mask(lattice, combo.initial.marker_radius, combo.initial.marker_center)
        energy_values[marker_mask] = combo.initial.marker_energy

    backend = _resolve_backend(execution, lattice)
    entropy_values = NumpyBackend._compute_entropy(energy_values, combo.dynamics, boundary=lattice.boundary)

    if isinstance(backend, TorchBackend):
        torch = backend._torch
        device = torch.device(backend.config.device)
        dtype = torch.float64
        state = DETMFieldState(
            lattice=lattice,
            energy=torch.tensor(energy_values, device=device, dtype=dtype),
            entropy=torch.tensor(entropy_values, device=device, dtype=dtype),
            internal_time=torch.zeros((lattice.height, lattice.width), device=device, dtype=dtype),
            shape=(lattice.height, lattice.width),
        )
    else:
        state = DETMFieldState(
            lattice=lattice,
            energy=energy_values.copy(),
            entropy=entropy_values.copy(),
            internal_time=np.zeros((lattice.height, lattice.width), dtype=float),
            shape=(lattice.height, lattice.width),
        )
    return state, marker_mask, backend.config.name, backend.config.device


def _field_array(field: Any) -> np.ndarray:
    try:
        import torch  # type: ignore
    except ModuleNotFoundError:
        torch = None
    if torch is not None and isinstance(field, torch.Tensor):
        return field.detach().to("cpu").numpy()
    return np.asarray(field, dtype=float)


def _mean_abs_delta(curr: np.ndarray, prev: np.ndarray) -> float:
    return float(np.mean(np.abs(curr - prev)))


def _structure_score(energy: np.ndarray) -> float:
    grad_x = 0.5 * (np.roll(energy, -1, axis=1) - np.roll(energy, 1, axis=1))
    grad_y = 0.5 * (np.roll(energy, -1, axis=0) - np.roll(energy, 1, axis=0))
    return float(np.mean(np.sqrt(grad_x * grad_x + grad_y * grad_y)))


def _state_signature(state: DETMFieldState) -> dict[str, float]:
    energy = _field_array(state.energy)
    entropy = _field_array(state.entropy)
    internal_time = _field_array(state.internal_time)
    attractors = detect_attractors(energy, threshold=0.9, top_k=8)
    return {
        "energy_mean": float(np.mean(energy)),
        "energy_min": float(np.min(energy)),
        "energy_max": float(np.max(energy)),
        "energy_var": float(np.var(energy)),
        "entropy_mean": float(np.mean(entropy)),
        "internal_time_mean": float(np.mean(internal_time)),
        "structure_score": _structure_score(energy),
        "attractor_count": float(len(attractors)),
        "max_attractor_strength": float(attractors[0].strength if attractors else 0.0),
    }


def _crystallized(
    deltas: deque[float],
    variances: deque[float],
    structures: deque[float],
    cfg: CrystallizationConfig,
    step_idx: int,
) -> bool:
    if step_idx < cfg.min_steps:
        return False
    if len(deltas) < cfg.window or len(variances) < cfg.window or len(structures) < cfg.window:
        return False
    return (
        float(np.mean(deltas)) <= cfg.delta_mean_threshold
        and float(np.std(variances)) <= cfg.energy_var_std_threshold
        and float(np.std(structures)) <= cfg.structure_std_threshold
        and float(np.mean(structures)) >= cfg.min_structure_score
    )


def _run_id(combo: RunCombo) -> str:
    return (
        f"size_{combo.size:03d}"
        f"__seed_{combo.seed}"
        f"__eq_{combo.initial.equilibrium_energy:.3f}"
        f"__noise_{combo.initial.noise:.3f}"
        f"__b_{combo.dynamics.beta:.3f}"
        f"__g_{combo.dynamics.gamma:.3f}"
        f"__k_{combo.dynamics.kappa:.3f}"
        f"__a_{combo.dynamics.alpha:.3f}"
        f"__t_{combo.dynamics.lambda_t:.3f}"
    )


def _write_metrics_csv(path: Path, rows: Sequence[Mapping[str, float]]) -> None:
    fieldnames = [
        "step",
        "energy_mean",
        "energy_min",
        "energy_max",
        "energy_var",
        "entropy_mean",
        "internal_time_mean",
        "structure_score",
        "attractor_count",
        "max_attractor_strength",
        "mean_abs_delta_energy",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_state_npz(
    path: Path,
    *,
    initial_energy: np.ndarray,
    crystallization_energy: np.ndarray,
    final_energy: np.ndarray,
    crystallization_tick: int | None,
    marker_mask: np.ndarray | None,
    checkpoint_energies: Mapping[int, np.ndarray],
) -> None:
    kwargs: dict[str, Any] = {
        "initial_energy": initial_energy,
        "crystallization_energy": crystallization_energy,
        "final_energy": final_energy,
        "crystallization_tick": -1 if crystallization_tick is None else crystallization_tick,
    }
    for step_idx, array in checkpoint_energies.items():
        kwargs[f"energy_step_{int(step_idx):04d}"] = array
    if marker_mask is not None:
        kwargs["marker_mask"] = marker_mask.astype(np.int8)
    np.savez(path, **kwargs)


def _plot_quicklook(
    path: Path,
    *,
    initial_energy: np.ndarray,
    checkpoint_energies: Mapping[int, np.ndarray],
    equilibrium_energy: float,
    energy_bounds: tuple[float, float] | None,
    title: str,
) -> None:
    ordered_steps = sorted(int(step_idx) for step_idx in checkpoint_energies)
    arrays = [initial_energy] + [checkpoint_energies[step_idx] for step_idx in ordered_steps]
    labels = ["initial"] + [f"step {step_idx}" for step_idx in ordered_steps]

    panel_count = len(arrays)
    cols = min(3, panel_count)
    rows = int(np.ceil(panel_count / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(4.0 * cols, 3.5 * rows), constrained_layout=True)
    axes_arr = np.atleast_1d(axes).reshape(rows, cols)

    for ax, label, data in zip(axes_arr.flatten(), labels, arrays):
        panel_mean = float(np.mean(data))
        residual = data - panel_mean
        q_low, q_high = np.percentile(residual, [2.0, 98.0])
        abs_max = max(abs(float(q_low)), abs(float(q_high)))
        min_half_span = 1e-4
        half_span = max(abs_max, min_half_span)
        norm = colors.TwoSlopeNorm(vmin=-half_span, vcenter=0.0, vmax=half_span)
        im = ax.imshow(residual, origin="lower", cmap="coolwarm", norm=norm)
        ax.set_title(label)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.text(
            0.02,
            0.02,
            f"mu={panel_mean:.6f}\nDelta±{half_span:.6f}",
            transform=ax.transAxes,
            ha="left",
            va="bottom",
            fontsize=8,
            color="white",
            bbox={"facecolor": "black", "alpha": 0.35, "pad": 1.5, "edgecolor": "none"},
        )
    for ax in axes_arr.flatten()[panel_count:]:
        ax.axis("off")
    cbar = fig.colorbar(im, ax=axes_arr.flatten()[:panel_count], shrink=0.85, pad=0.02)
    cbar.set_label("E - <E>_panel")
    fig.suptitle(title)
    fig.savefig(path, dpi=220)
    plt.close(fig)


def run_crystallization_protocol(
    combos: Iterable[RunCombo],
    *,
    crystallization: CrystallizationConfig,
    out_dir: Path,
    execution: ExecutionConfig,
) -> list[dict[str, Any]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    summaries: list[dict[str, Any]] = []

    for combo in combos:
        state, marker_mask, backend_name, resolved_device = _build_initial_state(combo, execution=execution)
        backend = _resolve_backend(
            ExecutionConfig(backend=backend_name, device=resolved_device),
            state.lattice,
        )
        initial_energy = _field_array(state.energy)
        crystallization_energy = initial_energy.copy()
        final_energy = initial_energy.copy()
        crystal_tick: int | None = None
        crystal_state = state
        checkpoint_energies: dict[int, np.ndarray] = {}

        deltas: deque[float] = deque(maxlen=crystallization.window)
        variances: deque[float] = deque(maxlen=crystallization.window)
        structures: deque[float] = deque(maxlen=crystallization.window)
        rows: list[dict[str, float]] = []
        prev_energy = initial_energy

        for step_idx in range(1, crystallization.max_steps + 1):
            state = backend.step(state, combo.dynamics, 1)
            curr_energy = _field_array(state.energy)
            metrics = _state_signature(state)
            delta_value = _mean_abs_delta(curr_energy, prev_energy)
            deltas.append(delta_value)
            variances.append(metrics["energy_var"])
            structures.append(metrics["structure_score"])

            row = {"step": float(step_idx), **metrics, "mean_abs_delta_energy": delta_value}
            rows.append(row)

            if crystal_tick is None and _crystallized(deltas, variances, structures, crystallization, step_idx):
                crystal_tick = step_idx
                crystallization_energy = curr_energy.copy()
                crystal_state = state

            if step_idx in crystallization.snapshot_steps:
                checkpoint_energies[step_idx] = curr_energy.copy()

            prev_energy = curr_energy

        final_energy = prev_energy.copy()
        final_state = state
        if crystal_tick is None:
            crystallization_energy = final_energy.copy()
            crystal_state = final_state
        if crystallization.max_steps not in checkpoint_energies:
            checkpoint_energies[crystallization.max_steps] = final_energy.copy()

        run_id = _run_id(combo)
        run_dir = out_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        metrics_path = run_dir / "metrics.csv"
        _write_metrics_csv(metrics_path, rows)
        _write_state_npz(
            run_dir / "state_snapshots.npz",
            initial_energy=initial_energy,
            crystallization_energy=crystallization_energy,
            final_energy=final_energy,
            crystallization_tick=crystal_tick,
            marker_mask=marker_mask,
            checkpoint_energies=checkpoint_energies,
        )
        _plot_quicklook(
            run_dir / "quicklook.png",
            initial_energy=initial_energy,
            checkpoint_energies=checkpoint_energies,
            equilibrium_energy=combo.initial.equilibrium_energy,
            energy_bounds=combo.dynamics.energy_bounds,
            title=run_id,
        )

        crystal_metrics = _state_signature(crystal_state)
        final_metrics = _state_signature(final_state)
        summary: dict[str, Any] = {
            "run_id": run_id,
            "seed": combo.seed,
            "size": combo.size,
            "boundary": combo.boundary,
            "initial_equilibrium_energy": combo.initial.equilibrium_energy,
            "initial_noise": combo.initial.noise,
            "marker_radius": combo.initial.marker_radius,
            "marker_energy": combo.initial.marker_energy,
            "beta": combo.dynamics.beta,
            "gamma": combo.dynamics.gamma,
            "kappa": combo.dynamics.kappa,
            "alpha": combo.dynamics.alpha,
            "lambda_t": combo.dynamics.lambda_t,
            "activation_threshold": combo.dynamics.activation_threshold,
            "energy_bounds": combo.dynamics.energy_bounds,
            "execution_backend_requested": execution.backend,
            "execution_device_requested": execution.device,
            "execution_backend_resolved": backend_name,
            "execution_device_resolved": resolved_device,
            "crystallization_window": crystallization.window,
            "snapshot_steps": list(crystallization.snapshot_steps),
            "crystallization_tick": crystal_tick,
            "crystallized": crystal_tick is not None,
            "final_step": crystallization.max_steps,
            "crystallization_energy_var": crystal_metrics["energy_var"],
            "crystallization_structure_score": crystal_metrics["structure_score"],
            "crystallization_attractor_count": int(crystal_metrics["attractor_count"]),
            "final_energy_var": final_metrics["energy_var"],
            "final_structure_score": final_metrics["structure_score"],
            "final_internal_time_mean": final_metrics["internal_time_mean"],
            "final_attractor_count": int(final_metrics["attractor_count"]),
            "final_max_attractor_strength": final_metrics["max_attractor_strength"],
            "metrics_csv": str(metrics_path.resolve()),
            "state_npz": str((run_dir / "state_snapshots.npz").resolve()),
            "quicklook_png": str((run_dir / "quicklook.png").resolve()),
        }
        (run_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        summaries.append(summary)

    return summaries


def _write_batch_summary(out_dir: Path, summaries: Sequence[Mapping[str, Any]]) -> None:
    summary_csv = out_dir / "summary.csv"
    fieldnames = [
        "run_id",
        "seed",
        "size",
        "boundary",
        "initial_equilibrium_energy",
        "initial_noise",
        "marker_radius",
        "marker_energy",
        "beta",
        "gamma",
        "kappa",
        "alpha",
        "lambda_t",
        "activation_threshold",
        "energy_bounds",
        "execution_backend_requested",
        "execution_device_requested",
        "execution_backend_resolved",
        "execution_device_resolved",
        "crystallization_window",
        "snapshot_steps",
        "crystallized",
        "crystallization_tick",
        "final_step",
        "crystallization_energy_var",
        "crystallization_structure_score",
        "crystallization_attractor_count",
        "final_energy_var",
        "final_structure_score",
        "final_internal_time_mean",
        "final_attractor_count",
        "final_max_attractor_strength",
        "metrics_csv",
        "state_npz",
        "quicklook_png",
    ]
    with summary_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summaries)
    (out_dir / "catalog.json").write_text(
        json.dumps({"runs": list(summaries)}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", type=Path, default=None, help="JSON/YAML config file")
    ap.add_argument("--sizes", type=int, nargs="*", default=None)
    ap.add_argument("--seeds", type=int, nargs="*", default=None)
    ap.add_argument("--boundary", type=str, default=None)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--backend", type=str, default=None, choices=("numpy", "torch"))
    ap.add_argument("--device", type=str, default=None)
    ap.add_argument("--equilibrium-energies", type=float, nargs="*", default=None)
    ap.add_argument("--noises", type=float, nargs="*", default=None)
    ap.add_argument("--marker-radius", type=int, default=None)
    ap.add_argument("--marker-energy", type=float, default=None)
    ap.add_argument("--center", type=int, nargs=2, metavar=("X", "Y"), default=None)
    ap.add_argument("--beta", type=float, nargs="*", default=None)
    ap.add_argument("--gamma", type=float, nargs="*", default=None)
    ap.add_argument("--kappa", type=float, nargs="*", default=None)
    ap.add_argument("--alpha", type=float, nargs="*", default=None)
    ap.add_argument("--lambda-t", type=float, nargs="*", default=None, dest="lambda_t")
    ap.add_argument("--activation-threshold", type=float, default=None)
    ap.add_argument("--no-energy-bounds", action="store_true")
    ap.add_argument("--window", type=int, default=None)
    ap.add_argument("--min-steps", type=int, default=None)
    ap.add_argument("--max-steps", type=int, default=None)
    ap.add_argument("--snapshot-steps", type=int, nargs="*", default=None)
    ap.add_argument("--delta-mean-threshold", type=float, default=None)
    ap.add_argument("--energy-var-std-threshold", type=float, default=None)
    ap.add_argument("--structure-std-threshold", type=float, default=None)
    ap.add_argument("--min-structure-score", type=float, default=None)

    args = ap.parse_args()
    config = load_structured_config(args.config)
    combos, crystallization, out_dir, execution = _build_combos(config, args)
    summaries = run_crystallization_protocol(
        combos,
        crystallization=crystallization,
        out_dir=out_dir,
        execution=execution,
    )
    _write_batch_summary(out_dir, summaries)
    print(f"[OK] {len(summaries)} long-run sweep(s) completed. Catalog: {(out_dir / 'catalog.json').resolve()}")


if __name__ == "__main__":
    main()
