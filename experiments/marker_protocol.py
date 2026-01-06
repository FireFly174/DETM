"""Marker stability protocol built on the new ``core.entropy`` API.

The script plants a high-energy marker in the centre of the lattice, runs a
deterministic evolution and records metrics inspired by the legacy
``analyze_grid_timeseries.py`` pipeline:
- global invariants (mean/min/max/variance of energy plus entropy and
  internal time averages),
- mean energy inside the marker footprint versus the background,
- dominant frequency of the energy mean time series.

Configuration can be provided via JSON or YAML and overridden from the CLI.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import numpy as np

from detm.core.entropy import DynamicsParameters, compute_entropy, evolve
from detm.core.fields import FieldState, Lattice, ScalarField
from detm.core.invariants import collect_series, describe_state
from experiments.configuration import load_structured_config, pick


@dataclass(frozen=True)
class MarkerConfig:
    radius: int = 2
    energy: float = 0.92
    center: tuple[int, int] | None = None


def _build_dynamics(config: Mapping[str, object], args: argparse.Namespace) -> DynamicsParameters:
    defaults = DynamicsParameters()
    cfg = config.get("dynamics", {}) if isinstance(config.get("dynamics"), Mapping) else {}

    energy_bounds = cfg.get("energy_bounds", defaults.energy_bounds)
    if getattr(args, "no_energy_bounds", False):
        energy_bounds = None
    elif args.energy_min is not None or args.energy_max is not None:
        lo = pick(cfg, args.energy_min, "energy_min", defaults.energy_bounds[0] if defaults.energy_bounds else 0.0)
        hi = pick(cfg, args.energy_max, "energy_max", defaults.energy_bounds[1] if defaults.energy_bounds else 1.0)
        energy_bounds = (float(lo), float(hi))
    elif energy_bounds is not None:
        energy_bounds = tuple(energy_bounds)  # type: ignore[arg-type]

    return DynamicsParameters(
        equilibrium_energy=pick(cfg, args.equilibrium_energy, "equilibrium_energy", defaults.equilibrium_energy),
        beta=pick(cfg, args.beta, "beta", defaults.beta),
        gamma=pick(cfg, args.gamma, "gamma", defaults.gamma),
        kappa=pick(cfg, args.kappa, "kappa", defaults.kappa),
        alpha=pick(cfg, args.alpha, "alpha", defaults.alpha),
        lambda_t=pick(cfg, args.lambda_t, "lambda_t", defaults.lambda_t),
        activation_threshold=pick(
            cfg, args.activation_threshold, "activation_threshold", defaults.activation_threshold
        ),
        energy_bounds=energy_bounds,  # type: ignore[arg-type]
    )


def _build_marker(config: Mapping[str, object], args: argparse.Namespace) -> MarkerConfig:
    cfg = config.get("marker", {}) if isinstance(config.get("marker"), Mapping) else {}
    center = cfg.get("center")
    if args.center is not None:
        center = tuple(args.center)  # type: ignore[assignment]
    elif isinstance(center, Sequence):
        center = (int(center[0]), int(center[1]))  # type: ignore[assignment]
    else:
        center = None
    return MarkerConfig(
        radius=int(pick(cfg, args.marker_radius, "radius", 2)),
        energy=float(pick(cfg, args.marker_energy, "energy", 0.92)),
        center=center,
    )


def _circular_mask(lattice: Lattice, radius: int, center: tuple[int, int] | None) -> np.ndarray:
    cx, cy = center or (lattice.width // 2, lattice.height // 2)
    y, x = np.ogrid[: lattice.height, : lattice.width]
    return (x - cx) ** 2 + (y - cy) ** 2 <= radius**2


def _build_initial_state(
    size: int,
    boundary: str,
    seed: int,
    params: DynamicsParameters,
    noise: float,
    marker: MarkerConfig,
) -> tuple[FieldState, np.ndarray]:
    lattice = Lattice(width=size, height=size, boundary=boundary)
    rng = np.random.default_rng(seed)
    energy_values = np.clip(
        rng.normal(loc=params.equilibrium_energy, scale=noise, size=lattice.size),
        0.0,
        1.0,
    ).reshape(lattice.height, lattice.width)

    mask = _circular_mask(lattice, marker.radius, marker.center)
    energy_values[mask] = marker.energy

    energy = ScalarField(lattice, energy_values.reshape(-1).tolist())
    entropy = compute_entropy(energy, params)
    internal_time = ScalarField.constant(lattice, value=0.0)
    return FieldState(energy=energy, entropy=entropy, internal_time=internal_time), mask


def _dominant_frequency(signal: Sequence[float]) -> tuple[float, float]:
    """Return (frequency, power) of the dominant non-DC component."""

    arr = np.asarray(signal, dtype=float)
    if arr.size < 2:
        return 0.0, 0.0
    arr = arr - float(arr.mean())
    spectrum = np.fft.rfft(arr)
    power = spectrum.real**2 + spectrum.imag**2
    if power.shape[0] <= 1:
        return 0.0, 0.0
    idx = 1 + int(np.argmax(power[1:]))
    freqs = np.fft.rfftfreq(arr.size, d=1.0)
    return float(freqs[idx]), float(power[idx])


def _collect_marker_series(history: Sequence[FieldState], mask: np.ndarray) -> tuple[list[float], list[float]]:
    marker_mean: list[float] = []
    background_mean: list[float] = []
    invert_mask = ~mask

    for state in history:
        arr = np.asarray(state.energy.values, dtype=float).reshape(mask.shape)
        marker_mean.append(float(arr[mask].mean()))
        background_mean.append(float(arr[invert_mask].mean()))
    return marker_mean, background_mean


def _write_series_csv(
    path: Path,
    series: Mapping[str, Sequence[float]],
    marker_mean: Sequence[float],
    background_mean: Sequence[float],
) -> None:
    steps = len(next(iter(series.values()), []))
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "step",
                "energy_mean",
                "energy_min",
                "energy_max",
                "energy_var",
                "entropy_mean",
                "internal_time_mean",
                "marker_energy_mean",
                "background_energy_mean",
            ]
        )
        for i in range(steps):
            writer.writerow(
                [
                    i,
                    series["energy_mean"][i],
                    series["energy_min"][i],
                    series["energy_max"][i],
                    series["energy_var"][i],
                    series["entropy_mean"][i],
                    series["internal_time_mean"][i],
                    marker_mean[i],
                    background_mean[i],
                ]
            )


def _write_final_state(path: Path, state: FieldState, mask: np.ndarray) -> None:
    lattice = state.lattice
    np.savez(
        path,
        energy=np.asarray(state.energy.values, dtype=float).reshape(lattice.height, lattice.width),
        entropy=np.asarray(state.entropy.values, dtype=float).reshape(lattice.height, lattice.width),
        internal_time=np.asarray(state.internal_time.values, dtype=float).reshape(lattice.height, lattice.width),
        marker_mask=mask.astype(np.int8),
    )


def _save_summary(path: Path, summary: Mapping[str, object]) -> None:
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")


def run_marker_protocol(
    seeds: Iterable[int],
    size: int,
    steps: int,
    boundary: str,
    noise: float,
    params: DynamicsParameters,
    marker: MarkerConfig,
    out_dir: Path,
) -> list[dict[str, object]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, object]] = []

    for seed in seeds:
        state0, mask = _build_initial_state(size, boundary, seed, params, noise, marker)
        history = evolve(state0, params, steps=steps)

        series = collect_series(history)
        marker_mean, background_mean = _collect_marker_series(history, mask)
        freq, power = _dominant_frequency(series["energy_mean"])
        final_snapshot = describe_state(history[-1])

        run_dir = out_dir / f"seed_{seed:04d}"
        run_dir.mkdir(parents=True, exist_ok=True)

        _write_series_csv(run_dir / "metrics.csv", series, marker_mean, background_mean)
        _write_final_state(run_dir / "final_state.npz", history[-1], mask)

        summary = {
            "seed": seed,
            "size": size,
            "steps": steps,
            "boundary": boundary,
            "noise": noise,
            "marker_radius": marker.radius,
            "marker_energy": marker.energy,
            "marker_center": marker.center or "center",
            "equilibrium_energy": params.equilibrium_energy,
            "kappa": params.kappa,
            "alpha": params.alpha,
            "beta": params.beta,
            "gamma": params.gamma,
            "lambda_t": params.lambda_t,
            "activation_threshold": params.activation_threshold,
            "energy_bounds": params.energy_bounds,
            "final_energy_mean": final_snapshot.energy.mean,
            "final_energy_min": final_snapshot.energy.minimum,
            "final_energy_max": final_snapshot.energy.maximum,
            "final_energy_var": final_snapshot.energy.variance,
            "final_entropy_mean": final_snapshot.entropy.mean,
            "final_internal_time_mean": final_snapshot.internal_time.mean,
            "marker_energy_mean_last": marker_mean[-1],
            "background_energy_mean_last": background_mean[-1],
            "dominant_frequency": freq,
            "dominant_power": power,
            "metrics_csv": str((run_dir / "metrics.csv").resolve()),
            "state_npz": str((run_dir / "final_state.npz").resolve()),
        }
        _save_summary(run_dir / "summary.json", summary)
        results.append(summary)

    return results


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", type=Path, default=None, help="JSON/YAML config file")
    ap.add_argument("--size", type=int, default=None, help="Lattice width/height")
    ap.add_argument("--steps", type=int, default=None, help="Steps to run")
    ap.add_argument("--seeds", type=int, nargs="*", default=None, help="Seeds to run (space-separated)")
    ap.add_argument("--boundary", type=str, default=None, help="Boundary condition: periodic or open")
    ap.add_argument("--noise", type=float, default=None, help="Std of initial energy noise")
    ap.add_argument("--out", type=Path, default=None, help="Output directory")

    # Dynamics overrides
    ap.add_argument("--equilibrium-energy", type=float, default=None, help="DynamicsParameters.equilibrium_energy")
    ap.add_argument("--beta", type=float, default=None)
    ap.add_argument("--gamma", type=float, default=None)
    ap.add_argument("--kappa", type=float, default=None)
    ap.add_argument("--alpha", type=float, default=None)
    ap.add_argument("--lambda-t", type=float, default=None, dest="lambda_t")
    ap.add_argument("--activation-threshold", type=float, default=None)
    ap.add_argument("--energy-min", type=float, default=None, help="Lower clamp; ignored when --no-energy-bounds set")
    ap.add_argument("--energy-max", type=float, default=None, help="Upper clamp; ignored when --no-energy-bounds set")
    ap.add_argument("--no-energy-bounds", action="store_true", help="Disable clamping of the energy field")

    # Marker overrides
    ap.add_argument("--marker-radius", type=int, default=None, help="Marker radius in cells")
    ap.add_argument("--marker-energy", type=float, default=None, help="Energy value to plant inside the marker")
    ap.add_argument("--center", type=int, nargs=2, metavar=("X", "Y"), default=None, help="Marker centre (x y)")

    args = ap.parse_args()

    config = load_structured_config(args.config)
    params = _build_dynamics(config, args)
    marker = _build_marker(config, args)

    size = int(pick(config, args.size, "size", 24))
    steps = int(pick(config, args.steps, "steps", 180))
    seeds = pick(config, args.seeds, "seeds", [1])
    if isinstance(seeds, int):
        seeds = [seeds]
    boundary = str(pick(config, args.boundary, "boundary", "periodic"))
    noise = float(pick(config, args.noise, "noise", 0.08))
    out_dir = Path(pick(config, args.out, "out", "runs/marker_protocol"))

    results = run_marker_protocol(
        seeds=seeds,
        size=size,
        steps=steps,
        boundary=boundary,
        noise=noise,
        params=params,
        marker=marker,
        out_dir=out_dir,
    )

    catalog = {"runs": results}
    catalog_path = out_dir / "catalog.json"
    catalog_path.write_text(json.dumps(catalog, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] {len(results)} run(s) completed. Catalog: {catalog_path.resolve()}")


if __name__ == "__main__":
    main()
