from __future__ import annotations

from typing import Dict

from detm.runtime.commit_packet import CommitPacket
from detm.runtime.fabric import ProofAck, TrustAck
from detm.runtime.fabric import FileFabricArtifactStore
from detm.runtime.fabric import InMemoryEpochWatermarkCoordinator
from detm.runtime.fabric import FabricEnvelope
from detm.runtime.fabric import FabricHandshakeService
from detm.runtime.fabric import InMemoryFabricBus
from detm.runtime.fabric import LocalFabricValidator, ReplaySamplePolicy


def _make_commit(commit_id: str, tick: int, parent_ref: str | None = None) -> CommitPacket:
    return CommitPacket.from_dict(
        {
            "commit_type": "state",
            "mode": "realtime",
            "node_id": "node-A",
            "commit_id": commit_id,
            "parent_ref": parent_ref,
            "tick_ref": {"base_level": "L0", "tick": tick},
            "delta_ref": f"artifact://delta/{tick}",
            "trace_ref": f"trace://run/{tick}",
            "signature": f"sig://node-A/{tick}",
        }
    )


def test_local_fabric_validator_accepts_chain_and_rejects_broken_parent():
    validator = LocalFabricValidator(validator_id="validator-1")

    p1, t1 = validator.validate_commit(_make_commit("node-A:1", tick=1))
    p2, t2 = validator.validate_commit(_make_commit("node-A:2", tick=2, parent_ref="node-A:1"))
    p3, t3 = validator.validate_commit(_make_commit("node-A:3", tick=3, parent_ref="node-A:999"))

    assert p1.status == "accepted"
    assert t1.status == "accepted"
    assert p2.status == "accepted"
    assert t2.status == "accepted"
    assert p3.status == "rejected"
    assert t3.status == "rejected"
    assert "parent mismatch" in str(p3.reason)


def test_local_fabric_validator_replay_sampling_rejects_failed_sample():
    validator = LocalFabricValidator(
        validator_id="validator-1",
        replay_policy=ReplaySamplePolicy(enabled=True, sample_stride=1, sample_offset=0),
        replay_checker=lambda _packet: (False, "replay mismatch"),
    )
    p1, t1 = validator.validate_commit(_make_commit("node-A:1", tick=1))
    assert p1.status == "rejected"
    assert t1.status == "rejected"
    assert "replay mismatch" in str(p1.reason)


def test_local_fabric_validator_replay_sampling_skips_non_sampled_tick():
    validator = LocalFabricValidator(
        validator_id="validator-1",
        replay_policy=ReplaySamplePolicy(enabled=True, sample_stride=2, sample_offset=0),
        replay_checker=lambda _packet: (False, "should not run on odd tick"),
    )
    p1, t1 = validator.validate_commit(_make_commit("node-A:1", tick=1))
    assert p1.status == "accepted"
    assert t1.status == "accepted"


def test_local_fabric_validator_replay_policy_off_disables_checker():
    validator = LocalFabricValidator(
        validator_id="validator-1",
        replay_policy=ReplaySamplePolicy(tier="off", enabled=True, sample_stride=1, sample_offset=0),
        replay_checker=lambda _packet: (False, "should not run when tier=off"),
    )
    p1, t1 = validator.validate_commit(_make_commit("node-A:1", tick=1))
    assert p1.status == "accepted"
    assert t1.status == "accepted"


def test_local_fabric_validator_replay_strict_window_rejects_old_tick():
    validator = LocalFabricValidator(
        validator_id="validator-1",
        replay_policy=ReplaySamplePolicy(tier="strict_window", strict_window_size=2),
        replay_checker=lambda _packet: (True, None),
    )
    p1, _t1 = validator.validate_commit(_make_commit("node-A:1", tick=1))
    p2, _t2 = validator.validate_commit(_make_commit("node-A:2", tick=2, parent_ref="node-A:1"))
    p3, _t3 = validator.validate_commit(_make_commit("node-A:3", tick=3, parent_ref="node-A:2"))
    p_old, t_old = validator.validate_commit(_make_commit("node-A:old", tick=1, parent_ref="node-A:3"))
    assert p1.status == "accepted"
    assert p2.status == "accepted"
    assert p3.status == "accepted"
    assert p_old.status == "rejected"
    assert t_old.status == "rejected"
    assert "strict_window violation" in str(p_old.reason)


