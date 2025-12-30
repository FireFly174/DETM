# utils/geometry.py
import numpy as np

def detect_line(E, E_level, p_top=0.01, delta=None):
    if delta is not None:
        thr = E_level + delta
    else:
        thr = np.quantile(E, 1.0 - p_top)
    mask = E > thr
    if not np.any(mask):
        return mask, None
    xs = np.arange(E.shape[1])[None, :]
    w = E * mask
    x_line = (w * xs).sum() / (w.sum() + 1e-12)
    return mask, int(round(x_line))

def band_right_slice(N, x_line, offset=2, width=6):
    if x_line is None:
        return slice(0, 0)
    x0 = min(max(x_line + offset, 0), N - 1)
    x1 = min(max(x0 + width, 0), N)
    return slice(x0, x1)
