"""Minimal demonstration of the new visualisation helpers.

The script runs a short deterministic evolution and emits a handful of figures:
- energy/entropy/internal time heatmaps,
- invariant time series (mean/min/max),
- a radial profile matching the legacy ``analyze_fields.py`` behaviour.

All outputs are written next to the script by default.  The Plotly HTML heatmap
is saved only when the optional dependency is available.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from core.entropy import DynamicsParameters, compute_entropy, evolve
from core.fields import FieldState, Lattice, ScalarField
from core.invariants import collect_series
from visualization import plot_field_state, plot_invariants, plot_radial, plotly_scalar_field


def build_initial_state(size: int, seed: int | None, params: DynamicsParameters) -> FieldState:
    lattice = Lattice(width=size, height=size, boundary="periodic")
    rng = np.random.default_rng(seed)
    energy = ScalarField(
        lattice=lattice,
        values=np.clip(
            rng.normal(loc=params.equilibrium_energy, scale=0.12, size=lattice.size),
            0.0,
            1.0,
        ).tolist(),
    )
    entropy = compute_entropy(energy, params)
    internal_time = ScalarField.constant(lattice, value=0.0)
    return FieldState(energy=energy, entropy=entropy, internal_time=internal_time)


def save_plt(plot, path: Path) -> None:
    plot.figure.savefig(path, dpi=160)
    plt.close(plot.figure)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=18, help="lattice width/height")
    ap.add_argument("--steps", type=int, default=40, help="evolution steps to run")
    ap.add_argument("--seed", type=int, default=1, help="random seed for initial field")
    ap.add_argument("--out", type=Path, default=Path("."), help="output directory")
    args = ap.parse_args()

    params = DynamicsParameters(equilibrium_energy=0.55, kappa=0.08, alpha=0.9)
    state0 = build_initial_state(args.size, args.seed, params)
    history = evolve(state0, params, steps=args.steps)

    args.out.mkdir(parents=True, exist_ok=True)

    save_plt(plot_field_state(history[-1]), args.out / "fields.png")

    series = collect_series(history)
    save_plt(plot_invariants(series), args.out / "invariants.png")

    save_plt(plot_radial(history[-1].energy), args.out / "radial_energy.png")

    plotly_fig = plotly_scalar_field(history[-1].energy, title="Energy field (interactive)")
    if plotly_fig is not None:
        plotly_fig.write_html(args.out / "energy_heatmap.html")

    print(f"Wrote figures to {args.out.resolve()}")


if __name__ == "__main__":
    main()
