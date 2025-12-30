# core/logger.py
import os, csv, time, json, uuid
from datetime import datetime
import numpy as np
class RunLogger:
    def __init__(self, run_dir, meta: dict, flush_every=1):
        self.run_dir = run_dir
        self.flush_every = max(1, int(flush_every))
        self._rows_since_flush = 0

        # --- run identity + time origin ---
        # run_id: уникальный идентификатор прогона (удобно объединять разные CSV)
        self.run_id = meta.get("run_id") if isinstance(meta, dict) and "run_id" in meta else str(uuid.uuid4())[:8]
        # wall clock start
        self.wall_t0 = time.time()
        # sim tick origin (t_global when first row written)
        self.t0 = None

        # --- segmentation inside one run (optional) ---
        self.segment_id = 0
        self.segment_t0 = None  # t_global at segment start

        os.makedirs(run_dir, exist_ok=True)
        os.makedirs(os.path.join(run_dir, "screenshots"), exist_ok=True)
        # --- fields recording (E history) ---
        self.fields_dir = os.path.join(run_dir, "fields")
        os.makedirs(self.fields_dir, exist_ok=True)

        # E-history
        self._E_hist_enabled = False
        self._E_hist_stride = 10
        self._E_hist_dtype = np.float32
        self._E_hist_max_frames = None
        self._E_hist_k = 0
        self._E_hist_frames = []
        self._E_hist_t = []

        # generic field-history
        self._field_hist_enabled = False
        self._field_hist_stride = 10
        self._field_hist_dtype = np.float32
        self._field_hist_max_frames = None
        self._field_hist_k = 0
        self._field_hist_fields = ("E",)
        self._field_hist_frames = {}  # name -> list[np.ndarray]
        self._field_hist_t = []
        # enrich meta
        meta = dict(meta) if isinstance(meta, dict) else {}
        meta["run_id"] = self.run_id
        meta["wall_t0"] = self.wall_t0


        with open(os.path.join(run_dir, "meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        self.csv_path = os.path.join(run_dir, f"timeseries_{self.run_id}.csv")
        self._csv_file = open(self.csv_path, "w", newline="", encoding="utf-8")
        self._writer = None

    def close(self):
        # сначала пытаемся выгрузить накопленные поля
        try:
            if hasattr(self, "flush_E_history"):
                self.flush_E_history()
            if hasattr(self, "flush_field_history"):
                self.flush_field_history()
        except Exception:
            pass

        # потом закрываем CSV
        try:
            if self._csv_file:
                self._csv_file.flush()
                self._csv_file.close()
        except Exception:
            pass

    def bump_segment(self, t_global=None):
        """
        Начать новый сегмент внутри одного запуска.
        Полезно, если ты хочешь вручную разделять прогон на 0–200/200–400/... без перезапуска.
        """
        self.segment_id += 1
        if t_global is not None:
            self.segment_t0 = float(t_global)
        else:
            self.segment_t0 = None

    def write_row(self, row: dict):
        # inject run/segment/time fields
        if "run_id" not in row:
            row["run_id"] = self.run_id

        # wall time relative
        if "wall_time" not in row:
            row["wall_time"] = time.time()

        row["wall_rel"] = float(row["wall_time"] - self.wall_t0)

        # t_rel based on first seen t_global
        if "t_global" in row and row["t_global"] is not None:
            tg = float(row["t_global"])
            if self.t0 is None:
                self.t0 = tg
            row["t_rel"] = tg - self.t0

            # segment relative
            row["segment_id"] = int(self.segment_id)
            if self.segment_t0 is None:
                self.segment_t0 = tg
            row["segment_rel"] = tg - float(self.segment_t0)
        else:
            row["t_rel"] = None
            row["segment_id"] = int(self.segment_id)
            row["segment_rel"] = None

        if self._writer is None:
            # фиксируем порядок колонок по первому row
            self._writer = csv.DictWriter(self._csv_file, fieldnames=list(row.keys()))
            self._writer.writeheader()

        self._writer.writerow(row)
        self._rows_since_flush += 1

        if self._rows_since_flush >= self.flush_every:
            self._csv_file.flush()
            self._rows_since_flush = 0

    def enable_E_history(self, stride: int = 10, dtype: str = "float32", max_frames: int | None = None):
        """
        Включить запись истории поля энергии E(t,i,j) в память с последующей выгрузкой в npz при close().
        stride=10 означает: сохранить каждый 10-й тик.
        dtype: "float16" | "float32"
        """
        self._E_hist_enabled = True
        self._E_hist_stride = max(1, int(stride))
        self._E_hist_max_frames = None if max_frames is None else int(max_frames)

        if dtype == "float16":
            self._E_hist_dtype = np.float16
        else:
            self._E_hist_dtype = np.float32

    def record_E(self, E, t_global: float | None = None):
        """
        Записать текущее поле E, но только если включено enable_E_history()
        и наступил нужный шаг по stride.
        """
        if not getattr(self, "_E_hist_enabled", False):
            return

        self._E_hist_k += 1
        if (self._E_hist_k % self._E_hist_stride) != 0:
            return

        if self._E_hist_max_frames is not None and len(self._E_hist_frames) >= self._E_hist_max_frames:
            return

        # E ожидается как numpy array (в torch backend у тебя есть numpy-mirror)
        arr = np.asarray(E, dtype=self._E_hist_dtype)
        self._E_hist_frames.append(arr.copy())

        if t_global is None:
            self._E_hist_t.append(np.nan)
        else:
            self._E_hist_t.append(float(t_global))

    def flush_E_history(self):
        """
        Сохранить E_hist в NPZ, если что-то накоплено.
        """
        if not getattr(self, "_E_hist_enabled", False):
            return
        if len(self._E_hist_frames) == 0:
            return

        E_hist = np.stack(self._E_hist_frames, axis=0)  # [T, N, N]
        t_hist = np.asarray(self._E_hist_t, dtype=np.float64)

        out_path = os.path.join(self.fields_dir, f"E_hist_{self.run_id}.npz")
        np.savez_compressed(out_path, E_hist=E_hist, t=t_hist)

        # освобождаем память (важно для batch)
        self._E_hist_frames.clear()
        self._E_hist_t.clear()

    def enable_field_history(self, fields=("E", "Jx", "Jy"), stride: int = 10,
                             dtype: str = "float32", max_frames: int | None = None):
        """
        Запись истории нескольких полей (E, Jx, Jy, S, tau, ...).
        fields: iterable of names, которые будут взяты из state по getattr(st, name)
        """
        self._field_hist_enabled = True
        self._field_hist_stride = max(1, int(stride))
        self._field_hist_max_frames = None if max_frames is None else int(max_frames)

        if dtype == "float16":
            self._field_hist_dtype = np.float16
        else:
            self._field_hist_dtype = np.float32

        self._field_hist_frames = {str(f): [] for f in fields}
        self._field_hist_t = []
        self._field_hist_k = 0

    def record_fields_from_state(self, st):
        """
        Считать поля из st и записать по stride.
        Требует enable_field_history().
        """
        if not getattr(self, "_field_hist_enabled", False):
            return

        self._field_hist_k += 1
        if (self._field_hist_k % self._field_hist_stride) != 0:
            return

        if self._field_hist_max_frames is not None:
            # если любой буфер уже достиг лимита — больше не пишем
            any_len = next(iter(self._field_hist_frames.values()))
            if len(any_len) >= self._field_hist_max_frames:
                return

        for name, buf in self._field_hist_frames.items():
            if not hasattr(st, name):
                continue
            arr = np.asarray(getattr(st, name), dtype=self._field_hist_dtype)
            buf.append(arr.copy())

        tg = getattr(st, "t_global", np.nan)

        # if "E" in self._field_hist_frames:
        #     E = getattr(st, "E", None)
        #     if E is not None:
        #         print("[fieldlog] tg=", getattr(st, "t_global", None),
        #               "Estd=", float(np.std(E)), "Jstd=", float(np.std(getattr(st, "Jx", 0.0))))
        self._field_hist_t.append(float(tg) if tg is not None else np.nan)

    def flush_field_history(self):
        """
        Сохранить историю полей в NPZ.
        """
        if not getattr(self, "_field_hist_enabled", False):
            return
        if not self._field_hist_frames:
            return
        # проверим, что хоть что-то записано
        lens = [len(v) for v in self._field_hist_frames.values()]
        if max(lens) == 0:
            return

        out = {}
        # t
        out["t"] = np.asarray(self._field_hist_t, dtype=np.float64)
        # поля
        for name, frames in self._field_hist_frames.items():
            if len(frames) == 0:
                continue
            out[f"{name}_hist"] = np.stack(frames, axis=0)

        out_path = os.path.join(self.fields_dir, f"fields_hist_{self.run_id}.npz")
        np.savez_compressed(out_path, **out)

        # clean
        for k in self._field_hist_frames:
            self._field_hist_frames[k].clear()
        self._field_hist_t.clear()

    def save_figure(self, fig, step_tag=""):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        tag = f"_{step_tag}" if step_tag else ""
        path = os.path.join(self.run_dir, "screenshots", f"shot_{ts}{tag}.png")
        fig.savefig(path, dpi=160)
        return path

    @staticmethod
    def make_run_dir(base_dir="."):
        # avoid collisions in batch: add microseconds + short uuid tail
        ts = datetime.now().strftime("run_%Y%m%d_%H%M%S_%f")
        tail = str(uuid.uuid4())[:4]
        return os.path.join(base_dir, f"{ts}_{tail}")

    @staticmethod
    def wall_time():
        return time.time()
