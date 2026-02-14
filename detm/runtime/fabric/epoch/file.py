"""File-backed epoch/watermark coordinator."""

from __future__ import annotations

import contextlib
import json
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator

from detm.runtime.commit_packet import CommitPacket
from detm.runtime.fabric.epoch.contracts import EpochDecision
from detm.runtime.fabric.epoch.memory import InMemoryEpochWatermarkCoordinator
from detm.runtime.fabric.epoch.operations import commit_epoch, commit_watermark


@dataclass
class FileEpochWatermarkCoordinator:
    """File-backed epoch/watermark coordinator for shared-node MVP."""

    state_path: Path
    lock_path: Path | None = None
    lock_timeout_ms: int = 5000
    lock_poll_ms: int = 10
    lock_stale_ms: int | None = 30000
    enforce_monotonic_tick: bool = True
    enforce_monotonic_epoch: bool = True
    enforce_monotonic_watermark: bool = True
    enforce_watermark_le_epoch: bool = True
    _lock: threading.RLock = field(default_factory=threading.RLock)

    def __post_init__(self) -> None:
        self.state_path = Path(self.state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        if self.lock_path is None:
            self.lock_path = self.state_path.with_suffix(f"{self.state_path.suffix}.lock")
        else:
            self.lock_path = Path(self.lock_path)
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_timeout_ms = max(1, int(self.lock_timeout_ms))
        self.lock_poll_ms = max(1, int(self.lock_poll_ms))
        if self.lock_stale_ms is not None:
            self.lock_stale_ms = max(1, int(self.lock_stale_ms))

    def evaluate_commit(self, packet: CommitPacket) -> EpochDecision:
        with self._lock:
            try:
                with self._file_lock():
                    coordinator = self._load_coordinator()
                    decision = coordinator.evaluate_commit(packet)
                    if bool(decision.accepted):
                        self._store_snapshot(coordinator.snapshot())
                    return decision
            except TimeoutError as exc:
                tick = int(packet.tick_ref.tick)
                epoch = int(commit_epoch(packet))
                watermark = int(commit_watermark(packet))
                return EpochDecision(
                    accepted=False,
                    reason=f"epoch coordinator lock timeout: {exc}",
                    epoch=epoch,
                    watermark=watermark,
                    tick=tick,
                )

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            with self._file_lock():
                coordinator = self._load_coordinator()
                payload = coordinator.snapshot()
                payload["state_path"] = str(self.state_path)
                payload["lock"] = {
                    "lock_path": str(self.lock_path),
                    "timeout_ms": int(self.lock_timeout_ms),
                    "poll_ms": int(self.lock_poll_ms),
                    "stale_ms": None if self.lock_stale_ms is None else int(self.lock_stale_ms),
                }
                return payload

    def _load_coordinator(self) -> InMemoryEpochWatermarkCoordinator:
        coordinator = InMemoryEpochWatermarkCoordinator(
            enforce_monotonic_tick=bool(self.enforce_monotonic_tick),
            enforce_monotonic_epoch=bool(self.enforce_monotonic_epoch),
            enforce_monotonic_watermark=bool(self.enforce_monotonic_watermark),
            enforce_watermark_le_epoch=bool(self.enforce_watermark_le_epoch),
        )
        if not self.state_path.exists():
            return coordinator
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception:
            return coordinator
        if isinstance(payload, dict):
            coordinator.load_snapshot(payload)
        return coordinator

    def _store_snapshot(self, payload: Dict[str, Any]) -> None:
        tmp_path = self.state_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        tmp_path.replace(self.state_path)

    @contextlib.contextmanager
    def _file_lock(self) -> Iterator[None]:
        assert self.lock_path is not None
        start = time.monotonic()
        fh: int | None = None
        while fh is None:
            try:
                fh = os.open(str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_RDWR)
                meta = json.dumps({"pid": os.getpid(), "acquired_at_ms": int(time.time() * 1000)})
                os.write(fh, meta.encode("utf-8"))
                break
            except FileExistsError:
                if self._clear_stale_lock_if_needed():
                    continue
                elapsed_ms = (time.monotonic() - start) * 1000.0
                if elapsed_ms >= float(self.lock_timeout_ms):
                    raise TimeoutError(f"lock_path={self.lock_path}")
                time.sleep(float(self.lock_poll_ms) / 1000.0)
        try:
            yield
        finally:
            if fh is not None:
                try:
                    os.close(fh)
                except OSError:
                    pass
            with contextlib.suppress(OSError):
                if self.lock_path.exists():
                    self.lock_path.unlink()

    def _clear_stale_lock_if_needed(self) -> bool:
        if self.lock_stale_ms is None:
            return False
        assert self.lock_path is not None
        try:
            stat = self.lock_path.stat()
        except FileNotFoundError:
            return True
        age_ms = int((time.time() - float(stat.st_mtime)) * 1000.0)
        if age_ms < int(self.lock_stale_ms):
            return False
        with contextlib.suppress(OSError):
            self.lock_path.unlink()
        return not self.lock_path.exists()


__all__ = ["FileEpochWatermarkCoordinator"]

