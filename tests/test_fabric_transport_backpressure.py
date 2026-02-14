from __future__ import annotations

import time

import pytest

from detm.runtime.fabric import FabricEnvelope
from detm.runtime.fabric import BufferedFabricTransport


def _env(commit_ref: str) -> FabricEnvelope:
    return FabricEnvelope.from_dict(
        {
            "message_type": "commit",
            "channel": "fabric.commit",
            "mode": "realtime",
            "sender": "node-A",
            "payload_ref": f"artifact://commit/{commit_ref}",
            "commit_ref": commit_ref,
        }
    )


class _RecordingTransport:
    def __init__(self) -> None:
        self.rows: list[FabricEnvelope] = []

    def subscribe(self, channel, handler, *, mode=None) -> None:  # pragma: no cover - passthrough stub
        return None

    def unsubscribe(self, channel, handler, *, mode=None) -> bool:  # pragma: no cover - passthrough stub
        return False

    def publish(self, envelope: FabricEnvelope) -> int:
        self.rows.append(envelope)
        return 1

    def close(self) -> None:
        return None


def _wait_until(predicate, timeout_s: float = 1.0) -> bool:
    started = time.perf_counter()
    while (time.perf_counter() - started) < timeout_s:
        if bool(predicate()):
            return True
        time.sleep(0.01)
    return False


def test_buffered_transport_drop_newest_policy_reports_drop_and_keeps_oldest():
    base = _RecordingTransport()
    transport = BufferedFabricTransport(
        base=base,
        max_pending=1,
        policy="drop_newest",
        auto_start=False,
        close_base_on_close=False,
    )
    try:
        assert transport.publish(_env("1")) == 1
        assert transport.publish(_env("2")) == 0
        snap_before = transport.snapshot()
        assert int(snap_before["pending_count"]) == 1
        assert int(snap_before["dropped_newest_total"]) == 1

        transport.start()
        assert _wait_until(lambda: int(transport.snapshot()["pending_count"]) == 0)
        assert [str(row.commit_ref) for row in base.rows] == ["1"]
    finally:
        transport.close()


def test_buffered_transport_drop_oldest_policy_replaces_pending_item():
    base = _RecordingTransport()
    transport = BufferedFabricTransport(
        base=base,
        max_pending=1,
        policy="drop_oldest",
        auto_start=False,
        close_base_on_close=False,
    )
    try:
        assert transport.publish(_env("1")) == 1
        assert transport.publish(_env("2")) == 1
        snap_before = transport.snapshot()
        assert int(snap_before["pending_count"]) == 1
        assert int(snap_before["dropped_oldest_total"]) == 1

        transport.start()
        assert _wait_until(lambda: int(transport.snapshot()["pending_count"]) == 0)
        assert [str(row.commit_ref) for row in base.rows] == ["2"]
    finally:
        transport.close()


def test_buffered_transport_block_policy_raises_on_timeout_when_queue_full():
    base = _RecordingTransport()
    transport = BufferedFabricTransport(
        base=base,
        max_pending=1,
        policy="block",
        block_timeout_ms=10,
        auto_start=False,
        close_base_on_close=False,
    )
    try:
        assert transport.publish(_env("1")) == 1
        with pytest.raises(RuntimeError, match="block timeout exceeded"):
            transport.publish(_env("2"))
        snap = transport.snapshot()
        assert int(snap["rejected_total"]) == 1
        assert int(snap["pending_count"]) == 1
    finally:
        transport.close()

