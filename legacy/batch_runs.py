# batch_runs.py
import os
import glob
import csv
import numpy as np
import pandas as pd
from datetime import datetime

from core.state import State
from core.engine import Engine
from core.diagnostics import Diagnostics
from core.logger import RunLogger
from config import Params, DiagCfg
#from experiments.init_patterns import init_cross

# -----------------------------
# helpers for series layout
# -----------------------------
def ensure_series_dirs(series_dir: str):
    for sub in ("timeseries", "meta", "screenshots", "fields"):
        os.makedirs(os.path.join(series_dir, sub), exist_ok=True)


def move_run_artifacts(run_dir: str, series_dir: str, run_id: str):
    ensure_series_dirs(series_dir)

    for name, sub in [
        (f"timeseries_{run_id}.csv", "timeseries"),
        (f"meta_{run_id}.json", "meta"),
    ]:
        src = os.path.join(run_dir, name)
        if os.path.exists(src):
            dst = os.path.join(series_dir, sub, name)
            if os.path.exists(dst):
                os.remove(dst)
            os.replace(src, dst)

    shots_dir = os.path.join(run_dir, "screenshots")
    if os.path.isdir(shots_dir):
        dst_dir = os.path.join(series_dir, "screenshots", run_id)
        os.makedirs(dst_dir, exist_ok=True)
        for f in glob.glob(os.path.join(shots_dir, "*.png")):
            os.replace(f, os.path.join(dst_dir, os.path.basename(f)))
    # ---- fields (npz) ----
    fields_dir = os.path.join(run_dir, "fields")
    if os.path.isdir(fields_dir):
        dst_dir = os.path.join(series_dir, "fields", run_id)
        os.makedirs(dst_dir, exist_ok=True)
        for f in glob.glob(os.path.join(fields_dir, "*.npz")):
            os.replace(f, os.path.join(dst_dir, os.path.basename(f)))


# -----------------------------
# summary writer
# -----------------------------
class SummaryWriter:
    def __init__(self, path: str):
        self.path = path
        self._file = open(path, "a", newline="", encoding="utf-8")
        self._writer = None

    def write(self, row: dict):
        if self._writer is None:
            self._writer = csv.DictWriter(self._file, fieldnames=list(row.keys()))
            if self._file.tell() == 0:
                self._writer.writeheader()
        self._writer.writerow(row)
        self._file.flush()

    def close(self):
        self._file.close()


# -----------------------------
# bundling timeseries
# -----------------------------
def bundle_series_timeseries(series_dir: str, out_name: str = "timeseries_bundle.csv") -> str:
    ts_dir = os.path.join(series_dir, "timeseries")
    paths = sorted(glob.glob(os.path.join(ts_dir, "timeseries_*.csv")))
    if not paths:
        raise FileNotFoundError(f"No timeseries found in {ts_dir}")

    frames = []
    for ordinal, p in enumerate(paths):
        df = pd.read_csv(p)

        run_id = os.path.basename(p)[len("timeseries_"):-4]
        if "run_id" not in df.columns:
            df.insert(0, "run_id", run_id)
        else:
            df["run_id"] = df["run_id"].fillna(run_id)

        if "t_rel" not in df.columns:
            t0 = float(df["t_global"].iloc[0])
            df["t_rel"] = df["t_global"] - t0

        df.insert(1, "run_ordinal", ordinal)
        frames.append(df)

    # harmonize columns
    cols = []
    for df in frames:
        for c in df.columns:
            if c not in cols:
                cols.append(c)

    for i, df in enumerate(frames):
        for c in cols:
            if c not in df.columns:
                df[c] = np.nan
        frames[i] = df[cols]

    out_path = os.path.join(series_dir, out_name)
    pd.concat(frames, ignore_index=True).to_csv(out_path, index=False)
    return out_path


def finalize_series(series_dir: str):
    try:
        out = bundle_series_timeseries(series_dir)
        print(f"[finalize] timeseries bundled → {out}")
    except Exception as e:
        print(f"[finalize] warn: {e}")


