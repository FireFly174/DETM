"""Grid time-series analysis for `E_hist` (dominant frequency, top points).

Adapted from `legacy/analyze_grid_timeseries.py`.
"""

from __future__ import annotations

import argparse
import os

import numpy as np


def _require_matplotlib():
    try:
        import matplotlib.pyplot as plt  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("matplotlib is required for detm.analysis (pip install matplotlib)") from exc
    return plt


def dominant_freq_map(X_hist: np.ndarray, dt: float = 1.0) -> tuple[np.ndarray, np.ndarray]:
    T = X_hist.shape[0]
    X = X_hist.astype(np.float32, copy=False)
    X = X - X.mean(axis=0, keepdims=True)
    F = np.fft.rfft(X, axis=0)
    P = (F.real * F.real + F.imag * F.imag)
    freqs = np.fft.rfftfreq(T, d=dt)

    if P.shape[0] > 1:
        P0 = P[1:]
        idx = np.argmax(P0, axis=0) + 1
    else:
        idx = np.zeros((X_hist.shape[1], X_hist.shape[2]), dtype=int)

    f_dom = freqs[idx]
    p_dom = P[idx, np.arange(X_hist.shape[1])[:, None], np.arange(X_hist.shape[2])[None, :]]
    return f_dom, p_dom


def save_heatmap(img: np.ndarray, title: str, out_png: str) -> None:
    plt = _require_matplotlib()
    plt.figure(figsize=(7, 6))
    plt.imshow(img, origin="lower", interpolation="nearest")
    plt.title(title)
    plt.colorbar()
    plt.tight_layout()
    plt.savefig(out_png, dpi=160)
    plt.close()


def plot_top_points(t: np.ndarray, X_hist: np.ndarray, score_map: np.ndarray, k: int, out_png: str) -> None:
    plt = _require_matplotlib()
    N = score_map.shape[0]
    flat = score_map.reshape(-1)
    top_idx = np.argsort(flat)[-k:][::-1]

    plt.figure(figsize=(12, 6))
    for m, idx in enumerate(top_idx):
        i = int(idx // N)
        j = int(idx % N)
        y = X_hist[:, i, j]
        plt.plot(t, y, label=f"({i},{j}) score={score_map[i,j]:.4g}")
        if m >= 12:
            break
    plt.title(f"Top points by score (showing up to 13 of {k})")
    plt.xlabel("t")
    plt.ylabel("value")
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(out_png, dpi=160)
    plt.close()


def main() -> None:  # pragma: no cover
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--npz", required=True, help="Path to fields_hist.npz")
    ap.add_argument("--field", default="E", choices=["E", "S", "tau"], help="Which field to analyze")
    ap.add_argument("--out", default=None, help="Output dir (default: рядом с npz)")
    ap.add_argument("--top-k", type=int, default=50)
    args = ap.parse_args()

    out_dir = args.out or os.path.join(os.path.dirname(args.npz), "analysis_grid")
    os.makedirs(out_dir, exist_ok=True)

    data = np.load(args.npz)
    key = {"E": "E_hist", "S": "S_hist", "tau": "tau_hist"}[str(args.field)]
    X_hist = data[key].astype(np.float32, copy=False)

    t = data.get("t", None)
    if t is None or not np.isfinite(t).any():
        t = np.arange(X_hist.shape[0], dtype=float)

    mean_X = np.mean(X_hist, axis=0, dtype=np.float64)
    std_X = np.std(X_hist, axis=0, dtype=np.float64)
    save_heatmap(mean_X, f"mean({args.field}) per cell", os.path.join(out_dir, f"mean_{args.field}.png"))
    save_heatmap(std_X, f"std({args.field}) per cell", os.path.join(out_dir, f"std_{args.field}.png"))

    f_dom, p_dom = dominant_freq_map(X_hist, dt=1.0)
    save_heatmap(f_dom, f"dominant frequency ({args.field})", os.path.join(out_dir, f"f_dom_{args.field}.png"))
    save_heatmap(p_dom, f"dominant power ({args.field})", os.path.join(out_dir, f"p_dom_{args.field}.png"))

    plot_top_points(t, X_hist, std_X, k=int(args.top_k), out_png=os.path.join(out_dir, f"top_by_std_{args.field}.png"))
    plot_top_points(t, X_hist, p_dom, k=int(args.top_k), out_png=os.path.join(out_dir, f"top_by_pdom_{args.field}.png"))

    N = std_X.shape[0]
    flat = std_X.reshape(-1)
    top_idx = np.argsort(flat)[-int(args.top_k):][::-1]
    out_csv = os.path.join(out_dir, f"top_points_by_std_{args.field}.csv")
    with open(out_csv, "w", encoding="utf-8") as f:
        f.write("rank,i,j,std\n")
        for r, idx in enumerate(top_idx, 1):
            i = int(idx // N)
            j = int(idx % N)
            f.write(f"{r},{i},{j},{std_X[i,j]:.8g}\n")

    print("[OK] Wrote analysis to:", out_dir)
    print("[OK] Source:", args.npz)


if __name__ == "__main__":
    main()

