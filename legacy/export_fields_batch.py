#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import sys
import numpy as np


# -------------------------
# physics helpers
# -------------------------
def div2d(Jx, Jy):
    # axis0 = rows (x), axis1 = cols (y) — as in your original code
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


def find_key(d, candidates):
    for k in candidates:
        if k in d.files:
            return k
    return None


# -------------------------
# int8 quantization (optional)
# -------------------------
def quantize_linear_int8(x, clip_sigma=4.0):
    """
    Robust int8 quantization around mean/std.
    Returns (q:int8, scale:float32, zero:float32).
    Reconstruct approx: x_hat = scale*q + zero
    """
    x = x.astype(np.float32, copy=False)
    mu = np.nanmean(x, dtype=np.float64)
    sig = np.nanstd(x, dtype=np.float64)
    if not np.isfinite(sig) or sig < 1e-12:
        sig = 1.0
    lo = mu - clip_sigma * sig
    hi = mu + clip_sigma * sig
    x_clip = np.clip(x, lo, hi)

    scale = (hi - lo) / 254.0
    if scale < 1e-12:
        scale = 1.0

    mid = (lo + hi) / 2.0
    q = np.round((x_clip - mid) / scale).astype(np.int16)
    q = np.clip(q, -127, 127).astype(np.int8)

    return q, np.float32(scale), np.float32(mid)


# -------------------------
# export single file
# -------------------------
def export_one(
    npz_path: str,
    out_path: str,
    stride: int = 5,
    center: str | None = None,
    rmax: int | None = None,
    keep_ehist: bool = False,
    keep_jhist: bool = False,
    dtype: str = "float16",
    clip_sigma: float = 4.0,
):
    d = np.load(npz_path)

    kE = find_key(d, ["E_hist", "E"])
    kJx = find_key(d, ["Jx_hist", "Jx"])
    kJy = find_key(d, ["Jy_hist", "Jy"])
    kt = find_key(d, ["t", "t_hist"])

    if kE is None:
        raise RuntimeError(f"E_hist not found in {npz_path}")

    E_hist = d[kE]
    if E_hist.ndim != 3:
        raise RuntimeError(f"{kE} must be [T,N,N], got {E_hist.shape} in {npz_path}")

    stride = max(1, int(stride))
    E_ds = E_hist[::stride].astype(np.float32, copy=False)

    if kt is None:
        t = np.arange(E_hist.shape[0], dtype=np.float32)[::stride]
    else:
        t0 = d[kt]
        if t0 is None or (not np.isfinite(t0).any()):
            t = np.arange(E_hist.shape[0], dtype=np.float32)[::stride]
        else:
            t = t0[::stride].astype(np.float32, copy=False)

    mean_E = np.mean(E_ds, axis=0, dtype=np.float64).astype(np.float32)
    std_E = np.std(E_ds, axis=0, dtype=np.float64).astype(np.float32)

    N = mean_E.shape[0]
    if center is None:
        idx = int(np.argmax(mean_E))
        cx, cy = idx // N, idx % N
    else:
        cx, cy = map(int, center.split(","))

    ridx, r_max = rings_indices(N, (cx, cy), r_max=rmax)
    E_ring = ring_means(E_ds, ridx, r_max).astype(np.float32)  # [T_ds, r]

    out = {
        "t": t,
        "center": np.array([cx, cy], dtype=np.int32),
        "r_max": np.int32(r_max),
        "stride": np.int32(stride),
        "mean_E": mean_E,
        "std_E": std_E,
        "E_ring": E_ring,
    }

    have_J = (kJx is not None) and (kJy is not None)
    if have_J:
        Jx_ds = d[kJx][::stride].astype(np.float32, copy=False)
        Jy_ds = d[kJy][::stride].astype(np.float32, copy=False)

        Jmag = np.sqrt(Jx_ds * Jx_ds + Jy_ds * Jy_ds).astype(np.float32)
        out["mean_Jmag"] = np.mean(Jmag, axis=0, dtype=np.float64).astype(np.float32)
        out["std_Jmag"] = np.std(Jmag, axis=0, dtype=np.float64).astype(np.float32)
        out["J_ring"] = ring_means(Jmag, ridx, r_max).astype(np.float32)

        out["div_last"] = div2d(Jx_ds[-1], Jy_ds[-1]).astype(np.float32)
        out["curl_last"] = curl2d(Jx_ds[-1], Jy_ds[-1]).astype(np.float32)

        if keep_jhist:
            out["Jx_hist_ds"] = Jx_ds
            out["Jy_hist_ds"] = Jy_ds

    if keep_ehist:
        out["E_hist_ds"] = E_ds

    # storage conversion / quantization
    big_keys = []
    for k in list(out.keys()):
        if isinstance(out[k], np.ndarray) and out[k].dtype in (np.float32, np.float64, np.float16):
            big_keys.append(k)

    if dtype == "float16":
        for k in big_keys:
            if out[k].dtype == np.float32:
                out[k] = out[k].astype(np.float16)
        out["storage"] = np.array([b"float16"])
    elif dtype == "int8":
        qmeta = {}
        for k in big_keys:
            if out[k].dtype in (np.float32, np.float16):
                q, scale, zero = quantize_linear_int8(out[k].astype(np.float32), clip_sigma=clip_sigma)
                out[k] = q
                qmeta[f"{k}__scale"] = np.array([scale], dtype=np.float32)
                qmeta[f"{k}__zero"] = np.array([zero], dtype=np.float32)
        out.update(qmeta)
        out["storage"] = np.array([b"int8_linear"])
        out["clip_sigma"] = np.array([clip_sigma], dtype=np.float32)
    else:
        out["storage"] = np.array([b"float32"])

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    np.savez_compressed(out_path, **out)


