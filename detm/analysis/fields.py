"""Analyze recorded field histories (`fields_hist.npz`).

This is adapted from `legacy/analyze_fields.py` and supports the new recorder
output:
  t, E_hist, S_hist, tau_hist, Jx_hist, Jy_hist
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Tuple

import numpy as np


def _require_matplotlib():
    try:
        import matplotlib.pyplot as plt  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("matplotlib is required for detm.analysis (pip install matplotlib)") from exc
    return plt


def div2d(Jx: np.ndarray, Jy: np.ndarray) -> np.ndarray:
    dJx = 0.5 * (np.roll(Jx, -1, axis=0) - np.roll(Jx, 1, axis=0))
    dJy = 0.5 * (np.roll(Jy, -1, axis=1) - np.roll(Jy, 1, axis=1))
    return dJx + dJy


def curl2d(Jx: np.ndarray, Jy: np.ndarray) -> np.ndarray:
    dJy_dx = 0.5 * (np.roll(Jy, -1, axis=0) - np.roll(Jy, 1, axis=0))
    dJx_dy = 0.5 * (np.roll(Jx, -1, axis=1) - np.roll(Jx, 1, axis=1))
    return dJy_dx - dJx_dy


def save_heatmap(img: np.ndarray, title: str, out_png: str) -> None:
    plt = _require_matplotlib()
    plt.figure(figsize=(7, 6))
    plt.imshow(img, origin="lower", interpolation="nearest")
    plt.title(title)
    plt.colorbar()
    plt.tight_layout()
    plt.savefig(out_png, dpi=160)
    plt.close()


def rings_indices(N: int, center: Tuple[int, int], r_max: int | None = None):
    cx, cy = center
    xs = np.arange(N)[:, None]
    ys = np.arange(N)[None, :]
    rr = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2)
    if r_max is None:
        r_max = int(rr.max())
    ridx = np.clip(rr.astype(int), 0, r_max)
    return ridx, r_max


def ring_means(field: np.ndarray, ridx: np.ndarray, r_max: int) -> np.ndarray:
    if field.ndim == 2:
        out = np.zeros((r_max + 1,), dtype=np.float64)
        for r in range(r_max + 1):
            m = ridx == r
            out[r] = field[m].mean() if m.any() else np.nan
        return out
    T = field.shape[0]
    out = np.zeros((T, r_max + 1), dtype=np.float64)
    for r in range(r_max + 1):
        m = ridx == r
        if not m.any():
            out[:, r] = np.nan
        else:
            out[:, r] = field[:, m].mean(axis=1)
    return out


def main() -> None:  # pragma: no cover (CLI utility)
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--npz", required=True, help="Path to fields_hist.npz")
    ap.add_argument("--out", default=None, help="Output dir (default: рядом с npz)")
    ap.add_argument("--center", default=None, help="cx,cy (default: argmax mean(E))")
    ap.add_argument("--rmax", type=int, default=None)
    args = ap.parse_args()

    data = np.load(args.npz)
    t = data.get("t", None)
    if t is None or (not np.isfinite(t).any()):
        any_key = next(k for k in data.files if k.endswith("_hist"))
        T = data[any_key].shape[0]
        t = np.arange(T, dtype=float)

    E_hist = data.get("E_hist", None)
    S_hist = data.get("S_hist", None)
    tau_hist = data.get("tau_hist", None)
    Jx_hist = data.get("Jx_hist", None)
    Jy_hist = data.get("Jy_hist", None)

    if E_hist is None:
        raise RuntimeError("E_hist not found in npz.")

    E_hist = E_hist.astype(np.float32, copy=False)
    out_dir = args.out or os.path.join(os.path.dirname(args.npz), "analysis_fields")
    os.makedirs(out_dir, exist_ok=True)

    mean_E = np.mean(E_hist, axis=0, dtype=np.float64)
    std_E = np.std(E_hist, axis=0, dtype=np.float64)
    save_heatmap(mean_E, "mean(E)", os.path.join(out_dir, "mean_E.png"))
    save_heatmap(std_E, "std(E)", os.path.join(out_dir, "std_E.png"))

    if S_hist is not None:
        S_hist = S_hist.astype(np.float32, copy=False)
        save_heatmap(np.mean(S_hist, axis=0, dtype=np.float64), "mean(S)", os.path.join(out_dir, "mean_S.png"))
        save_heatmap(np.std(S_hist, axis=0, dtype=np.float64), "std(S)", os.path.join(out_dir, "std_S.png"))

    if tau_hist is not None:
        tau_hist = tau_hist.astype(np.float32, copy=False)
        save_heatmap(
            np.mean(tau_hist, axis=0, dtype=np.float64),
            "mean(tau)",
            os.path.join(out_dir, "mean_tau.png"),
        )
        save_heatmap(np.std(tau_hist, axis=0, dtype=np.float64), "std(tau)", os.path.join(out_dir, "std_tau.png"))

    N = mean_E.shape[0]
    if args.center is None:
        idx = int(np.argmax(mean_E))
        cx, cy = idx // N, idx % N
    else:
        cx, cy = map(int, str(args.center).split(","))
    ridx, r_max = rings_indices(N, (cx, cy), r_max=args.rmax)

    E_ring = ring_means(E_hist, ridx, r_max)
    save_heatmap(E_ring.T, "E ring means (r x t)", os.path.join(out_dir, "E_ring.png"))

    if Jx_hist is not None and Jy_hist is not None:
        Jx_hist = Jx_hist.astype(np.float32, copy=False)
        Jy_hist = Jy_hist.astype(np.float32, copy=False)
        Jmag_hist = np.sqrt(Jx_hist * Jx_hist + Jy_hist * Jy_hist, dtype=np.float32)
        save_heatmap(np.mean(Jmag_hist, axis=0, dtype=np.float64), "mean(|J|)", os.path.join(out_dir, "mean_Jmag.png"))
        save_heatmap(np.std(Jmag_hist, axis=0, dtype=np.float64), "std(|J|)", os.path.join(out_dir, "std_Jmag.png"))

        div_last = div2d(Jx_hist[-1], Jy_hist[-1])
        curl_last = curl2d(Jx_hist[-1], Jy_hist[-1])
        save_heatmap(div_last, "div J (last)", os.path.join(out_dir, "divJ_last.png"))
        save_heatmap(curl_last, "curl J (last)", os.path.join(out_dir, "curlJ_last.png"))

        J_ring = ring_means(Jmag_hist, ridx, r_max)
        save_heatmap(J_ring.T, "|J| ring means (r x t)", os.path.join(out_dir, "J_ring.png"))

    plt = _require_matplotlib()
    plt.figure(figsize=(12, 5))
    for r in [0, 2, 5, 10, 15]:
        if r <= r_max:
            plt.plot(t, E_ring[:, r], label=f"r={r}")
    plt.title(f"E ring means around center ({cx},{cy})")
    plt.xlabel("t")
    plt.ylabel("E_ring")
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "E_ring_curves.png"), dpi=160)
    plt.close()

    print("[OK] center:", (cx, cy), "r_max:", r_max)
    print("[OK] wrote:", out_dir)


if __name__ == "__main__":
    main()

