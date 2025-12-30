# utils/signal.py
from __future__ import annotations
import numpy as np

# Hilbert (optional)
try:
    from scipy.signal import hilbert as _scipy_hilbert  # type: ignore
    HAS_HILBERT = True
except Exception:
    _scipy_hilbert = None
    HAS_HILBERT = False


def wrap_pi(x: np.ndarray) -> np.ndarray:
    return (x + np.pi) % (2 * np.pi) - np.pi


def _is_time_like(x: np.ndarray) -> bool:
    if x.ndim != 1 or x.size < 5:
        return False
    if not np.all(np.isfinite(x)):
        return False
    dx = np.diff(x)
    return (np.mean(dx) > 0) and (np.sum(dx <= 0) < 0.05 * dx.size)


def _smooth(sig: np.ndarray, win: int) -> np.ndarray:
    sig = sig.astype(float, copy=True)
    if not np.all(np.isfinite(sig)):
        med = np.nanmedian(sig)
        sig[~np.isfinite(sig)] = med
    w = int(max(1, win))
    if w <= 1 or w >= sig.size:
        return sig
    k = np.ones(w, dtype=float) / float(w)
    return np.convolve(sig, k, mode="same")


def _find_peaks_simple(sig: np.ndarray, min_dist: int = 1, prominence: float = 0.0) -> np.ndarray:
    n = sig.size
    if n < 3:
        return np.array([], dtype=int)
    m = (sig[1:-1] > sig[:-2]) & (sig[1:-1] >= sig[2:])
    idx = np.where(m)[0] + 1
    if idx.size == 0:
        return idx
    if prominence > 0:
        med = np.median(sig)
        idx = idx[sig[idx] >= med + prominence]
        if idx.size == 0:
            return idx
    if min_dist > 1 and idx.size > 1:
        order = np.argsort(sig[idx])[::-1]
        chosen = []
        blocked = np.zeros(n, dtype=bool)
        for k in order:
            i = int(idx[k])
            if blocked[i]:
                continue
            chosen.append(i)
            lo = max(0, i - min_dist)
            hi = min(n, i + min_dist + 1)
            blocked[lo:hi] = True
        return np.array(sorted(chosen), dtype=int)
    return idx.astype(int)


def phase_from_peaks(
    a: np.ndarray,
    t: np.ndarray | None = None,
    *,
    min_period: int = 80,
    max_period: int = 5000,
    smooth_win: int = 9,
    prominence: float = 0.0,
):
    """
    Совместимая функция.

    Допускает вызовы:
      - phase_from_peaks(sig, t, ...)
      - phase_from_peaks(t, sig, ...)  (если перепутали)
      - phase_from_peaks(sig, ...)     (тогда t = 0..len-1)

    Возвращает:
      phi: np.ndarray (wrapped)
      T_inst: np.ndarray
      peaks: list[int]
    """
    a = np.asarray(a, float).ravel()
    if t is None:
        tt = np.arange(a.size, dtype=float)
        sig = a
    else:
        t = np.asarray(t, float).ravel()
        if _is_time_like(a) and not _is_time_like(t):
            tt = a
            sig = t
        else:
            tt = t
            sig = a
        n = min(tt.size, sig.size)
        tt = tt[:n]
        sig = sig[:n]

    n = sig.size
    if n < 5:
        return None, None, []

    x = _smooth(sig, int(smooth_win))

    peaks = _find_peaks_simple(x, min_dist=int(max(1, min_period)), prominence=float(prominence))
    if peaks.size >= 2:
        d = np.diff(peaks)
        ok = (d >= int(min_period)) & (d <= int(max_period))
        keep = np.zeros(peaks.size, dtype=bool)
        keep[:-1] |= ok
        keep[1:] |= ok
        peaks = peaks[keep]

    peaks_list = [int(p) for p in peaks.tolist()]
    phi = np.full(n, np.nan, dtype=float)
    T_inst = np.full(n, np.nan, dtype=float)

    if len(peaks_list) < 2:
        return phi, T_inst, peaks_list

    for k in range(len(peaks_list) - 1):
        p0 = peaks_list[k]
        p1 = peaks_list[k + 1]
        if p1 <= p0:
            continue
        T = float(p1 - p0)
        T_inst[p0:p1 + 1] = T
        u = (np.arange(p0, p1 + 1, dtype=float) - float(p0)) / T
        phi[p0:p1 + 1] = (2.0 * np.pi) * u

    first = peaks_list[0]
    last = peaks_list[-1]
    if first > 0:
        T_inst[:first] = T_inst[first]
        phi[:first] = phi[first]
    if last < n:
        T_inst[last:] = T_inst[last]
        phi[last:] = phi[last]

    phi = wrap_pi(phi)
    return phi, T_inst, peaks_list


def local_phase_via_quadrature(sig: np.ndarray, phi_g: np.ndarray, win: int = 21):
    """
    Минимальная совместимая версия (на случай если твой старый код её ожидает).
    Возвращает: theta_last, plv, var
    """
    x = np.asarray(sig, float).ravel()
    g = np.asarray(phi_g, float).ravel()
    n = min(len(x), len(g))
    if n < max(5, win):
        return None, np.nan, np.nan
    x = x[-n:]
    g = g[-n:]

    # quadrature via finite difference (fallback if no hilbert)
    if HAS_HILBERT and _scipy_hilbert is not None:
        z = _scipy_hilbert(x)
        theta = np.angle(z)
    else:
        dx = np.gradient(x)
        theta = np.arctan2(dx, x)

    d = wrap_pi(theta - g)
    # PLV
    v = np.exp(1j * d[-win:])
    plv = float(np.abs(np.mean(v)))
    var = float(1.0 - plv)
    return float(theta[-1]), plv, var
