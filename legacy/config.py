# config.py
from dataclasses import dataclass

@dataclass
class Params:
    kappa: float = 0.1
    alpha: float = 0.3
    beta: float = 1.0
    gamma: float = 0.1
    lambda_t: float = 1.0

@dataclass
class DiagCfg:
    W: int = 700
    Wmin: int = 250
    use_hilbert: bool = True

    line_top_p: float = 0.01
    line_delta: float | None = None

    band_offset: int = 2
    band_width: int = 6

    probe_step: int = 3
    probe_x_from: int = 4
    probe_x_to: int = 40

    anchors_K: int = 12
    plv_every: int = 8

    freeze_thr: float = 0.05
    log_every: int = 1
    # ---- Peak-based phase (no scipy) ----
    peak_smooth_win: int = 9        # сглаживание A(t) перед поиском пиков
    peak_min_period: int = 80       # минимальный период в "тиках" t_global
    peak_max_period: int = 5000     # максимальный период в "тиках"
    peak_prominence: float = 0.0    # можно поднять, если пики шумные (например 0.02)

    # ---- Quadrature for probes ----
    quad_win: int = 21              # окно сглаживания I/Q (должно быть меньше ожидаемого периода)
    plv_thr: float = 0.7

    # ---- A3: radial coherence profile ----
    a3_every: int = 10         # как часто пересчитывать профиль (в кадрах диагностики)
    a3_bins: int = 14          # число радиальных бинов
    a3_rmax: float = 45.0      # максимальный радиус (в клетках)
    a3_min_per_bin: int = 6    # минимум проб в бине, иначе bin = nan
@dataclass
class VizCfg:
    quiver_step: int = 3
    quiver_scale: float = 30.0
    auto_clim: bool = True
    hist_bins: int = 1
    show_quiver: bool = True
