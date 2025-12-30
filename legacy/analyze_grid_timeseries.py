#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import numpy as np
import matplotlib.pyplot as plt


def dominant_freq_map(E_hist: np.ndarray, dt: float = 1.0) -> tuple[np.ndarray, np.ndarray]:
    """
    E_hist: [T, N, N]
    Возвращает:
      f_dom: [N, N] доминирующая частота (в 1/dt)
      p_dom: [N, N] мощность на доминирующей частоте
    """
    T = E_hist.shape[0]
    X = E_hist.astype(np.float32)

    # remove mean per cell to kill DC
    X = X - X.mean(axis=0, keepdims=True)

    # rFFT along time axis
    F = np.fft.rfft(X, axis=0)  # [F, N, N]
    P = (F.real * F.real + F.imag * F.imag)  # power

    freqs = np.fft.rfftfreq(T, d=dt)  # [F]

    # ignore DC bin (0)
    if P.shape[0] > 1:
        P0 = P[1:]
        idx = np.argmax(P0, axis=0) + 1
    else:
        idx = np.zeros((E_hist.shape[1], E_hist.shape[2]), dtype=int)

    f_dom = freqs[idx]
    p_dom = P[idx, np.arange(E_hist.shape[1])[:, None], np.arange(E_hist.shape[2])[None, :]]
    return f_dom, p_dom


def plot_top_points(t: np.ndarray, E_hist: np.ndarray, score_map: np.ndarray, k: int, out_png: str):
    """
    Рисует k точек с максимальным score_map (например std или p_dom).
    """
    N = score_map.shape[0]
    flat = score_map.reshape(-1)
    top_idx = np.argsort(flat)[-k:][::-1]

    plt.figure(figsize=(12, 6))
    for m, idx in enumerate(top_idx):
        i = idx // N
        j = idx % N
        y = E_hist[:, i, j]
        plt.plot(t, y, label=f"({i},{j}) score={score_map[i,j]:.4g}")

        if m >= 12:  # чтобы легенда не стала адом
            break

    plt.title(f"Top points by score (showing up to 13 of {k})")
    plt.xlabel("t (saved frames index / t_global if available)")
    plt.ylabel("E")
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(out_png, dpi=160)
    plt.close()


def save_heatmap(img: np.ndarray, title: str, out_png: str):
    plt.figure(figsize=(7, 6))
    plt.imshow(img, origin="lower", interpolation="nearest")
    plt.title(title)
    plt.colorbar()
    plt.tight_layout()
    plt.savefig(out_png, dpi=160)
    plt.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--npz", required=True, help="Path to E_hist_<run_id>.npz")
    ap.add_argument("--out", default=None, help="Output dir (default: рядом с npz)")
    ap.add_argument("--top-k", type=int, default=50)
    args = ap.parse_args()

    npz_path = args.npz
    out_dir = args.out or os.path.join(os.path.dirname(npz_path), "analysis")
    os.makedirs(out_dir, exist_ok=True)

    data = np.load(npz_path)
    E_hist = data["E_hist"]  # [T, N, N]
    # IMPORTANT: если сохранено в float16, статистики в numpy тоже будут float16 и могут быть мусором.
    # Апкастим для корректных mean/std/fft.
    E_hist = E_hist.astype(np.float32, copy=False)
    t = data.get("t", None)
    if t is None:
        t = np.arange(E_hist.shape[0], dtype=float)
    else:
        # если t весь nan (бывает), fallback на индекс
        if not np.isfinite(t).any():
            t = np.arange(E_hist.shape[0], dtype=float)

    # базовые карты
    mean_E = np.mean(E_hist, axis=0, dtype=np.float64)
    std_E = np.std(E_hist, axis=0, dtype=np.float64)

    save_heatmap(mean_E, "mean(E) per cell", os.path.join(out_dir, "mean_E.png"))
    save_heatmap(std_E, "std(E) per cell", os.path.join(out_dir, "std_E.png"))

    # частотная карта
    f_dom, p_dom = dominant_freq_map(E_hist, dt=1.0)
    save_heatmap(f_dom, "dominant frequency f_dom", os.path.join(out_dir, "f_dom.png"))
    save_heatmap(p_dom, "dominant power p_dom", os.path.join(out_dir, "p_dom.png"))

    # графики лучших точек
    plot_top_points(t, E_hist, std_E, k=args.top_k, out_png=os.path.join(out_dir, "top_by_std.png"))
    plot_top_points(t, E_hist, p_dom, k=args.top_k, out_png=os.path.join(out_dir, "top_by_pdom.png"))

    # сохраним таблицу топ-точек (по std)
    N = std_E.shape[0]
    flat = std_E.reshape(-1)
    top_idx = np.argsort(flat)[-args.top_k:][::-1]
    out_csv = os.path.join(out_dir, "top_points_by_std.csv")
    with open(out_csv, "w", encoding="utf-8") as f:
        f.write("rank,i,j,std\n")
        for r, idx in enumerate(top_idx, 1):
            i = idx // N
            j = idx % N
            f.write(f"{r},{i},{j},{std_E[i,j]:.8g}\n")

    print("[OK] Wrote analysis to:", out_dir)
    print("[OK] Source:", npz_path)


if __name__ == "__main__":
    main()