# -----------------------------
# batch runner (как было)
# -----------------------------
def run_one(
    base_dir: str,
    N: int,
    E_level: float,
    seed: int,
    max_steps: int,
    min_t: int,
    tail_steps: int,
    diag_fast: int,
    diag_slow: int,
    A_thr: float,
    A_win: int,
    T_need: int,
    T_rel_eps: float,
    backend: str = "fast",
):
    params = Params()
    diag_cfg = DiagCfg()
    diag_cfg.fast_stride = diag_fast
    diag_cfg.slow_stride = diag_slow

    run_dir = RunLogger.make_run_dir(base_dir)
    meta = dict(
        N=N,
        E_level=E_level,
        seed=seed,
        backend=backend,
        mode="batch",
    )
    logger = RunLogger(run_dir, meta=meta)
    # В batch лучше реже, чтобы не раздувать размер
    logger.enable_E_history(stride=max(1, int(min(diag_fast, diag_slow))), dtype="float32")

    logger.enable_field_history(fields=("E", "Jx", "Jy", "tau"), stride=max(1, int(min(diag_fast, diag_slow))), dtype="float32")
    class TorchToNumpyMirror:
        def __init__(self, torch_model, st_np, stride=10):
            self.inner = torch_model
            self.stride = stride
            self._k = 0
            self.st = st_np  # чтобы Engine/Visualizer/Logger обращались к .st как обычно
            self._st_t = torch_model.st

        def _sync(self):
            from core.model_torch import torch
            st_t = self._st_t

            self.st.E[:] = st_t.E.detach().to("cpu", dtype=torch.float32).numpy()
            self.st.S[:] = st_t.S.detach().to("cpu", dtype=torch.float32).numpy()
            self.st.Jx[:] = st_t.Jx.detach().to("cpu", dtype=torch.float32).numpy()
            self.st.Jy[:] = st_t.Jy.detach().to("cpu", dtype=torch.float32).numpy()
            self.st.tau[:] = st_t.tau.detach().to("cpu", dtype=torch.float32).numpy()

            self.st.mu_bar = float(getattr(st_t, "mu_bar", 0.0))
            self.st.t_global = float(getattr(st_t, "t_global", 0.0))

        def sync(self):
            self._sync()

        def step(self):
            self.inner.step()
            self._k += 1
            if self._k % self.stride == 0:
                self._sync()

        # --- backend selection ---
    # if backend == "fast":
    #     from core.model_fast import ModelFast as ModelImpl
    #
    #     st = State(N=N, E_level=E_level, seed=seed)
    #     init_cross(st.E, strength=0.3, noise=0.05)
    #     model = ModelImpl(st, params)
    #
    # elif backend == "torch":
    #     # 1) numpy-state for Diagnostics/Logger compatibility
    #     st_np = State(N=N, E_level=E_level, seed=seed)
    #     init_cross(st_np.E, strength=0.3, noise=0.05)
    #     # 2) torch-state + torch-model for fast stepping
    #     from core.state_torch import TorchState
    #     from core.model_torch import ModelTorchFast as TorchModel
    #     from core.model_torch import require_torch, torch
    #
    #     require_torch()
    #     device = "cuda" if torch.cuda.is_available() else "cpu"
    #
    #     st_t = TorchState(N=N, E_level=E_level, seed=seed, device=device)
    #     torch_model = TorchModel(st_t, params)
    #
    #     # 3) wrap torch model so Engine sees numpy-state
    #     model = TorchToNumpyMirror(torch_model, st_np, stride=min(diag_fast, diag_slow))
    #     st = st_np
    #
    #     # (optional) initial sync so t=0 diagnostics sees correct tensors
    #     model._sync()
    #
    # else:
    #     from core.model import Model as ModelImpl
    #
    #     st = State(N=N, E_level=E_level, seed=seed)
    #     model = ModelImpl(st, params)
    # --- backend selection ---
    if backend == "fast":
        from core.model_fast import ModelFast as ModelImpl

        st = State(N=N, E_level=E_level, seed=seed)
        init_cross(st.E, strength=0.3, noise=0.05)
        model = ModelImpl(st, params)

    elif backend == "torch":
        # 1) numpy-state for Diagnostics/Logger compatibility
        st_np = State(N=N, E_level=E_level, seed=seed)
        init_cross(st_np.E, strength=0.3, noise=0.05)


        # 2) torch-state + torch-model
        from core.state_torch import TorchState
        from core.model_torch import ModelTorchFast as TorchModel
        from core.model_torch import require_torch, torch

        require_torch()
        device = "cuda" if torch.cuda.is_available() else "cpu"

        st_t = TorchState(N=N, E_level=E_level, seed=seed, device=device)
        print("AFTER INIT", st.E.min(), st.E.max(), st.E.mean(), st.E.std())

        # ✅ СИНХРОНИЗИРУЕМ НАЧАЛЬНОЕ СОСТОЯНИЕ: numpy -> torch
        st_t.E[:] = torch.tensor(st_np.E, device=device, dtype=st_t.E.dtype)

        torch_model = TorchModel(st_t, params)

        # 3) wrap torch model so Engine sees numpy-state
        mirror_stride = 1  # ✅ для эксперимента: чтобы каждый тик писал реальную динамику
        model = TorchToNumpyMirror(torch_model, st_np, stride=mirror_stride)
        model._sync()
        st = st_np

        # initial sync so logs at t=0 are consistent


    else:
        from core.model import Model as ModelImpl

        st = State(N=N, E_level=E_level, seed=seed)
        init_cross(st.E, strength=0.3, noise=0.05)  # ✅ добавили
        model = ModelImpl(st, params)
    diag = Diagnostics(st, diag_cfg, logger=logger)
    engine = Engine(model, diag, viz=None, logger=logger)
    logger.record_fields_from_state(st)  # снимок t=0
    engine.run(max_steps=max_steps)

    # simple stability extract (как было)
    stable_at = None
    reason = "done"

    return run_dir, logger.run_id, stable_at, None, None, None, reason
