"""Boundary-flux diagnostics for DETM runs (`fields_hist.npz`).

This utility is meant to test/operationalize the "fixed point on the boundary"
idea: measure not the full field, but boundary/transfer readouts and their
time-series structure (spectrum, correlation time, phase locking).

Input
-----
`--npz` must point to a `fields_hist.npz` produced by the recorder. Expected keys:
- `t` (optional): 1D time axis
- `E_hist`: (T, N, N) energy history
- `Jx_hist`, `Jy_hist` (optional): (T, N, N) flow components (see `detm.analysis.fields`)

Mask
----
If a binary region mask is available inside the same NPZ (e.g. `marker_mask` from
`experiments/marker_protocol.py`), the tool can compute boundary flux across the
interface between the region and its complement.

Without a mask, the tool falls back to the full-domain outer boundary.

Output
------
Writes `boundary_flux.csv` + `summary.json` and, if matplotlib is available,
PNG plots (timeseries/spectrum/acf) into `--out`.
"""

from __future__ import annotations

import argparse
import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np


def _require_matplotlib():
    try:
        import matplotlib.pyplot as plt  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("matplotlib is required for plotting (pip install matplotlib)") from exc
    return plt


def _wrap_pi(x: np.ndarray) -> np.ndarray:
    return (x + np.pi) % (2.0 * np.pi) - np.pi


def _dominant_frequency(x: np.ndarray, dt: float) -> Tuple[float, float]:
    x = np.asarray(x, dtype=float).ravel()
    if x.size < 4:
        return 0.0, 0.0
    x = x - float(x.mean())
    spec = np.fft.rfft(x)
    power = spec.real**2 + spec.imag**2
    if power.shape[0] <= 1:
        return 0.0, 0.0
    idx = 1 + int(np.argmax(power[1:]))
    freqs = np.fft.rfftfreq(x.size, d=dt)
    return float(freqs[idx]), float(power[idx])


def _spectral_entropy(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=float).ravel()
    if x.size < 4:
        return 0.0
    x = x - float(x.mean())
    spec = np.fft.rfft(x)
    power = spec.real**2 + spec.imag**2
    if power.shape[0] <= 2:
        return 0.0
    p = power[1:]  # drop DC
    s = float(p.sum())
    if not np.isfinite(s) or s <= 0.0:
        return 0.0
    p = p / s
    # normalized Shannon entropy in [0,1]
    h = -float(np.sum(p * np.log(p + 1e-12)))
    h_norm = h / math.log(p.size)
    return float(np.clip(h_norm, 0.0, 1.0))


def _autocorr(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float).ravel()
    if x.size < 4:
        return np.asarray([], dtype=float)
    x = x - float(x.mean())
    denom = float(np.dot(x, x))
    if denom <= 0.0 or not np.isfinite(denom):
        return np.zeros((x.size,), dtype=float)
    r = np.correlate(x, x, mode="full")[x.size - 1 :]
    return r / denom


def _corr_time(acf: np.ndarray, threshold: float = 1.0 / math.e) -> int:
    if acf.size == 0:
        return 0
    for lag in range(1, acf.size):
        if not np.isfinite(acf[lag]):
            continue
        if acf[lag] < threshold:
            return lag
    return int(acf.size - 1)


def _phase_quadrature(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float).ravel()
    if x.size < 4:
        return np.asarray([], dtype=float)
    dx = np.gradient(x)
    theta = np.arctan2(dx, x)
    return _wrap_pi(theta)


def _plv(phi_a: np.ndarray, phi_b: np.ndarray, win: int) -> float:
    if phi_a.size == 0 or phi_b.size == 0:
        return float("nan")
    n = min(phi_a.size, phi_b.size)
    if n < max(5, win):
        return float("nan")
    d = _wrap_pi(phi_a[-n:] - phi_b[-n:])
    v = np.exp(1j * d[-win:])
    return float(np.abs(np.mean(v)))


@dataclass(frozen=True)
class BoundaryEdges:
    """Edge masks *on inside cells* for the interface between inside/outside.

    Conventions follow `detm.analysis.fields`:
    - axis=0 is "x" direction for `Jx`
    - axis=1 is "y" direction for `Jy`
    """

    x_plus: np.ndarray
    x_minus: np.ndarray
    y_plus: np.ndarray
    y_minus: np.ndarray

    @property
    def edge_count(self) -> int:
        return int(self.x_plus.sum() + self.x_minus.sum() + self.y_plus.sum() + self.y_minus.sum())


def _edges_from_mask(mask: np.ndarray) -> BoundaryEdges:
    inside = np.asarray(mask, dtype=bool)
    if inside.ndim != 2:
        raise ValueError("mask must be a 2D array")

    # interface between inside and outside; masks live on the inside side
    x_plus = inside & (~np.roll(inside, -1, axis=0))
    x_minus = inside & (~np.roll(inside, +1, axis=0))
    y_plus = inside & (~np.roll(inside, -1, axis=1))
    y_minus = inside & (~np.roll(inside, +1, axis=1))
    return BoundaryEdges(x_plus=x_plus, x_minus=x_minus, y_plus=y_plus, y_minus=y_minus)


