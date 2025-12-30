#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import glob
import os
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict

import numpy as np
import pandas as pd


@dataclass
class RunPlan:
    path: str
    run_id: str
    n_rows: int
    avg_row_bytes: int


def _infer_run_id(path: str, df: pd.DataFrame) -> str:
    # 1) try column run_id
    if "run_id" in df.columns and df["run_id"].notna().any():
        v = df["run_id"].dropna().astype(str).iloc[0]
        if v:
            return v
    # 2) try filename timeseries_<runid>.csv
    base = os.path.basename(path)
    if base.startswith("timeseries_") and base.lower().endswith(".csv"):
        mid = base[len("timeseries_"):-len(".csv")]
        if mid:
            return mid
    # 3) fallback: basename without ext
    return os.path.splitext(base)[0]


def _estimate_avg_row_bytes(path: str, sample_rows: int = 300) -> int:
    # Read small sample and estimate bytes per row when written as CSV
    df = pd.read_csv(path, nrows=sample_rows)
    if df.empty:
        return 200  # arbitrary
    s = df.to_csv(index=False)
    # Rough: total bytes / rows (including header). Add small safety.
    bpr = max(50, int(len(s.encode("utf-8")) / max(1, len(df))) + 10)
    return bpr


def _count_rows_fast(path: str) -> int:
    # Fast line count without loading whole CSV
    # subtract header line if present
    with open(path, "rb") as f:
        n = sum(1 for _ in f)
    return max(0, n - 1)


def _pick_event_indices(df: pd.DataFrame) -> np.ndarray:
    """
    Событийные точки, если соответствующие колонки существуют.
    Возвращает массив индексов (позиции строк), которые важно сохранить.
    """
    idx = set()

    n = len(df)
    if n == 0:
        return np.array([], dtype=int)

    # Always keep first/last
    idx.add(0)
    idx.add(n - 1)

    # x_line change points
    if "x_line" in df.columns:
        x = df["x_line"].to_numpy()
        # treat -1 / NaN as missing
        x2 = np.copy(x)
        # mark changes
        ch = np.where(np.diff(x2, prepend=x2[0]) != 0)[0]
        for i in ch:
            idx.add(int(i))
            if i > 0:
                idx.add(int(i - 1))
            if i < n - 1:
                idx.add(int(i + 1))

    # Peaks of A (keep top K peaks by prominence-ish)
    if "A" in df.columns:
        A = df["A"].to_numpy(dtype=float)
        if np.isfinite(A).any():
            # local maxima: A[i-1] < A[i] >= A[i+1]
            m = np.zeros(n, dtype=bool)
            m[1:-1] = (A[1:-1] > A[:-2]) & (A[1:-1] >= A[2:])
            peak_idx = np.where(m)[0]
            if len(peak_idx) > 0:
                # rank by amplitude, keep up to 60
                K = min(60, len(peak_idx))
                top = peak_idx[np.argsort(A[peak_idx])[-K:]]
                for i in top:
                    idx.add(int(i))

    # Big jumps in T (period changes)
    if "T" in df.columns:
        T = df["T"].to_numpy(dtype=float)
        # ignore NaN
        if np.isfinite(T).any():
            Tn = np.copy(T)
            # forward-fill NaN for diff detection
            mask = np.isfinite(Tn)
            if mask.any():
                last = Tn[mask][0]
                for i in range(n):
                    if np.isfinite(Tn[i]):
                        last = Tn[i]
                    else:
                        Tn[i] = last
                d = np.abs(np.diff(Tn, prepend=Tn[0]))
                # keep top jump points
                K = min(40, n)
                top = np.argsort(d)[-K:]
                for i in top:
                    idx.add(int(i))

    # Max |dE_obj| events
    if "E_obj" in df.columns:
        Eo = df["E_obj"].to_numpy(dtype=float)
        if np.isfinite(Eo).any():
            d = np.abs(np.diff(Eo, prepend=Eo[0]))
            K = min(40, n)
            top = np.argsort(d)[-K:]
            for i in top:
                idx.add(int(i))

    return np.array(sorted(idx), dtype=int)


def _uniform_indices(n: int, k: int) -> np.ndarray:
    if n <= 0:
        return np.array([], dtype=int)
    if k >= n:
        return np.arange(n, dtype=int)
    # evenly spaced incl endpoints
    return np.unique(np.linspace(0, n - 1, k, dtype=int))