def test_fabric_handshake_service_publishes_acks_for_commit_envelope():
    bus = InMemoryFabricBus()
    validator = LocalFabricValidator(validator_id="validator-1")

    commit_store: Dict[str, CommitPacket] = {
        "artifact://commit/node-A/1": _make_commit("node-A:1", tick=1),
    }
    ack_store: Dict[str, ProofAck | TrustAck] = {}
    ack_envelopes: list[FabricEnvelope] = []

    def resolve_commit(payload_ref: str) -> CommitPacket | None:
        return commit_store.get(payload_ref)

    def write_ack(ack: ProofAck | TrustAck) -> str:
        ref = f"artifact://ack/{len(ack_store) + 1}"
        ack_store[ref] = ack
        return ref

    service = FabricHandshakeService(
        transport=bus,
        validator=validator,
        commit_resolver=resolve_commit,
        ack_writer=write_ack,
        commit_channel="fabric.commit",
        ack_channel="fabric.ack",
    )
    service.start()

    bus.subscribe("fabric.ack", lambda envelope: ack_envelopes.append(envelope))
    bus.publish(
        FabricEnvelope.from_dict(
            {
                "message_type": "commit",
                "channel": "fabric.commit",
                "mode": "realtime",
                "sender": "node-A",
                "payload_ref": "artifact://commit/node-A/1",
                "trace_ref": "trace://run/1",
                "commit_ref": "node-A:1",
            }
        )
    )

    assert len(ack_envelopes) == 2
    assert {env.message_type for env in ack_envelopes} == {"proof_ack", "trust_ack"}
    assert all(env.recipient == "node-A" for env in ack_envelopes)
    assert len(ack_store) == 2
    assert all(ack.status == "accepted" for ack in ack_store.values())


def test_fabric_handshake_service_rejects_missing_payload_ref():
    bus = InMemoryFabricBus()
    validator = LocalFabricValidator(validator_id="validator-1")
    ack_store: Dict[str, ProofAck | TrustAck] = {}
    ack_envelopes: list[FabricEnvelope] = []

    def resolve_commit(_payload_ref: str) -> CommitPacket | None:
        return None

    def write_ack(ack: ProofAck | TrustAck) -> str:
        ref = f"artifact://ack/{len(ack_store) + 1}"
        ack_store[ref] = ack
        return ref

    service = FabricHandshakeService(
        transport=bus,
        validator=validator,
        commit_resolver=resolve_commit,
        ack_writer=write_ack,
    )
    service.start()
    bus.subscribe("fabric.ack", lambda envelope: ack_envelopes.append(envelope))

    bus.publish(
        FabricEnvelope.from_dict(
            {
                "message_type": "commit",
                "channel": "fabric.commit",
                "mode": "realtime",
                "sender": "node-A",
                "payload_ref": "artifact://missing/1",
                "commit_ref": "node-A:missing",
            }
        )
    )

    assert len(ack_envelopes) == 2
    assert all(env.commit_ref == "node-A:missing" for env in ack_envelopes)
    assert all(ack.status == "rejected" for ack in ack_store.values())


def test_fabric_handshake_service_accepts_inline_commit_payload_when_ref_missing():
    bus = InMemoryFabricBus()
    validator = LocalFabricValidator(validator_id="validator-1")
    ack_store: Dict[str, ProofAck | TrustAck] = {}
    ack_envelopes: list[FabricEnvelope] = []

    def resolve_commit(_payload_ref: str) -> CommitPacket | None:
        return None

    def write_ack(ack: ProofAck | TrustAck) -> str:
        ref = f"artifact://ack/{len(ack_store) + 1}"
        ack_store[ref] = ack
        return ref

    service = FabricHandshakeService(
        transport=bus,
        validator=validator,
        commit_resolver=resolve_commit,
        ack_writer=write_ack,
    )
    service.start()
    bus.subscribe("fabric.ack", lambda envelope: ack_envelopes.append(envelope))

    packet = _make_commit("node-A:inline", tick=7)
    bus.publish(
        FabricEnvelope.from_dict(
            {
                "message_type": "commit",
                "channel": "fabric.commit",
                "mode": "realtime",
                "sender": "node-A",
                "payload_ref": "artifact://missing/inline",
                "payload_inline": packet.to_dict(),
                "commit_ref": "node-A:inline",
            }
        )
    )

    assert len(ack_envelopes) == 2
    assert all(env.payload_inline is not None for env in ack_envelopes)
    assert all(ack.status == "accepted" for ack in ack_store.values())


