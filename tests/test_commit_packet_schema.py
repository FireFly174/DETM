from __future__ import annotations

import pytest

from detm.runtime.commit_packet import CommitPacket
from detm.runtime.schemas import DETM_COMMIT_PACKET_V1, get_schema_versions


def test_commit_packet_roundtrip_and_schema_registry():
    payload = {
        "schema_version": DETM_COMMIT_PACKET_V1,
        "commit_type": "boundary",
        "mode": "realtime",
        "node_id": "node-A",
        "commit_id": "node-A:42",
        "parent_ref": "node-A:41",
        "tick_ref": {"base_level": "L0", "tick": 42, "equiv_l0_ticks": 42},
        "inputs_ref": "artifact://inputs/42",
        "delta_ref": "artifact://delta/42",
        "invariants_ref": "artifact://inv/42",
        "trace_ref": "trace://run/42",
        "summary": {"boundary_flux": 0.12, "event_count": 3},
        "signature": "sig://node-A/42",
        "created_at_ms": 123456,
    }

    packet = CommitPacket.from_dict(payload)
    restored = CommitPacket.from_dict(packet.to_dict())

    assert restored.commit_type == "boundary"
    assert restored.mode == "realtime"
    assert restored.tick_ref.tick == 42
    assert restored.trace_ref == "trace://run/42"
    assert get_schema_versions()["commit_packet"] == DETM_COMMIT_PACKET_V1


def test_commit_packet_requires_trace_ref():
    payload = {
        "commit_type": "state",
        "mode": "realtime",
        "node_id": "node-A",
        "commit_id": "node-A:1",
        "tick_ref": {"base_level": "L0", "tick": 1},
        "delta_ref": "artifact://delta/1",
        "trace_ref": "",
        "signature": "sig://node-A/1",
    }
    with pytest.raises(ValueError, match="trace_ref"):
        CommitPacket.from_dict(payload)


def test_commit_packet_requires_delta_for_state_boundary_coarsened():
    for commit_type in ("state", "boundary", "coarsened"):
        payload = {
            "commit_type": commit_type,
            "mode": "realtime",
            "node_id": "node-A",
            "commit_id": f"node-A:{commit_type}",
            "tick_ref": {"base_level": "L0", "tick": 1},
            "trace_ref": "trace://run/1",
            "signature": "sig://node-A/1",
        }
        with pytest.raises(ValueError, match="delta_ref"):
            CommitPacket.from_dict(payload)


def test_proof_commit_requires_invariants_ref():
    payload = {
        "commit_type": "proof",
        "mode": "audit",
        "node_id": "node-A",
        "commit_id": "node-A:proof-1",
        "tick_ref": {"base_level": "L0", "tick": 1},
        "trace_ref": "trace://run/1",
        "signature": "sig://node-A/1",
    }
    with pytest.raises(ValueError, match="invariants_ref"):
        CommitPacket.from_dict(payload)
