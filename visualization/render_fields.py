"""Thin matplotlib/plotly rendering helpers for the new ``FieldState`` core."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import matplotlib.pyplot as plt
import numpy as np

from detm.core.fields import FieldState, ScalarField
from detm.core.invariants import collect_series, radial_profile


def _to_array(field: ScalarField) -> np.ndarray:
    """Return a ``(height, width)`` numpy view of the field values."""

    lattice = field.lattice
    return np.asarray(field.values, dtype=float).reshape(lattice.height, lattice.width)


@dataclass(frozen=True)
class FieldPlot:
    """Bundle returned by the plotting helpers."""

    figure: plt.Figure
    axes: Sequence[plt.Axes]


def plot_scalar_field(
    field: ScalarField,
    *,
    title: str | None = None,
    cmap: str = "magma",
    colorbar: bool = True,
) -> FieldPlot:
    """Render a single scalar field heatmap with matplotlib."""

    fig, ax = plt.subplots(figsize=(6, 5))
    arr = _to_array(field)
    im = ax.imshow(arr, origin="lower", cmap=cmap, interpolation="nearest")
    if colorbar:
        fig.colorbar(im, ax=ax, shrink=0.85)
    ax.set_title(title or "Scalar field")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    fig.tight_layout()
    return FieldPlot(figure=fig, axes=[ax])


def plot_field_state(state: FieldState, *, cmap: str = "magma") -> FieldPlot:
    """Show energy, entropy and internal time side-by-side."""

    state.ensure_alignment()
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    fields = [
        (state.energy, "Energy"),
        (state.entropy, "Entropy"),
        (state.internal_time, "Internal time"),
    ]
    for ax, (field, title) in zip(axes, fields):
        arr = _to_array(field)
        im = ax.imshow(arr, origin="lower", cmap=cmap, interpolation="nearest")
        fig.colorbar(im, ax=ax, shrink=0.8)
        ax.set_title(title)
        ax.set_xlabel("x")
        ax.set_ylabel("y")

    fig.tight_layout()
    return FieldPlot(figure=fig, axes=axes)


def plot_invariants(series: Mapping[str, Sequence[float]]) -> FieldPlot:
    """Plot invariant trajectories such as mean energy across time."""

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    t = np.arange(len(next(iter(series.values()), [])), dtype=int)

    axes[0].plot(t, series.get("energy_mean", []), label="mean(E)")
    axes[0].fill_between(
        t,
        series.get("energy_min", []),
        series.get("energy_max", []),
        alpha=0.2,
        label="min/max(E)",
    )
    axes[0].set_title("Energy invariants")
    axes[0].set_xlabel("step")
    axes[0].set_ylabel("energy")
    axes[0].legend()

    axes[1].plot(t, series.get("entropy_mean", []), label="mean(S)")
    axes[1].plot(t, series.get("internal_time_mean", []), label="mean(τ)")
    axes[1].set_title("Entropy / internal time")
    axes[1].set_xlabel("step")
    axes[1].legend()

    fig.tight_layout()
    return FieldPlot(figure=fig, axes=axes)


def plot_radial(field: ScalarField, *, center: tuple[int, int] | None = None) -> FieldPlot:
    """Plot radial average profile to mirror legacy ``analyze_fields.py``."""

    profile, radii = radial_profile(field, center=center)
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(radii, profile)
    ax.set_title("Radial average")
    ax.set_xlabel("radius (cells)")
    ax.set_ylabel("mean value")
    ax.grid(alpha=0.35)
    fig.tight_layout()
    return FieldPlot(figure=fig, axes=[ax])


def plotly_scalar_field(
    field: ScalarField,
    *,
    title: str | None = None,
    colorscale: str = "Magma",
):
    """Return a Plotly heatmap figure if the dependency is available."""

    try:
        import plotly.graph_objects as go
    except ImportError:  # pragma: no cover - exercised in runtime only
        return None

    arr = _to_array(field)
    fig = go.Figure(
        data=go.Heatmap(
            z=arr,
            colorscale=colorscale,
            colorbar=dict(title="value"),
        )
    )
    fig.update_layout(
        title=title or "Scalar field",
        xaxis_title="x",
        yaxis_title="y",
    )
    return fig


__all__ = [
    "FieldPlot",
    "plot_field_state",
    "plot_invariants",
    "plot_radial",
    "plot_scalar_field",
    "plotly_scalar_field",
]
