# main.py
import os
import argparse
from datetime import datetime

from config import Params, DiagCfg, VizCfg
from core.state import State
from core.diagnostics import Diagnostics
from core.logger import RunLogger
from core.engine import Engine
from viz.visualizer import Visualizer
#from experiments.init_patterns import init_cross, init_circle

import batch_runs


# -----------------------------
# defaults
# -----------------------------
DEFAULT_VIZ = dict(
    N=15,
    E_level=0.6,
    seed=None,
    interval_ms=1,
    backend="torch",
)


def default_out_root():
    return os.path.join(os.path.dirname(__file__), "../../LMU/runs_out")


# -----------------------------
# viz
# -----------------------------
def cmd_viz(args):
    series_dir = os.path.join(
        args.out_root,
        args.series or datetime.now().strftime("Run_%Y%m%d_%H%M%S"),
    )
    batch_runs.ensure_series_dirs(series_dir)

    run_dir = RunLogger.make_run_dir(series_dir)

    params = Params()
    diag_cfg = DiagCfg()
    viz_cfg = VizCfg()

    meta = dict(mode="viz", N=args.N, seed=args.seed)
    logger = RunLogger(run_dir, meta=meta)
    # логируем поле E раз в 10 тиков (можно менять)
    #logger.enable_E_history(stride=10, dtype="float32")
    backend = getattr(args, "backend", "torch")
    logger.enable_field_history(fields=("E", "Jx", "Jy", "tau"), stride=1, dtype="float32")
    if backend == "torch":
        # numpy mirror for viz+diagnostics
        st_np = State(N=args.N, E_level=args.E_level, seed=args.seed)
        #init_cross(st_np.E, strength=0.9, noise=0.67)
        from core.model_torch import require_torch, torch
        from core.state_torch import TorchState
        from core.model_torch import ModelTorchFast as TorchModel

        require_torch()
        device = "cuda" if torch.cuda.is_available() else "cpu"

        st_t = TorchState(N=args.N, E_level=args.E_level, seed=args.seed, device=device)

        torch_model = TorchModel(st_t, params)

        # Mirror wrapper: sync each *frame*, not each tick (см. Engine правку ниже)
        class TorchToNumpyMirror:
            def __init__(self, inner, st_np):
                self.inner = inner
                self.st = st_np
                self._st_t = inner.st

            def step(self):
                self.inner.step()

            def sync(self):
                # called by Engine once per frame (после пакета шагов)
                st_t = self._st_t
                # переносим то, что нужно viz/diag
                self.st.E[:] = st_t.E.detach().to("cpu", dtype=torch.float32).numpy()
                self.st.S[:] = st_t.S.detach().to("cpu", dtype=torch.float32).numpy()
                self.st.Jx[:] = st_t.Jx.detach().to("cpu", dtype=torch.float32).numpy()
                self.st.Jy[:] = st_t.Jy.detach().to("cpu", dtype=torch.float32).numpy()
                self.st.tau[:] = st_t.tau.detach().to("cpu", dtype=torch.float32).numpy()
                self.st.mu_bar = float(getattr(st_t, "mu_bar", 0.0))
                self.st.t_global = float(getattr(st_t, "t_global", 0.0))

        model = TorchToNumpyMirror(torch_model, st_np)
        st = st_np
        # первичная синхронизация
        model.sync()

    elif backend == "fast":
        from core.model_fast import ModelFast
        st = State(N=args.N, E_level=args.E_level, seed=args.seed)
        model = ModelFast(st, params)

    else:
        from core.model import Model
        st = State(N=args.N, E_level=args.E_level, seed=args.seed)
        model = Model(st, params)

    diag = Diagnostics(st, diag_cfg, logger=logger)
    viz = Visualizer(st, diag, viz_cfg, diag_cfg)

    engine = Engine(model, diag, viz, logger=logger, interval_ms=args.interval_ms)
    engine.run()

    batch_runs.move_run_artifacts(run_dir, series_dir, logger.run_id)

    # summary (1 строка)
    sw = batch_runs.SummaryWriter(os.path.join(series_dir, "summary.csv"))
    sw.write(dict(run_id=logger.run_id, N=args.N, seed=args.seed, mode="viz"))
    sw.close()

    batch_runs.finalize_series(series_dir)


# -----------------------------
# batch
# -----------------------------

