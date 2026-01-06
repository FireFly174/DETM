"""Scaling protocol that sweeps lattice sizes using the new API.

The goal mirrors the legacy time-series bundling scripts: run controlled
experiments, extract reproducible metrics and keep output files compact and
self-describing.  For each (size, seed) pair the script records:

- invariant time series (mean/min/max/variance of energy, plus entropy and
  internal time means),
- dominant frequency of the energy mean trajectory,
- final field snapshot saved as ``.npz`` for downstream analysis.

Configuration can be supplied via JSON/YAML with CLI overrides.
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
class SweepConfig:
    sizes: Sequence[int]
    seeds: Sequence[int]
    steps: int


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


def _build_initial_state(
    size: int,
    boundary: str,
    seed: int,
    params: DynamicsParameters,
    noise: float,
) -> FieldState:
    lattice = Lattice(width=size, height=size, boundary=boundary)
    rng = np.random.default_rng(seed)
    energy_values = np.clip(
        rng.normal(loc=params.equilibrium_energy, scale=noise, size=lattice.size),
        0.0,
        1.0,
    )
    energy = ScalarField(lattice, energy_values.tolist())
    entropy = compute_entropy(energy, params)
    internal_time = ScalarField.constant(lattice, value=0.0)
    return FieldState(energy=energy, entropy=entropy, internal_time=internal_time)


def _dominant_frequency(signal: Sequence[float]) -> tuple[float, float]:
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


def _write_series_csv(path: Path, series: Mapping[str, Sequence[float]]) -> None:
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
                ]
            )


def _write_final_state(path: Path, state: FieldState) -> None:
    lattice = state.lattice
    np.savez(
        path,
        energy=np.asarray(state.energy.values, dtype=float).reshape(lattice.height, lattice.width),
        entropy=np.asarray(state.entropy.values, dtype=float).reshape(lattice.height, lattice.width),
        internal_time=np.asarray(state.internal_time.values, dtype=float).reshape(lattice.height, lattice.width),
    )


def run_scaling_sweep(
    sizes: Iterable[int],
    seeds: Iterable[int],
    steps: int,
    boundary: str,
    noise: float,
    params: DynamicsParameters,
    out_dir: Path,
) -> list[dict[str, object]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, object]] = []

    for size in sizes:
        for seed in seeds:
            state0 = _build_initial_state(size, boundary, seed, params, noise)
            history = evolve(state0, params, steps=steps)
            series = collect_series(history)
            freq, power = _dominant_frequency(series["energy_mean"])
            final_snapshot = describe_state(history[-1])

            run_dir = out_dir / f"size_{size:03d}" / f"seed_{seed:04d}"
            run_dir.mkdir(parents=True, exist_ok=True)

            _write_series_csv(run_dir / "metrics.csv", series)
            _write_final_state(run_dir / "final_state.npz", history[-1])

            summary = {
                "size": size,
                "seed": seed,
                "steps": steps,
                "boundary": boundary,
                "noise": noise,
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
                "dominant_frequency": freq,
                "dominant_power": power,
                "metrics_csv": str((run_dir / "metrics.csv").resolve()),
                "state_npz": str((run_dir / "final_state.npz").resolve()),
            }
            (run_dir / "summary.json").write_text(
                json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            results.append(summary)

    return results


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", type=Path, default=None, help="JSON/YAML config file")
    ap.add_argument("--sizes", type=int, nargs="*", default=None, help="Lattice sizes to sweep")
    ap.add_argument("--seeds", type=int, nargs="*", default=None, help="Seeds to run")
    ap.add_argument("--steps", type=int, default=None, help="Number of steps to run")
    ap.add_argument("--boundary", type=str, default=None, help="Boundary condition")
    ap.add_argument("--noise", type=float, default=None, help="Std of initial energy noise")
    ap.add_argument("--out", type=Path, default=None, help="Output directory")

    # Dynamics overrides
    ap.add_argument("--equilibrium-energy", type=float, default=None)
    ap.add_argument("--beta", type=float, default=None)
    ap.add_argument("--gamma", type=float, default=None)
    ap.add_argument("--kappa", type=float, default=None)
    ap.add_argument("--alpha", type=float, default=None)
    ap.add_argument("--lambda-t", type=float, default=None, dest="lambda_t")
    ap.add_argument("--activation-threshold", type=float, default=None)
    ap.add_argument("--energy-min", type=float, default=None, help="Lower clamp; ignored when --no-energy-bounds set")
    ap.add_argument("--energy-max", type=float, default=None, help="Upper clamp; ignored when --no-energy-bounds set")
    ap.add_argument("--no-energy-bounds", action="store_true", help="Disable clamping of the energy field")

    args = ap.parse_args()

    config = load_structured_config(args.config)
    params = _build_dynamics(config, args)

    sizes = pick(config, args.sizes, "sizes", [12, 18, 24])
    seeds = pick(config, args.seeds, "seeds", [1, 2])
    steps = int(pick(config, args.steps, "steps", 160))
    boundary = str(pick(config, args.boundary, "boundary", "periodic"))
    noise = float(pick(config, args.noise, "noise", 0.08))
    out_dir = Path(pick(config, args.out, "out", "runs/scaling_protocol"))

    if isinstance(sizes, int):
        sizes = [sizes]
    if isinstance(seeds, int):
        seeds = [seeds]

    results = run_scaling_sweep(
        sizes=sizes,
        seeds=seeds,
        steps=steps,
        boundary=boundary,
        noise=noise,
        params=params,
        out_dir=out_dir,
    )

    summary_csv = out_dir / "summary.csv"
    with summary_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "size",
                "seed",
                "steps",
                "boundary",
                "noise",
                "equilibrium_energy",
                "kappa",
                "alpha",
                "beta",
                "gamma",
                "lambda_t",
                "activation_threshold",
                "energy_bounds",
                "final_energy_mean",
                "final_energy_min",
                "final_energy_max",
                "final_energy_var",
                "final_entropy_mean",
                "final_internal_time_mean",
                "dominant_frequency",
                "dominant_power",
                "metrics_csv",
                "state_npz",
            ],
        )
        writer.writeheader()
        writer.writerows(results)

    catalog_path = out_dir / "catalog.json"
    catalog_path.write_text(json.dumps({"runs": results}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] sweep complete: {len(results)} runs. Summary: {summary_csv.resolve()}")


if __name__ == "__main__":
    main()