def _edges_for_outer_boundary(shape: Tuple[int, int]) -> BoundaryEdges:
    n0, n1 = shape
    inside = np.ones((n0, n1), dtype=bool)

    x_plus = np.zeros_like(inside)
    x_minus = np.zeros_like(inside)
    y_plus = np.zeros_like(inside)
    y_minus = np.zeros_like(inside)

    x_minus[0, :] = True
    x_plus[-1, :] = True
    y_minus[:, 0] = True
    y_plus[:, -1] = True

    return BoundaryEdges(x_plus=x_plus, x_minus=x_minus, y_plus=y_plus, y_minus=y_minus)


def _flux_timeseries(Jx_hist: np.ndarray, Jy_hist: np.ndarray, edges: BoundaryEdges) -> Tuple[np.ndarray, np.ndarray]:
    """Return (net_outward_flux, throughput_abs) time series."""

    Jx_hist = np.asarray(Jx_hist, dtype=float)
    Jy_hist = np.asarray(Jy_hist, dtype=float)
    if Jx_hist.shape != Jy_hist.shape:
        raise ValueError("Jx_hist and Jy_hist must have the same shape")
    if Jx_hist.ndim != 3:
        raise ValueError("expected flow histories with shape (T,N,N)")

    x_plus = edges.x_plus[None, :, :]
    x_minus = edges.x_minus[None, :, :]
    y_plus = edges.y_plus[None, :, :]
    y_minus = edges.y_minus[None, :, :]

    # signed net outward flux
    net = (
        (Jx_hist * x_plus).sum(axis=(1, 2))
        + (-Jx_hist * x_minus).sum(axis=(1, 2))
        + (Jy_hist * y_plus).sum(axis=(1, 2))
        + (-Jy_hist * y_minus).sum(axis=(1, 2))
    )

    # absolute "throughput"
    thr = (
        (np.abs(Jx_hist) * x_plus).sum(axis=(1, 2))
        + (np.abs(Jx_hist) * x_minus).sum(axis=(1, 2))
        + (np.abs(Jy_hist) * y_plus).sum(axis=(1, 2))
        + (np.abs(Jy_hist) * y_minus).sum(axis=(1, 2))
    )
    return net.astype(float, copy=False), thr.astype(float, copy=False)