def get_batch_config(args):
    import json

    # load defaults from config if exists
    cfg_path = getattr(args, "config", None)
    cfg = {}
    if cfg_path and os.path.exists(cfg_path):
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

    def pick(name, default=None):
        v = getattr(args, name, None)
        if v is None:
            return cfg.get(name, default)
        # special: empty list -> take from cfg
        if isinstance(v, list) and len(v) == 0:
            return cfg.get(name, default)
        return v

    args.Ns = pick("Ns", [25])
    args.runs_per_N = pick("runs_per_N", 3)
    args.E_level = pick("E_level", 0.2)
    args.seed0 = pick("seed0", 0)

    args.max_steps = pick("max_steps", 8000)
    args.min_t = pick("min_t", 1200)
    args.tail = pick("tail", 2000)

    args.diag_fast = pick("diag_fast", 8)
    args.diag_slow = pick("diag_slow", 2)

    args.A_thr = pick("A_thr", 0.05)
    args.A_win = pick("A_win", 200)
    args.T_need = pick("T_need", 12)
    args.T_rel_eps = pick("T_rel_eps", 0.05)

    args.backend = pick("backend", "fast")
def cmd_batch(args):
    get_batch_config(args)

    series_dir = os.path.join(
        args.out_root,
        args.series or datetime.now().strftime("Run_%Y%m%d_%H%M%S"),
    )
    batch_runs.ensure_series_dirs(series_dir)

    summary = batch_runs.SummaryWriter(os.path.join(series_dir, "summary.csv"))

    for N in args.Ns:
        for r in range(args.runs_per_N):
            seed = args.seed0 + N * 1000 + r

            run_dir, run_id, *_ = batch_runs.run_one(
                base_dir=series_dir,
                N=N,
                E_level=args.E_level,
                seed=seed,
                max_steps=args.max_steps,
                min_t=args.min_t,
                tail_steps=args.tail,
                diag_fast=args.diag_fast,
                diag_slow=args.diag_slow,
                A_thr=args.A_thr,
                A_win=args.A_win,
                T_need=args.T_need,
                T_rel_eps=args.T_rel_eps,
                backend=args.backend,
            )

            batch_runs.move_run_artifacts(run_dir, series_dir, run_id)
            summary.write(dict(run_id=run_id, N=N, seed=seed, mode="batch"))

    summary.close()
    batch_runs.finalize_series(series_dir)


# -----------------------------
# CLI
# -----------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-root", default=default_out_root())
    ap.add_argument("--series", default=None)

    sub = ap.add_subparsers(dest="cmd")

    ap_v = sub.add_parser("viz")
    ap_v.add_argument("--N", type=int, default=DEFAULT_VIZ["N"])
    ap_v.add_argument("--E-level", type=float, default=DEFAULT_VIZ["E_level"])
    ap_v.add_argument("--seed", type=int, default=DEFAULT_VIZ["seed"])
    ap_v.add_argument("--interval-ms", type=int, default=DEFAULT_VIZ["interval_ms"])
    ap_v.add_argument("--backend", default=DEFAULT_VIZ.get("backend", "torch"), choices=["torch", "fast", "slow"])
    ap_v.set_defaults(func=cmd_viz)

    ap_b = sub.add_parser("batch")
    ap_b.add_argument("--config", default="batch_config.json")
    ap_b.add_argument("--Ns", nargs="*", type=int, default=None)
    ap_b.add_argument("--runs-per-N", type=int, default=3)
    ap_b.add_argument("--E-level", type=float, default=0.2)
    ap_b.add_argument("--seed0", type=int, default=0)
    ap_b.add_argument("--max-steps", type=int, default=8000)
    ap_b.add_argument("--min-t", type=int, default=1200)
    ap_b.add_argument("--tail", type=int, default=2000)
    ap_b.add_argument("--diag-fast", type=int, default=8)
    ap_b.add_argument("--diag-slow", type=int, default=2)
    ap_b.add_argument("--A-thr", type=float, default=0.05)
    ap_b.add_argument("--A-win", type=int, default=200)
    ap_b.add_argument("--T-need", type=int, default=12)
    ap_b.add_argument("--T-rel-eps", type=float, default=0.05)
    ap_b.add_argument("--backend", default=None)
    ap_b.set_defaults(func=cmd_batch)

    args = ap.parse_args()

    if args.cmd is None:
        # emulate: python main.py viz --defaults
        args.cmd = "viz"
        args.func = cmd_viz

        args.N = DEFAULT_VIZ["N"]
        args.E_level = DEFAULT_VIZ["E_level"]
        args.seed = DEFAULT_VIZ["seed"]
        args.interval_ms = DEFAULT_VIZ["interval_ms"]

    args.func(args)


if __name__ == "__main__":
    main()
