from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, List

import numpy as np

from detm.runtime.state import DETMState

from detm_app.runtime.subscribers.common import _to_numpy


@dataclass
class FieldHistoryRecorder:
    """Record field histories into `fields_hist.npz` (legacy-friendly)."""

    out_path: Path
    every_steps: int = 1
    dtype: str = "float32"
    _t: List[int] = None  # type: ignore[assignment]
    _E: List[np.ndarray] = None  # type: ignore[assignment]
    _S: List[np.ndarray] = None  # type: ignore[assignment]
    _tau: List[np.ndarray] = None  # type: ignore[assignment]
    _Jx: List[np.ndarray] = None  # type: ignore[assignment]
    _Jy: List[np.ndarray] = None  # type: ignore[assignment]
    _last_step: int = -1
    _unsub_reset: Callable[[], None] | None = None
    _unsub_step: Callable[[], None] | None = None
    _unsub_close: Callable[[], None] | None = None

    @classmethod
    def attach(
        cls,
        bus,
        out_path: Path,
        *,
        every_steps: int = 1,
        dtype: str = "float32",
    ) -> "FieldHistoryRecorder":
        rec = cls(out_path=out_path, every_steps=max(1, int(every_steps)), dtype=str(dtype))
        rec._t, rec._E, rec._S, rec._tau, rec._Jx, rec._Jy = [], [], [], [], [], []
        rec._unsub_reset = bus.add_event_listener_unsub("reset", rec.on_reset)
        rec._unsub_step = bus.add_event_listener_unsub("step", rec.on_step)
        rec._unsub_close = bus.add_event_listener_unsub("close", rec.on_close)
        return rec

    def _append_state(self, state: DETMState) -> None:
        lattice = state.lattice
        H, W = lattice.height, lattice.width

        E = _to_numpy(state.field_state.energy).astype(np.float32, copy=False).reshape(H, W)
        S = _to_numpy(state.field_state.entropy).astype(np.float32, copy=False).reshape(H, W)
        tau = _to_numpy(state.field_state.internal_time).astype(np.float32, copy=False).reshape(H, W)

        Jx = 0.5 * (np.roll(E, -1, axis=1) - np.roll(E, 1, axis=1))
        Jy = 0.5 * (np.roll(E, -1, axis=0) - np.roll(E, 1, axis=0))

        self._t.append(int(state.step_count))
        self._E.append(E)
        self._S.append(S)
        self._tau.append(tau)
        self._Jx.append(Jx)
        self._Jy.append(Jy)

    def on_reset(self, *, state: DETMState, **_rest: Any) -> None:
        self._last_step = -1
        self._append_state(state)
        self._last_step = int(state.step_count)

    def on_step(self, *, state: DETMState, **_rest: Any) -> None:
        step = int(state.step_count)
        if self._last_step >= 0 and (step - self._last_step) < self.every_steps:
            return
        self._append_state(state)
        self._last_step = step

    def on_close(self, **_rest: Any) -> None:
        self.out_path.parent.mkdir(parents=True, exist_ok=True)
        dtype = np.float16 if self.dtype.lower() == "float16" else np.float32

        t = np.asarray(self._t, dtype=float)
        E_hist = np.asarray(self._E, dtype=dtype)
        S_hist = np.asarray(self._S, dtype=dtype)
        tau_hist = np.asarray(self._tau, dtype=dtype)
        Jx_hist = np.asarray(self._Jx, dtype=dtype)
        Jy_hist = np.asarray(self._Jy, dtype=dtype)

        np.savez_compressed(
            self.out_path,
            t=t,
            E_hist=E_hist,
            S_hist=S_hist,
            tau_hist=tau_hist,
            Jx_hist=Jx_hist,
            Jy_hist=Jy_hist,
        )
        self.detach()

    def detach(self) -> None:
        if self._unsub_reset is not None:
            self._unsub_reset()
            self._unsub_reset = None
        if self._unsub_step is not None:
            self._unsub_step()
            self._unsub_step = None
        if self._unsub_close is not None:
            self._unsub_close()
            self._unsub_close = None


__all__ = ["FieldHistoryRecorder"]