def test_fabric_handshake_service_uses_shared_artifact_store_without_inline_bridge(tmp_path):
    bus = InMemoryFabricBus()
    validator = LocalFabricValidator(validator_id="validator-1")
    store = FileFabricArtifactStore(tmp_path / "shared")
    ack_envelopes: list[FabricEnvelope] = []

    packet = _make_commit("node-A:shared", tick=9)
    commit_ref = store.write_commit(packet, artifact_ref="artifact://commit/shared/9")

    service = FabricHandshakeService(
        transport=bus,
        validator=validator,
        commit_resolver=store.read_commit,
        ack_writer=store.write_ack,
    )
    service.start()
    bus.subscribe("fabric.ack", lambda envelope: ack_envelopes.append(envelope))

    bus.publish(
        FabricEnvelope.from_dict(
            {
                "message_type": "commit",
                "channel": "fabric.commit",
                "mode": "realtime",
                "sender": "node-A",
                "payload_ref": commit_ref,
                "commit_ref": "node-A:shared",
            }
        )
    )

    assert len(ack_envelopes) == 2
    assert all(env.payload_inline is not None for env in ack_envelopes)
    for env in ack_envelopes:
        restored = store.read_ack(env.payload_ref)
        assert restored is not None
        assert restored.commit_ref == "node-A:shared"


def test_fabric_handshake_service_rejects_epoch_regression():
    bus = InMemoryFabricBus()
    validator = LocalFabricValidator(validator_id="validator-1")
    epoch_coordinator = InMemoryEpochWatermarkCoordinator()
    ack_store: Dict[str, ProofAck | TrustAck] = {}
    ack_envelopes: list[FabricEnvelope] = []

    commit_store: Dict[str, CommitPacket] = {
        "artifact://commit/1": CommitPacket.from_dict(
            {
                "commit_type": "state",
                "mode": "realtime",
                "node_id": "node-A",
                "commit_id": "node-A:1",
                "tick_ref": {"base_level": "L0", "tick": 1},
                "delta_ref": "artifact://delta/1",
                "trace_ref": "trace://run/1",
                "summary": {"epoch": 1, "watermark": 1},
                "signature": "sig://node-A/1",
            }
        ),
        "artifact://commit/2": CommitPacket.from_dict(
            {
                "commit_type": "state",
                "mode": "realtime",
                "node_id": "node-A",
                "commit_id": "node-A:2",
                "parent_ref": "node-A:1",
                "tick_ref": {"base_level": "L0", "tick": 2},
                "delta_ref": "artifact://delta/2",
                "trace_ref": "trace://run/2",
                "summary": {"epoch": 0, "watermark": 0},
                "signature": "sig://node-A/2",
            }
        ),
    }

    def resolve_commit(payload_ref: str) -> CommitPacket | None:
        return commit_store.get(payload_ref)

    def write_ack(ack: ProofAck | TrustAck) -> str:
        ref = f"artifact://ack/{len(ack_store) + 1}"
        ack_store[ref] = ack
        return ref

    service = FabricHandshakeService(
        transport=bus,
        validator=validator,
        commit_resolver=resolve_commit,
        ack_writer=write_ack,
        epoch_coordinator=epoch_coordinator,
    )
    service.start()
    bus.subscribe("fabric.ack", lambda envelope: ack_envelopes.append(envelope))

    bus.publish(
        FabricEnvelope.from_dict(
            {
                "message_type": "commit",
                "channel": "fabric.commit",
                "mode": "realtime",
                "sender": "node-A",
                "payload_ref": "artifact://commit/1",
                "commit_ref": "node-A:1",
            }
        )
    )
    bus.publish(
        FabricEnvelope.from_dict(
            {
                "message_type": "commit",
                "channel": "fabric.commit",
                "mode": "realtime",
                "sender": "node-A",
                "payload_ref": "artifact://commit/2",
                "commit_ref": "node-A:2",
            }
        )
    )

    second_pair = list(ack_store.values())[2:4]
    assert len(ack_envelopes) == 4
    assert len(second_pair) == 2
    assert {ack.status for ack in second_pair} == {"rejected"}
    assert any("epoch regression" in str(ack.reason) for ack in second_pair)