# -------------------------
# batch scanning
# -------------------------
def iter_fields_npz(root: str):
    """
    Finds fields_hist_*.npz recursively under root.
    """
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn.startswith("fields_hist_") and fn.endswith(".npz"):
                yield os.path.join(dirpath, fn)


def default_out_path(npz_path: str, out_root: str | None):
    """
    If out_root is None: place near source file in sibling folder 'export'
    else: mirror relative path under out_root.
    """
    src_dir = os.path.dirname(npz_path)
    base = os.path.basename(npz_path).replace(".npz", "")

    if out_root is None:
        exp_dir = os.path.join(src_dir, "export")
        return os.path.join(exp_dir, base + "__export.npz")

    # mirror structure from input root: put file under out_root using last 3 path parts by default
    # (simple & robust; you can change if you want exact mirroring)
    parts = npz_path.replace("\\", "/").split("/")
    tail = "/".join(parts[-4:-1])  # e.g. fields/<run_id>  (or slightly above)
    exp_dir = os.path.join(out_root, tail)
    return os.path.join(exp_dir, base + "__export.npz")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True,
                    help="Root folder to scan (e.g. runs_out/Run_.../fields or runs_out)")
    ap.add_argument("--out-root", default=None,
                    help="Where to write exports. If omitted, writes to sibling 'export' near each npz.")
    ap.add_argument("--stride", type=int, default=5)
    ap.add_argument("--dtype", choices=["float16", "float32", "int8"], default="float16")
    ap.add_argument("--clip-sigma", type=float, default=4.0)
    ap.add_argument("--center", default=None, help="cx,cy (default: argmax mean(E))")
    ap.add_argument("--rmax", type=int, default=None)
    ap.add_argument("--keep-ehist", action="store_true")
    ap.add_argument("--keep-jhist", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="Process only first N files (0 = no limit)")
    args = ap.parse_args()

    root = args.root
    if not os.path.exists(root):
        print(f"[ERR] root not found: {root}", file=sys.stderr)
        sys.exit(2)

    files = list(iter_fields_npz(root))
    if not files:
        print("[WARN] no fields_hist_*.npz found under:", root)
        sys.exit(0)

    if args.limit and args.limit > 0:
        files = files[:args.limit]

    ok = 0
    bad = 0
    for p in files:
        outp = default_out_path(p, args.out_root)
        try:
            export_one(
                npz_path=p,
                out_path=outp,
                stride=args.stride,
                center=args.center,
                rmax=args.rmax,
                keep_ehist=args.keep_ehist,
                keep_jhist=args.keep_jhist,
                dtype=args.dtype,
                clip_sigma=args.clip_sigma,
            )
            ok += 1
            print(f"[OK] {p} -> {outp}")
        except Exception as e:
            bad += 1
            print(f"[FAIL] {p}: {e}", file=sys.stderr)

    print(f"[DONE] processed={len(files)} ok={ok} failed={bad}")


if __name__ == "__main__":
    main()
