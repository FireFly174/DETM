from __future__ import annotations

from detm.runtime.fabric import JsonlFabricEnvelopeOutbox
from detm.runtime.fabric import FabricEnvelope


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


def test_jsonl_outbox_respects_capacity_and_drop_oldest(tmp_path):
    outbox = JsonlFabricEnvelopeOutbox(path=tmp_path / "outbox.jsonl", max_entries=2, drop_oldest=True)
    outbox.enqueue(_env("1"))
    outbox.enqueue(_env("2"))
    outbox.enqueue(_env("3"))

    seen: list[str] = []

    def publish(env: FabricEnvelope) -> int:
        seen.append(str(env.commit_ref))
        return 1

    report = outbox.flush(publish)
    assert int(report["sent"]) == 2
    assert seen == ["2", "3"]
    snap = outbox.snapshot()
    assert int(snap["pending_count"]) == 0
    assert int(snap["dropped_total"]) == 1


def test_jsonl_outbox_flush_limit_keeps_remaining(tmp_path):
    outbox = JsonlFabricEnvelopeOutbox(path=tmp_path / "outbox.jsonl")
    outbox.enqueue(_env("1"))
    outbox.enqueue(_env("2"))
    outbox.enqueue(_env("3"))

    sent: list[str] = []
    first = outbox.flush(lambda env: sent.append(str(env.commit_ref)) or 1, max_items=2)
    assert int(first["sent"]) == 2
    assert sent == ["1", "2"]
    assert int(first["remaining"]) == 1

    second = outbox.flush(lambda env: sent.append(str(env.commit_ref)) or 1)
    assert int(second["sent"]) == 1
    assert sent == ["1", "2", "3"]


def test_jsonl_outbox_audit_first_preserves_realtime_on_overflow(tmp_path):
    outbox = JsonlFabricEnvelopeOutbox(path=tmp_path / "outbox.jsonl", max_entries=3, drop_policy="audit_first")
    outbox.enqueue(_env("rt-1"))
    outbox.enqueue(FabricEnvelope.from_dict({**_env("au-1").to_dict(), "mode": "audit"}))
    outbox.enqueue(_env("rt-2"))
    outbox.enqueue(FabricEnvelope.from_dict({**_env("au-2").to_dict(), "mode": "audit"}))

    sent: list[str] = []
    report = outbox.flush(lambda env: sent.append(str(env.commit_ref)) or 1)
    assert int(report["sent"]) == 3
    assert sent == ["rt-1", "rt-2", "au-2"]
    snap = outbox.snapshot()
    dropped = dict(snap["dropped_by_mode"])
    assert int(dropped["audit"]) == 1
    assert int(dropped["realtime"]) == 0

