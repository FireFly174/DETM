#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import numpy as np


def div2d(Jx, Jy):
    # NOTE: axis convention must match your field layout.
    # Here assumes axis0 = x (rows), axis1 = y (cols), consistent with your original code.
    dJx = 0.5 * (np.roll(Jx, -1, axis=0) - np.roll(Jx, 1, axis=0))
    dJy = 0.5 * (np.roll(Jy, -1, axis=1) - np.roll(Jy, 1, axis=1))
    return dJx + dJy


def curl2d(Jx, Jy):
    dJy_dx = 0.5 * (np.roll(Jy, -1, axis=0) - np.roll(Jy, 1, axis=0))
    dJx_dy = 0.5 * (np.roll(Jx, -1, axis=1) - np.roll(Jx, 1, axis=1))
    return dJy_dx - dJx_dy


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


def find_hist_key(d, candidates):
    for k in candidates:
        if k in d.files:
            return k
    return None


def quantize_linear_int8(x, clip_sigma=4.0):
    """
    Simple robust int8 quantization around mean/std.
    Returns (q:int8, scale:float32, zero:float32).
    Reconstruct approx: x_hat = scale*(q) + zero
    """
    x = x.astype(np.float32, copy=False)
    mu = np.nanmean(x, dtype=np.float64)
    sig = np.nanstd(x, dtype=np.float64)
    if not np.isfinite(sig) or sig < 1e-12:
        sig = 1.0
    lo = mu - clip_sigma * sig
    hi = mu + clip_sigma * sig
    x_clip = np.clip(x, lo, hi)
    # map [lo,hi] -> [-127,127]
    scale = (hi - lo) / 254.0
    if scale < 1e-12:
        scale = 1.0
    q = np.round((x_clip - (lo + hi) / 2.0) / scale).astype(np.int16)
    q = np.clip(q, -127, 127).astype(np.int8)
    zero = np.float32((lo + hi) / 2.0)
    scale = np.float32(scale)
    return q, scale, zero


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--npz", required=True, help="fields_hist_<run_id>.npz")
    ap.add_argument("--out", default=None, help="output compact npz path")
    ap.add_argument("--stride", type=int, default=5, help="keep every N-th tick")
    ap.add_argument("--center", default=None, help="cx,cy (default: argmax mean(E))")
    ap.add_argument("--rmax", type=int, default=None, help="max ring radius")
    ap.add_argument("--keep-ehist", action="store_true", help="also store E_hist (downsampled)")
    ap.add_argument("--keep-jhist", action="store_true", help="also store Jx/Jy hist (downsampled)")
    ap.add_argument("--dtype", choices=["float16", "float32", "int8"], default="float16",
                    help="storage dtype for big arrays; int8 uses linear quantization")
    ap.add_argument("--clip-sigma", type=float, default=4.0, help="for int8 quantization")
    args = ap.parse_args()

    d = np.load(args.npz)

    # keys can differ; support both naming styles
    kE = find_hist_key(d, ["E_hist", "E"])
    kJx = find_hist_key(d, ["Jx_hist", "Jx"])
    kJy = find_hist_key(d, ["Jy_hist", "Jy"])
    kt = find_hist_key(d, ["t", "t_hist"])

    if kE is None:
        raise RuntimeError("E_hist not found. Expected one of: E_hist, E")

    E_hist = d[kE]
    if E_hist.ndim != 3:
        raise RuntimeError(f"{kE} must be [T,N,N], got {E_hist.shape}")

    # time downsample
    stride = max(1, int(args.stride))
    E_hist_ds = E_hist[::stride].astype(np.float32, copy=False)

    if kt is None:
        t = np.arange(E_hist.shape[0], dtype=np.float32)[::stride]
    else:
        t0 = d[kt]
        if (t0 is None) or (not np.isfinite(t0).any()):
            t = np.arange(E_hist.shape[0], dtype=np.float32)[::stride]
        else:
            t = t0[::stride].astype(np.float32, copy=False)

    # summary stats for E
    mean_E = np.mean(E_hist_ds, axis=0, dtype=np.float64).astype(np.float32)
    std_E = np.std(E_hist_ds, axis=0, dtype=np.float64).astype(np.float32)

    N = mean_E.shape[0]

    # center selection
    if args.center is None:
        idx = int(np.argmax(mean_E))
        cx, cy = idx // N, idx % N
    else:
        cx, cy = map(int, args.center.split(","))

    ridx, r_max = rings_indices(N, (cx, cy), r_max=args.rmax)

    # ring means (core export feature)
    E_ring = ring_means(E_hist_ds, ridx, r_max).astype(np.float32)  # [T_ds, r]

    out = {
        "t": t,
        "center": np.array([cx, cy], dtype=np.int32),
        "r_max": np.int32(r_max),
        "stride": np.int32(stride),

        "mean_E": mean_E,
        "std_E": std_E,
        "E_ring": E_ring,
    }

    # J-derived features if available
    have_J = (kJx is not None) and (kJy is not None)
    if have_J:
        Jx_hist = d[kJx][::stride].astype(np.float32, copy=False)
        Jy_hist = d[kJy][::stride].astype(np.float32, copy=False)

        Jmag_hist = np.sqrt(Jx_hist * Jx_hist + Jy_hist * Jy_hist).astype(np.float32)
        mean_Jmag = np.mean(Jmag_hist, axis=0, dtype=np.float64).astype(np.float32)
        std_Jmag = np.std(Jmag_hist, axis=0, dtype=np.float64).astype(np.float32)

        out["mean_Jmag"] = mean_Jmag
        out["std_Jmag"] = std_Jmag
        out["J_ring"] = ring_means(Jmag_hist, ridx, r_max).astype(np.float32)

        # last-frame div/curl
        Jx_last = Jx_hist[-1]
        Jy_last = Jy_hist[-1]
        out["div_last"] = div2d(Jx_last, Jy_last).astype(np.float32)
        out["curl_last"] = curl2d(Jx_last, Jy_last).astype(np.float32)

        if args.keep_jhist:
            out["Jx_hist_ds"] = Jx_hist
            out["Jy_hist_ds"] = Jy_hist

    if args.keep_ehist:
        out["E_hist_ds"] = E_hist_ds

    # apply storage dtype/quantization to large arrays
    big_keys = [k for k in out.keys() if k.endswith("_ds") or k in ("E_ring", "J_ring")]
    big_keys += [k for k in out.keys() if k in ("mean_E", "std_E", "mean_Jmag", "std_Jmag", "div_last", "curl_last")]

    if args.dtype == "float16":
        for k in big_keys:
            if k in out and isinstance(out[k], np.ndarray) and out[k].dtype == np.float32:
                out[k] = out[k].astype(np.float16)
        out["storage"] = np.array([b"float16"])
    elif args.dtype == "int8":
        # quantize selected float arrays (keeps meta scale/zero)
        qmeta = {}
        for k in big_keys:
            if k in out and isinstance(out[k], np.ndarray) and out[k].dtype in (np.float16, np.float32):
                q, scale, zero = quantize_linear_int8(out[k].astype(np.float32), clip_sigma=args.clip_sigma)
                out[k] = q
                qmeta[f"{k}__scale"] = np.array([scale], dtype=np.float32)
                qmeta[f"{k}__zero"] = np.array([zero], dtype=np.float32)
        out.update(qmeta)
        out["storage"] = np.array([b"int8_linear"])
        out["clip_sigma"] = np.array([args.clip_sigma], dtype=np.float32)
    else:
        out["storage"] = np.array([b"float32"])

    # output path
    out_path = args.out
    if out_path is None:
        base = os.path.basename(args.npz).replace(".npz", "")
        out_path = os.path.join(os.path.dirname(args.npz), f"{base}__export_s{stride}_{args.dtype}.npz")

    np.savez_compressed(out_path, **out)

    # report
    try:
        in_mb = os.path.getsize(args.npz) / 1024**2
        out_mb = os.path.getsize(out_path) / 1024**2
        print(f"[OK] wrote: {out_path}")
        print(f"     size: {in_mb:.1f} MB -> {out_mb:.1f} MB")
        print(f"     center=({cx},{cy}), r_max={r_max}, stride={stride}, have_J={have_J}, storage={args.dtype}")
    except Exception:
        print(f"[OK] wrote: {out_path}")

if __name__ == "__main__":
    main()
