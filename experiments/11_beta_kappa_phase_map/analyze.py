"""Aggregate and plot the beta x kappa crystallization sweep.

The script intentionally treats `runs/11_beta_kappa_phase_map` as the
source-of-truth run artifact and writes only derived analysis artifacts.
"""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, pstdev

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUN_DIR = REPO_ROOT / "runs" / "11_beta_kappa_phase_map"
DEFAULT_DOCS_FIGURE = REPO_ROOT / "docs" / "media" / "png" / "beta_kappa_phase_map.png"


@dataclass(frozen=True)
class SweepRow:
    seed: int
    beta: float
    kappa: float
    crystallized: bool
    final_structure_score: float
    final_energy_var: float
    final_internal_time_mean: float
    final_max_attractor_strength: float
    execution_backend_resolved: str
    execution_device_resolved: str
    state_npz: Path


def _read_rows(summary_csv: Path) -> list[SweepRow]:
    rows: list[SweepRow] = []
    with summary_csv.open(newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            rows.append(
                SweepRow(
                    seed=int(raw["seed"]),
                    beta=float(raw["beta"]),
                    kappa=float(raw["kappa"]),
                    crystallized=raw["crystallized"].strip().lower() == "true",
                    final_structure_score=float(raw["final_structure_score"]),
                    final_energy_var=float(raw["final_energy_var"]),
                    final_internal_time_mean=float(raw["final_internal_time_mean"]),
                    final_max_attractor_strength=float(raw["final_max_attractor_strength"]),
                    execution_backend_resolved=raw["execution_backend_resolved"],
                    execution_device_resolved=raw["execution_device_resolved"],
                    state_npz=Path(raw["state_npz"]),
                )
            )
    return rows


def _midrun_residual_std(state_npz: Path, key: str = "energy_step_0300") -> float:
    with np.load(state_npz) as data:
        field = np.asarray(data[key], dtype=float)
    return float(np.std(field))


def _safe_log10(value: float) -> float:
    if value <= 0.0:
        return -18.0
    return math.log10(value)


def _aggregate(rows: list[SweepRow]) -> list[dict[str, float | int | bool]]:
    grouped: dict[tuple[float, float], list[SweepRow]] = defaultdict(list)
    for row in rows:
        grouped[(row.beta, row.kappa)].append(row)

    aggregated: list[dict[str, float | int | bool]] = []
    for (beta, kappa), group in sorted(grouped.items()):
        mid_residual = [_midrun_residual_std(row.state_npz) for row in group]
        final_structure = [row.final_structure_score for row in group]
        final_energy_var = [row.final_energy_var for row in group]
        final_internal_time = [row.final_internal_time_mean for row in group]
        final_strength = [row.final_max_attractor_strength for row in group]
        aggregated.append(
            {
                "beta": beta,
                "kappa": kappa,
                "run_count": len(group),
                "crystallized_count": sum(1 for row in group if row.crystallized),
                "final_structure_score_mean": mean(final_structure),
                "final_structure_score_std": pstdev(final_structure),
                "final_energy_var_mean": mean(final_energy_var),
                "final_energy_var_std": pstdev(final_energy_var),
                "final_internal_time_mean": mean(final_internal_time),
                "final_internal_time_std": pstdev(final_internal_time),
                "final_max_attractor_strength_mean": mean(final_strength),
                "final_max_attractor_strength_std": pstdev(final_strength),
                "mid300_residual_std_mean": mean(mid_residual),
                "mid300_residual_std_std": pstdev(mid_residual),
            }
        )
    return aggregated


def _write_csv(path: Path, rows: list[dict[str, float | int | bool]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError("no rows to write")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _matrix(
    rows: list[dict[str, float | int | bool]], field: str, betas: list[float], kappas: list[float]
) -> np.ndarray:
    values = {(float(row["beta"]), float(row["kappa"])): float(row[field]) for row in rows}
    return np.asarray([[values[(beta, kappa)] for kappa in kappas] for beta in betas], dtype=float)


def _plot_phase_map(
    path: Path,
    rows: list[dict[str, float | int | bool]],
    betas: list[float],
    kappas: list[float],
) -> None:
    import matplotlib.pyplot as plt
    from matplotlib import colormaps
    from matplotlib.colors import Normalize

    panels = [
        (
            "Final structure score, log10(mean)",
            np.vectorize(_safe_log10)(_matrix(rows, "final_structure_score_mean", betas, kappas)),
            ".2f",
            "viridis",
        ),
        (
            "Final energy variance, log10(mean)",
            np.vectorize(_safe_log10)(_matrix(rows, "final_energy_var_mean", betas, kappas)),
            ".2f",
            "magma",
        ),
        (
            "Final internal time, mean",
            _matrix(rows, "final_internal_time_mean", betas, kappas),
            ".2f",
            "cividis",
        ),
        (
            "Tick 300 residual std, log10(mean)",
            np.vectorize(_safe_log10)(_matrix(rows, "mid300_residual_std_mean", betas, kappas)),
            ".2f",
            "plasma",
        ),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(11, 8.2), constrained_layout=True)
    fig.suptitle("DETM beta x kappa phase map, size 24, seeds 12345/22222/54321", fontsize=14)

    for ax, (title, values, fmt, cmap) in zip(axes.ravel(), panels):
        image = ax.imshow(values, aspect="auto", cmap=cmap)
        cmap_obj = colormaps[cmap]
        norm = Normalize(vmin=float(np.nanmin(values)), vmax=float(np.nanmax(values)))
        ax.set_title(title)
        ax.set_xlabel("kappa")
        ax.set_ylabel("beta")
        ax.set_xticks(range(len(kappas)), [f"{value:g}" for value in kappas])
        ax.set_yticks(range(len(betas)), [f"{value:g}" for value in betas])
        for row_idx, beta in enumerate(betas):
            for col_idx, kappa in enumerate(kappas):
                rgba = cmap_obj(norm(values[row_idx, col_idx]))
                luminance = 0.2126 * rgba[0] + 0.7152 * rgba[1] + 0.0722 * rgba[2]
                ax.text(
                    col_idx,
                    row_idx,
                    format(values[row_idx, col_idx], fmt),
                    ha="center",
                    va="center",
                    fontsize=8,
                    color="black" if luminance > 0.58 else "white",
                )
        fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)

    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _write_readout(path: Path, rows: list[SweepRow], aggregated: list[dict[str, float | int | bool]]) -> None:
    strongest = max(aggregated, key=lambda row: float(row["final_structure_score_mean"]))
    flattest = min(aggregated, key=lambda row: float(row["final_structure_score_mean"]))
    mid_residual = max(aggregated, key=lambda row: float(row["mid300_residual_std_mean"]))
    crystallized_count = sum(1 for row in rows if row.crystallized)
    backends = sorted(
        {f"{row.execution_backend_resolved}/{row.execution_device_resolved}" for row in rows}
    )
    backend_label = ", ".join(backends) if backends else "unknown"
    run_dir_label = DEFAULT_RUN_DIR.relative_to(REPO_ROOT).as_posix()

    path.write_text(
        "\n".join(
            [
                "# Beta x Kappa Phase Map Readout",
                "",
                f"- Source runs: `{run_dir_label}`",
                f"- Completed cells: `{len(aggregated)}` parameter cells / `{len(rows)}` runs",
                f"- Backend observed in catalog summaries: `{backend_label}`",
                f"- Crystallized by protocol threshold: `{crystallized_count}` / `{len(rows)}` runs",
                "",
                "## Main Signals",
                "",
                (
                    "- Largest late residual structure: "
                    f"`beta={float(strongest['beta']):g}`, `kappa={float(strongest['kappa']):g}`, "
                    f"mean structure `{float(strongest['final_structure_score_mean']):.6g}`."
                ),
                (
                    "- Strongest late flattening: "
                    f"`beta={float(flattest['beta']):g}`, `kappa={float(flattest['kappa']):g}`, "
                    f"mean structure `{float(flattest['final_structure_score_mean']):.6g}`."
                ),
                (
                    "- Largest tick-300 residual spread: "
                    f"`beta={float(mid_residual['beta']):g}`, `kappa={float(mid_residual['kappa']):g}`, "
                    f"mean residual std `{float(mid_residual['mid300_residual_std_mean']):.6g}`."
                ),
                "",
                "## Artifacts",
                "",
                "- `analysis/phase_map_summary.csv`",
                "- `analysis/beta_kappa_phase_map.png`",
                "- `docs/media/png/beta_kappa_phase_map.png`",
                "",
                "Applicability: this is a compact size-24, 3-seed readout. It supports regime screening, not a final architecture or universal threshold claim.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> None:
    run_dir = DEFAULT_RUN_DIR
    summary_csv = run_dir / "summary.csv"
    analysis_dir = run_dir / "analysis"
    rows = _read_rows(summary_csv)
    aggregated = _aggregate(rows)

    betas = sorted({row.beta for row in rows})
    kappas = sorted({row.kappa for row in rows})
    expected = len(betas) * len(kappas) * len({row.seed for row in rows})
    if len(rows) != expected:
        raise RuntimeError(f"incomplete sweep: got {len(rows)} rows, expected {expected}")

    _write_csv(analysis_dir / "phase_map_summary.csv", aggregated)
    _plot_phase_map(analysis_dir / "beta_kappa_phase_map.png", aggregated, betas, kappas)
    _plot_phase_map(DEFAULT_DOCS_FIGURE, aggregated, betas, kappas)
    _write_readout(analysis_dir / "README.md", rows, aggregated)

    print(f"[OK] wrote {analysis_dir / 'phase_map_summary.csv'}")
    print(f"[OK] wrote {analysis_dir / 'beta_kappa_phase_map.png'}")
    print(f"[OK] wrote {DEFAULT_DOCS_FIGURE}")


if __name__ == "__main__":
    main()
