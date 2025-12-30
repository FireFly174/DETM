#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import numpy as np
import matplotlib.pyplot as plt


def div2d(Jx, Jy):
    # Jx, Jy: [N,N]
    # div = dJx/dx + dJy/dy (дискретно через центральную разность)
    dJx = 0.5 * (np.roll(Jx, -1, axis=0) - np.roll(Jx, 1, axis=0))
    dJy = 0.5 * (np.roll(Jy, -1, axis=1) - np.roll(Jy, 1, axis=1))
    return dJx + dJy


def curl2d(Jx, Jy):
    # curl_z = dJy/dx - dJx/dy
    dJy_dx = 0.5 * (np.roll(Jy, -1, axis=0) - np.roll(Jy, 1, axis=0))
    dJx_dy = 0.5 * (np.roll(Jx, -1, axis=1) - np.roll(Jx, 1, axis=1))
    return dJy_dx - dJx_dy


def save_heatmap(img, title, out_png):
    plt.figure(figsize=(7, 6))
    plt.imshow(img, origin="lower", interpolation="nearest")
    plt.title(title)
    plt.colorbar()
    plt.tight_layout()
    plt.savefig(out_png, dpi=160)
    plt.close()


def rings_indices(N, center, r_max=None):
    cx, cy = center
    xs = np.arange(N)[:, None]
    ys = np.arange(N)[None, :]
    rr = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2)
    if r_max is None:
        r_max = int(rr.max())
    ridx = np.clip(rr.astype(int), 0, r_max)
    return ridx, r_max


def ring_means(field, ridx, r_max):
    # field: [T,N,N] or [N,N]
    if field.ndim == 2:
        out = np.zeros((r_max + 1,), dtype=np.float64)
        for r in range(r_max + 1):
            m = (ridx == r)
            out[r] = field[m].mean() if m.any() else np.nan
        return out
    else:
        T = field.shape[0]
        out = np.zeros((T, r_max + 1), dtype=np.float64)
        for r in range(r_max + 1):
            m = (ridx == r)
            if not m.any():
                out[:, r] = np.nan
            else:
                out[:, r] = field[:, m].mean(axis=1)
        return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--npz", required=True, help="fields_hist_<run_id>.npz")
    ap.add_argument("--out", default=None)
    ap.add_argument("--center", default=None, help="cx,cy (default: argmax mean(E))")
    ap.add_argument("--rmax", type=int, default=None)
    args = ap.parse_args()

    data = np.load(args.npz)

    t = data.get("t", None)
    if t is None or (not np.isfinite(t).any()):
        # fallback
        any_key = next(k for k in data.files if k.endswith("_hist"))
        T = data[any_key].shape[0]
        t = np.arange(T, dtype=float)

    # load fields
    E_hist = data.get("E_hist", None)
    Jx_hist = data.get("Jx_hist", None)
    Jy_hist = data.get("Jy_hist", None)

    if E_hist is None:
        raise RuntimeError("E_hist not found in npz. Enable fields ('E') in logger.")

    # IMPORTANT: stats in float64
    E_hist = E_hist.astype(np.float32, copy=False)

    out_dir = args.out or os.path.join(os.path.dirname(args.npz), "analysis_fields")
    os.makedirs(out_dir, exist_ok=True)

    mean_E = np.mean(E_hist, axis=0, dtype=np.float64)
    std_E = np.std(E_hist, axis=0, dtype=np.float64)
    save_heatmap(mean_E, "mean(E)", os.path.join(out_dir, "mean_E.png"))
    save_heatmap(std_E, "std(E)", os.path.join(out_dir, "std_E.png"))

    # center
    N = mean_E.shape[0]
    if args.center is None:
        idx = np.argmax(mean_E)
        cx, cy = idx // N, idx % N
    else:
        cx, cy = map(int, args.center.split(","))
    ridx, r_max = rings_indices(N, (cx, cy), r_max=args.rmax)

    # ring signals for E
    E_ring = ring_means(E_hist, ridx, r_max)  # [T, r]
    save_heatmap(E_ring.T, "E ring means (r x t)", os.path.join(out_dir, "E_ring.png"))

    # J analysis if present
    if (Jx_hist is not None) and (Jy_hist is not None):
        Jx_hist = Jx_hist.astype(np.float32, copy=False)
        Jy_hist = Jy_hist.astype(np.float32, copy=False)

        # magnitude
        Jmag_hist = np.sqrt(Jx_hist * Jx_hist + Jy_hist * Jy_hist, dtype=np.float32)
        mean_J = np.mean(Jmag_hist, axis=0, dtype=np.float64)
        std_J = np.std(Jmag_hist, axis=0, dtype=np.float64)
        save_heatmap(mean_J, "mean(|J|)", os.path.join(out_dir, "mean_Jmag.png"))
        save_heatmap(std_J, "std(|J|)", os.path.join(out_dir, "std_Jmag.png"))

        # div/curl for last frame (or average)
        Jx_last = Jx_hist[-1]
        Jy_last = Jy_hist[-1]
        div_last = div2d(Jx_last, Jy_last)
        curl_last = curl2d(Jx_last, Jy_last)
        save_heatmap(div_last, "div J (last frame)", os.path.join(out_dir, "divJ_last.png"))
        save_heatmap(curl_last, "curl J (last frame)", os.path.join(out_dir, "curlJ_last.png"))

        # ring signals for |J|
        J_ring = ring_means(Jmag_hist, ridx, r_max)  # [T, r]
        save_heatmap(J_ring.T, "|J| ring means (r x t)", os.path.join(out_dir, "J_ring.png"))

    # plot a few ring curves
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