def compress_timeseries(
    df: pd.DataFrame,
    target_rows: int,
    min_uniform_rows: int = 80,
) -> pd.DataFrame:
    """
    Сжатие:
    - сохраняем событийные точки
    - добавляем равномерную сетку по времени
    - если всё ещё слишком много — уплотняем равномерную часть, но события оставляем
    """
    n = len(df)
    if n == 0:
        return df

    target_rows = max(10, int(target_rows))

    ev = _pick_event_indices(df)
    # Uniform backbone
    uni = _uniform_indices(n, max(min_uniform_rows, target_rows // 2))
    keep = np.unique(np.concatenate([ev, uni]))

    if len(keep) > target_rows:
        # Keep all events, and sample remaining uniformly from non-event indices
        ev_set = set(map(int, ev.tolist()))
        non_ev = np.array([i for i in keep if int(i) not in ev_set], dtype=int)

        # budget for non-events
        budget = max(0, target_rows - len(ev_set))
        if budget <= 0:
            keep2 = np.array(sorted(ev_set), dtype=int)
        else:
            sampled = _uniform_indices(len(non_ev), budget)
            keep2 = np.unique(np.concatenate([np.array(sorted(ev_set), dtype=int), non_ev[sampled]]))
        keep = keep2

    out = df.iloc[keep].copy()

    # Ensure time-ordered by t_rel if present, else index
    if "t_rel" in out.columns:
        out = out.sort_values("t_rel", kind="mergesort")
    else:
        out = out.sort_index(kind="mergesort")

    out.reset_index(drop=True, inplace=True)
    return out


def plan_all_runs(paths: List[str]) -> List[RunPlan]:
    plans: List[RunPlan] = []
    for p in paths:
        n_rows = _count_rows_fast(p)
        avg_b = _estimate_avg_row_bytes(p)
        # read tiny to infer run_id
        df0 = pd.read_csv(p, nrows=5)
        run_id = _infer_run_id(p, df0)
        plans.append(RunPlan(path=p, run_id=run_id, n_rows=n_rows, avg_row_bytes=avg_b))
    return plans


def bundle(
    paths: List[str],
    out_prefix: str,
    max_mb: int,
    min_rows_per_run: int,
    reserve_mb: int = 1,
) -> List[str]:
    """
    Собирает в bundle_partXX.csv, ограничивая размер каждого файла.
    """
    max_bytes = max_mb * 1024 * 1024
    reserve_bytes = reserve_mb * 1024 * 1024
    limit = max(1_000_000, max_bytes - reserve_bytes)

    plans = plan_all_runs(paths)

    # approximate: allocate rows per run proportional to length, based on total budget
    # budget in rows = limit / avg_row_bytes (use median to be robust)
    med_bpr = int(np.median([p.avg_row_bytes for p in plans])) if plans else 200
    total_budget_rows = max(100, int(limit / max(50, med_bpr)))

    total_rows = sum(p.n_rows for p in plans) or 1

    allocations: Dict[str, int] = {}
    for p in plans:
        # proportional allocation, but at least min_rows_per_run
        k = int(total_budget_rows * (p.n_rows / total_rows))
        k = max(min_rows_per_run, k)
        allocations[p.run_id] = k

    # Output parts
    out_files: List[str] = []
    part_idx = 1
    current_path = f"{out_prefix}_part{part_idx:02d}.csv"
    current_bytes = 0
    wrote_header = False
    header_cols: Optional[List[str]] = None

    def _open_new_part():
        nonlocal part_idx, current_path, current_bytes, wrote_header, header_cols
        part_idx += 1
        current_path = f"{out_prefix}_part{part_idx:02d}.csv"
        current_bytes = 0
        wrote_header = False
        # header_cols stays the same

    # iterate runs
    for p in plans:
        df = pd.read_csv(p.path)
        # make sure run_id exists
        if "run_id" not in df.columns:
            df.insert(0, "run_id", p.run_id)
        else:
            # fill missing run_id with inferred
            df["run_id"] = df["run_id"].astype(str).replace({"nan": ""})
            if (df["run_id"] == "").all():
                df["run_id"] = p.run_id
            else:
                df["run_id"] = df["run_id"].where(df["run_id"] != "", p.run_id)

        k = allocations.get(p.run_id, min_rows_per_run)
        dfc = compress_timeseries(df, target_rows=k)

        # Harmonize columns across runs: keep union but stable order.
        if header_cols is None:
            header_cols = list(dfc.columns)
        else:
            # union
            for c in dfc.columns:
                if c not in header_cols:
                    header_cols.append(c)
            # add missing cols in dfc
            for c in header_cols:
                if c not in dfc.columns:
                    dfc[c] = np.nan
            dfc = dfc[header_cols]

        # estimate bytes to write
        csv_text = dfc.to_csv(index=False, header=not wrote_header)
        b = len(csv_text.encode("utf-8"))

        if current_bytes + b > limit and current_bytes > 0:
            # new part
            _open_new_part()
            csv_text = dfc.to_csv(index=False, header=True)
            b = len(csv_text.encode("utf-8"))

        # write append
        mode = "a" if os.path.exists(current_path) else "w"
        with open(current_path, mode, encoding="utf-8", newline="") as f:
            f.write(csv_text)

        current_bytes += b
        wrote_header = True

        if current_path not in out_files:
            out_files.append(current_path)

    return out_files


def main():
    ap = argparse.ArgumentParser(description="Bundle timeseries_*.csv into size-limited compressed parts.")
    ap.add_argument("--dir", type=str, default=".", help="Directory with timeseries_*.csv")
    ap.add_argument("--glob", type=str, default="timeseries_*.csv", help="Glob pattern")
    ap.add_argument("--out", type=str, default="bundle_timeseries", help="Output prefix (no .csv)")
    ap.add_argument("--max-mb", type=int, default=18, help="Max size per output file in MB")
    ap.add_argument("--min-rows", type=int, default=220, help="Minimum rows to keep per run (after compression)")
    args = ap.parse_args()

    paths = sorted(glob.glob(os.path.join(args.dir, args.glob)))
    if not paths:
        raise SystemExit(f"No files found: {os.path.join(args.dir, args.glob)}")

    out_files = bundle(paths, out_prefix=args.out, max_mb=args.max_mb, min_rows_per_run=args.min_rows)
    print("Created:")
    for p in out_files:
        sz = os.path.getsize(p) / (1024 * 1024)
        print(f"  {p}  ({sz:.2f} MB)")


if __name__ == "__main__":
    main()