def _write_csv(
    out_csv: Path,
    t: np.ndarray,
    energy_mean: np.ndarray,
    phi_net: np.ndarray,
    phi_thr: np.ndarray,
    phi_phase: np.ndarray,
    e_phase: np.ndarray,
) -> None:
    out_csv.write_text(
        "step,t,energy_mean,phi_net,phi_throughput,phi_phase,energy_phase\n"
        + "\n".join(
            f"{i},{float(t[i])},{float(energy_mean[i])},{float(phi_net[i])},{float(phi_thr[i])},"
            f"{float(phi_phase[i]) if i < phi_phase.size else ''},{float(e_phase[i]) if i < e_phase.size else ''}"
            for i in range(t.size)
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:  # pragma: no cover (CLI)
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--npz", required=True, help="Path to fields_hist.npz")
    ap.add_argument(
        "--mask-key",
        default=None,
        help="Optional key in the NPZ with a 2D binary mask (e.g. marker_mask)",
    )
    ap.add_argument("--out", default=None, help="Output dir (default: sibling boundary_flux)")
    ap.add_argument("--plv-window", type=int, default=64, help="Window (in steps) for PLV estimate")
    ap.add_argument("--no-plots", action="store_true", help="Skip matplotlib plots")
    args = ap.parse_args()

    data = np.load(args.npz)
    E_hist = data.get("E_hist", None)
    if E_hist is None:
        raise RuntimeError("E_hist not found in npz.")
    E_hist = np.asarray(E_hist, dtype=float)
    if E_hist.ndim != 3:
        raise RuntimeError("E_hist must have shape (T,N,N).")

    t = data.get("t", None)
    if t is None or (not np.isfinite(np.asarray(t)).any()):
        t = np.arange(E_hist.shape[0], dtype=float)
    else:
        t = np.asarray(t, dtype=float).reshape(-1)

    T = int(E_hist.shape[0])
    t = t[:T]
    dt = float(np.median(np.diff(t))) if t.size >= 2 else 1.0
    if not np.isfinite(dt) or dt <= 0.0:
        dt = 1.0

    energy_mean = E_hist.mean(axis=(1, 2), dtype=np.float64)

    mask = None
    if args.mask_key is not None:
        mask = data.get(args.mask_key, None)
        if mask is None:
            raise RuntimeError(f"mask key not found in npz: {args.mask_key!r}")
        mask = np.asarray(mask).astype(bool)
        if mask.ndim != 2:
            raise RuntimeError("mask must be 2D")

    Jx_hist = data.get("Jx_hist", None)
    Jy_hist = data.get("Jy_hist", None)
    if Jx_hist is None or Jy_hist is None:
        raise RuntimeError("Jx_hist/Jy_hist not found in npz (need flow history to compute boundary flux).")

    Jx_hist = np.asarray(Jx_hist, dtype=float)[:T]
    Jy_hist = np.asarray(Jy_hist, dtype=float)[:T]

    if mask is None:
        edges = _edges_for_outer_boundary((E_hist.shape[1], E_hist.shape[2]))
        mask_label = "outer_boundary"
    else:
        edges = _edges_from_mask(mask)
        mask_label = args.mask_key

    phi_net, phi_thr = _flux_timeseries(Jx_hist, Jy_hist, edges)
    phi_phase = _phase_quadrature(phi_thr)
    e_phase = _phase_quadrature(energy_mean)
    plv_val = _plv(phi_phase, e_phase, win=int(args.plv_window))

    acf = _autocorr(phi_thr)
    tau_corr_steps = _corr_time(acf)
    f_dom, p_dom = _dominant_frequency(phi_thr, dt=dt)
    h_spec = _spectral_entropy(phi_thr)

    out_dir = args.out or os.path.join(os.path.dirname(args.npz), "boundary_flux")
    os.makedirs(out_dir, exist_ok=True)

    out_csv = Path(out_dir) / "boundary_flux.csv"
    _write_csv(out_csv, t=t, energy_mean=energy_mean, phi_net=phi_net, phi_thr=phi_thr, phi_phase=phi_phase, e_phase=e_phase)

    summary: Dict[str, Any] = {
        "npz": str(Path(args.npz).resolve()),
        "mask": mask_label,
        "T": T,
        "dt": dt,
        "edge_count": edges.edge_count,
        "phi_thr_mean": float(np.mean(phi_thr)),
        "phi_thr_std": float(np.std(phi_thr)),
        "phi_thr_spectral_entropy": float(h_spec),
        "phi_thr_dominant_frequency": float(f_dom),
        "phi_thr_dominant_period": (float(1.0 / f_dom) if f_dom > 0 else 0.0),
        "phi_thr_dominant_power": float(p_dom),
        "phi_thr_corr_time_steps": int(tau_corr_steps),
        "phi_thr_corr_time": float(tau_corr_steps * dt),
        "plv(phi_thr,energy_mean)": float(plv_val),
        "csv": str(out_csv.resolve()),
    }
    (Path(out_dir) / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    if not args.no_plots:
        try:
            plt = _require_matplotlib()
            fig = plt.figure(figsize=(12, 8))
            ax1 = fig.add_subplot(3, 1, 1)
            ax1.plot(t, energy_mean, label="E_mean(t)")
            ax1.set_title("Energy mean")
            ax1.grid(True, alpha=0.3)

            ax2 = fig.add_subplot(3, 1, 2, sharex=ax1)
            ax2.plot(t, phi_thr, label="Φ_boundary throughput(t)")
            ax2.set_title("Boundary throughput (abs flux)")
            ax2.grid(True, alpha=0.3)

            ax3 = fig.add_subplot(3, 1, 3)
            ax3.plot(np.arange(acf.size) * dt, acf, label="ACF(Φ)")
            ax3.axhline(1.0 / math.e, color="k", lw=1, alpha=0.4)
            ax3.axvline(tau_corr_steps * dt, color="r", lw=1, alpha=0.6, label="τ_corr")
            ax3.set_title("Autocorrelation")
            ax3.grid(True, alpha=0.3)
            ax3.legend(loc="best")

            fig.tight_layout()
            fig.savefig(Path(out_dir) / "timeseries.png", dpi=160)
            plt.close(fig)

            # spectrum
            x = phi_thr - float(phi_thr.mean())
            spec = np.fft.rfft(x)
            power = spec.real**2 + spec.imag**2
            freqs = np.fft.rfftfreq(x.size, d=dt)
            fig = plt.figure(figsize=(12, 4))
            ax = fig.add_subplot(1, 1, 1)
            ax.plot(freqs[1:], power[1:])
            ax.set_title("Spectrum |rFFT(Φ)|^2 (no DC)")
            ax.set_xlabel("frequency")
            ax.set_ylabel("power")
            ax.grid(True, alpha=0.3)
            fig.tight_layout()
            fig.savefig(Path(out_dir) / "spectrum.png", dpi=160)
            plt.close(fig)
        except Exception:
            pass

    print("[OK] wrote:", out_dir)
    print("[OK] summary:", summary)


if __name__ == "__main__":
    main()
