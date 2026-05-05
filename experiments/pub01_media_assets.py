"""Build curated public media assets from completed experiment summaries."""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean, pstdev


REPO_ROOT = Path(__file__).resolve().parents[1]
MEDIA_DIR = REPO_ROOT / "docs" / "media" / "png"


def _read_summary(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _safe_log10(value: float) -> float:
    if value <= 0.0:
        return -18.0
    return math.log10(value)


def _aggregate(rows: list[dict[str, str]], axis: str) -> list[dict[str, float]]:
    grouped: dict[tuple[float, float], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(float(row[axis]), float(row["initial_equilibrium_energy"]))].append(row)

    aggregated: list[dict[str, float]] = []
    for (axis_value, eq_energy), group in sorted(grouped.items()):
        structure = [float(row["final_structure_score"]) for row in group]
        energy_var = [float(row["final_energy_var"]) for row in group]
        internal_time = [float(row["final_internal_time_mean"]) for row in group]
        strength = [float(row["final_max_attractor_strength"]) for row in group]
        aggregated.append(
            {
                axis: axis_value,
                "initial_equilibrium_energy": eq_energy,
                "run_count": float(len(group)),
                "final_structure_score_mean": mean(structure),
                "final_structure_score_std": pstdev(structure),
                "final_energy_var_mean": mean(energy_var),
                "final_energy_var_std": pstdev(energy_var),
                "final_internal_time_mean": mean(internal_time),
                "final_internal_time_std": pstdev(internal_time),
                "final_max_attractor_strength_mean": mean(strength),
                "final_max_attractor_strength_std": pstdev(strength),
            }
        )
    return aggregated


def _write_aggregate_csv(path: Path, rows: list[dict[str, float]]) -> None:
    if not rows:
        raise ValueError("no aggregate rows to write")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _plot_axis_readout(
    *,
    rows: list[dict[str, float]],
    axis: str,
    title: str,
    output_png: Path,
) -> None:
    import matplotlib.pyplot as plt

    eq_values = sorted({row["initial_equilibrium_energy"] for row in rows})
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.1), constrained_layout=True)
    fig.suptitle(title, fontsize=13)

    panels = [
        ("Final structure score", "final_structure_score_mean", "log10", "o"),
        ("Final energy variance", "final_energy_var_mean", "log10", "s"),
        ("Final internal time", "final_internal_time_mean", "linear", "^"),
    ]

    for ax_obj, (panel_title, field, scale, marker) in zip(axes, panels):
        for eq_energy in eq_values:
            series = [row for row in rows if row["initial_equilibrium_energy"] == eq_energy]
            x_values = [row[axis] for row in series]
            y_values = [row[field] for row in series]
            if scale == "log10":
                y_values = [_safe_log10(value) for value in y_values]
                ylabel = "log10(mean)"
            else:
                ylabel = "mean"
            ax_obj.plot(
                x_values,
                y_values,
                marker=marker,
                linewidth=2.0,
                label=f"eq={eq_energy:g}",
            )
        ax_obj.set_title(panel_title)
        ax_obj.set_xlabel(axis)
        ax_obj.set_ylabel(ylabel)
        ax_obj.grid(True, alpha=0.28)
        ax_obj.legend(frameon=False)

    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, dpi=180)
    plt.close(fig)


def build_beta_readout() -> None:
    rows = _aggregate(_read_summary(REPO_ROOT / "runs" / "04_beta_viscosity" / "summary.csv"), "beta")
    _write_aggregate_csv(REPO_ROOT / "runs" / "04_beta_viscosity" / "analysis" / "beta_summary.csv", rows)
    _plot_axis_readout(
        rows=rows,
        axis="beta",
        title="DETM beta viscosity sweep, size 24, seeds 22222/44444/66666",
        output_png=MEDIA_DIR / "beta_viscosity_readout.png",
    )


def build_kappa_readout() -> None:
    rows = _aggregate(
        _read_summary(REPO_ROOT / "runs" / "07_kappa_viscosity" / "summary.csv"), "kappa"
    )
    _write_aggregate_csv(REPO_ROOT / "runs" / "07_kappa_viscosity" / "analysis" / "kappa_summary.csv", rows)
    _plot_axis_readout(
        rows=rows,
        axis="kappa",
        title="DETM kappa viscosity sweep, beta 0.9, size 24, seeds 22222/44444/66666",
        output_png=MEDIA_DIR / "kappa_viscosity_readout.png",
    )


def main() -> None:
    build_beta_readout()
    build_kappa_readout()
    print(f"[OK] wrote {MEDIA_DIR / 'beta_viscosity_readout.png'}")
    print(f"[OK] wrote {MEDIA_DIR / 'kappa_viscosity_readout.png'}")


if __name__ == "__main__":
    main()
