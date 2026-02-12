from __future__ import annotations

from typing import Dict

from detm.runtime.commit_packet import CommitPacket
from detm.runtime.fabric_ack import ProofAck, TrustAck
from detm.runtime.fabric_delivery import JsonlFabricEnvelopeOutbox
from detm.runtime.fabric_envelope import FabricEnvelope
from detm.runtime.fabric_handshake import FabricHandshakeService, RetryPolicy
from detm.runtime.fabric_quorum import BasicQuorumPolicy, InMemoryQuorumCoordinator, ValidatorSetQuorumPolicy
from detm.runtime.fabric_transport import InMemoryFabricBus
from detm.runtime.fabric_validator import LocalFabricValidator
from detm.runtime.fabric_validator_registry import StaticValidatorRegistry


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


def test_in_memory_quorum_coordinator_accepts_commit_after_two_ack_types():
    store: Dict[str, ProofAck | TrustAck] = {}

    proof = ProofAck(
        validator_id="validator-1",
        node_id="node-A",
        commit_ref="node-A:1",
        status="accepted",
        signature="sig://validator-1/proof/1",
    )
    trust = TrustAck(
        validator_id="validator-1",
        node_id="node-A",
        commit_ref="node-A:1",
        status="accepted",
        signature="sig://validator-1/trust/1",
    )
    store["artifact://ack/1"] = proof
    store["artifact://ack/2"] = trust

    coordinator = InMemoryQuorumCoordinator(
        policy=BasicQuorumPolicy(required_proof_accepts=1, required_trust_accepts=1),
        ack_resolver=lambda ref: store.get(ref),
    )
    coordinator.on_ack_envelope(
        FabricEnvelope.from_dict(
            {
                "message_type": "proof_ack",
                "channel": "fabric.ack",
                "mode": "realtime",
                "sender": "validator-1",
                "payload_ref": "artifact://ack/1",
                "commit_ref": "node-A:1",
            }
        )
    )
    coordinator.on_ack_envelope(
        FabricEnvelope.from_dict(
            {
                "message_type": "trust_ack",
                "channel": "fabric.ack",
                "mode": "realtime",
                "sender": "validator-1",
                "payload_ref": "artifact://ack/2",
                "commit_ref": "node-A:1",
            }
        )
    )

    evaluation = coordinator.evaluate("node-A:1")
    assert evaluation["status"] == "accepted"
    snapshot = coordinator.snapshot()
    assert int(snapshot["accepted_count"]) == 1


def test_validator_set_quorum_policy_requires_unique_validators_and_validator_set():
    policy = ValidatorSetQuorumPolicy(
        required_proof_accepts=2,
        required_trust_accepts=2,
        required_unique_proof_validators=2,
        required_unique_trust_validators=2,
        required_validator_ids=frozenset({"validator-1", "validator-2"}),
        enforce_required_validator_ids=True,
    )
    proof_acks = [
        ProofAck(
            validator_id="validator-1",
            node_id="node-A",
            commit_ref="node-A:1",
            status="accepted",
            signature="sig://validator-1/proof/1",
        ),
        ProofAck(
            validator_id="validator-2",
            node_id="node-A",
            commit_ref="node-A:1",
            status="accepted",
            signature="sig://validator-2/proof/1",
        ),
    ]
    trust_acks = [
        TrustAck(
            validator_id="validator-1",
            node_id="node-A",
            commit_ref="node-A:1",
            status="accepted",
            signature="sig://validator-1/trust/1",
        ),
        TrustAck(
            validator_id="validator-2",
            node_id="node-A",
            commit_ref="node-A:1",
            status="accepted",
            signature="sig://validator-2/trust/1",
        ),
    ]

    status, reason = policy.evaluate(proof_acks, trust_acks)
    assert status == "accepted"
    assert reason is None


def test_validator_set_quorum_policy_pending_when_required_validator_missing():
    policy = ValidatorSetQuorumPolicy(
        required_proof_accepts=1,
        required_trust_accepts=1,
        required_unique_proof_validators=1,
        required_unique_trust_validators=1,
        required_validator_ids=frozenset({"validator-1", "validator-2"}),
        enforce_required_validator_ids=True,
    )
    proof_acks = [
        ProofAck(
            validator_id="validator-1",
            node_id="node-A",
            commit_ref="node-A:1",
            status="accepted",
            signature="sig://validator-1/proof/1",
        )
    ]
    trust_acks = [
        TrustAck(
            validator_id="validator-1",
            node_id="node-A",
            commit_ref="node-A:1",
            status="accepted",
            signature="sig://validator-1/trust/1",
        )
    ]
    status, reason = policy.evaluate(proof_acks, trust_acks)
    assert status == "pending"
    assert "required validator set missing" in str(reason)


def test_static_validator_registry_normalizes_ids_and_checks_activity():
    registry = StaticValidatorRegistry.from_ids([" validator-1 ", "", "validator-2", "validator-1"])
    assert registry.required_validator_ids() == frozenset({"validator-1", "validator-2"})
    assert registry.is_active("validator-1")
    assert not registry.is_active("validator-3")


def test_in_memory_quorum_coordinator_rejects_pending_commit_after_timeout():
    coordinator = InMemoryQuorumCoordinator(
        policy=BasicQuorumPolicy(required_proof_accepts=1, required_trust_accepts=1),
        pending_timeout_ms=50,
    )
    coordinator.register_commit("node-A:timeout", created_at_ms=1000)
    row = coordinator.evaluate("node-A:timeout", now_ms=1060)
    assert row["status"] == "rejected"
    timeout = dict(row["timeout"])
    assert bool(timeout["enabled"]) is True
    assert bool(timeout["exceeded"]) is True


def test_in_memory_quorum_snapshot_includes_registered_commits_without_acks():
    coordinator = InMemoryQuorumCoordinator()
    coordinator.register_commit("node-A:registered-only")
    snapshot = coordinator.snapshot()
    refs = {str(row["commit_ref"]) for row in list(snapshot["evaluations"])}
    assert "node-A:registered-only" in refs


def test_in_memory_quorum_coordinator_accepts_inline_ack_payloads_without_resolver():
    coordinator = InMemoryQuorumCoordinator(
        policy=BasicQuorumPolicy(required_proof_accepts=1, required_trust_accepts=1),
        ack_resolver=None,
    )
    coordinator.register_commit("node-A:inline")

    proof = ProofAck(
        validator_id="validator-1",
        node_id="node-A",
        commit_ref="node-A:inline",
        status="accepted",
        signature="sig://validator-1/proof/inline",
    )
    trust = TrustAck(
        validator_id="validator-1",
        node_id="node-A",
        commit_ref="node-A:inline",
        status="accepted",
        signature="sig://validator-1/trust/inline",
    )
    coordinator.on_ack_envelope(
        FabricEnvelope.from_dict(
            {
                "message_type": "proof_ack",
                "channel": "fabric.ack",
                "mode": "realtime",
                "sender": "validator-1",
                "payload_ref": "artifact://remote/ack/1",
                "payload_inline": proof.to_dict(),
                "commit_ref": "node-A:inline",
            }
        )
    )
    coordinator.on_ack_envelope(
        FabricEnvelope.from_dict(
            {
                "message_type": "trust_ack",
                "channel": "fabric.ack",
                "mode": "realtime",
                "sender": "validator-1",
                "payload_ref": "artifact://remote/ack/2",
                "payload_inline": trust.to_dict(),
                "commit_ref": "node-A:inline",
            }
        )
    )

    row = coordinator.evaluate("node-A:inline")
    assert row["status"] == "accepted"


class _FlakyAckBus(InMemoryFabricBus):
    def __init__(self) -> None:
        super().__init__()
        self.failures_remaining = 1

    def publish(self, envelope: FabricEnvelope) -> int:
        if envelope.channel == "fabric.ack" and self.failures_remaining > 0:
            self.failures_remaining -= 1
            raise RuntimeError("transient publish error")
        return super().publish(envelope)


class _FailingAckBus(InMemoryFabricBus):
    def publish(self, envelope: FabricEnvelope) -> int:
        if envelope.channel.startswith("fabric.ack"):
            raise RuntimeError("persistent publish error")
        return super().publish(envelope)


class _DroppingAckBus(InMemoryFabricBus):
    def publish(self, envelope: FabricEnvelope) -> int:
        if envelope.channel.startswith("fabric.ack"):
            return 0
        return super().publish(envelope)


def test_fabric_handshake_service_retries_ack_publish_on_transient_failure():
    bus = _FlakyAckBus()
    validator = LocalFabricValidator(validator_id="validator-1")
    commit_store: Dict[str, CommitPacket] = {"artifact://commit/1": _make_commit("node-A:1", tick=1)}
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
        retry_policy=RetryPolicy(max_attempts=2),
    )
    service.start()
    bus.subscribe("fabric.ack", lambda env: ack_envelopes.append(env))

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

    assert len(ack_envelopes) == 2
    assert service.dead_letters == []


def test_fabric_handshake_service_mode_specific_channels_for_realtime_and_audit():
    bus = InMemoryFabricBus()
    validator = LocalFabricValidator(validator_id="validator-1")
    commit_store: Dict[str, CommitPacket] = {
        "artifact://commit/realtime": _make_commit("node-A:realtime", tick=1),
        "artifact://commit/audit": CommitPacket.from_dict(
            {
                "commit_type": "proof",
                "mode": "audit",
                "node_id": "node-A",
                "commit_id": "node-A:audit",
                "parent_ref": "node-A:realtime",
                "tick_ref": {"base_level": "L0", "tick": 2},
                "delta_ref": "artifact://delta/2",
                "invariants_ref": "artifact://invariants/2",
                "trace_ref": "trace://run/2",
                "signature": "sig://node-A/2",
            }
        ),
    }
    ack_store: Dict[str, ProofAck | TrustAck] = {}
    realtime_acks: list[FabricEnvelope] = []
    audit_acks: list[FabricEnvelope] = []

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
        commit_channels_by_mode={
            "realtime": "fabric.commit.realtime",
            "audit": "fabric.commit.audit",
        },
        ack_channels_by_mode={
            "realtime": "fabric.ack.realtime",
            "audit": "fabric.ack.audit",
        },
        mode_filter=None,
    )
    service.start()
    bus.subscribe("fabric.ack.realtime", lambda env: realtime_acks.append(env), mode="realtime")
    bus.subscribe("fabric.ack.audit", lambda env: audit_acks.append(env), mode="audit")

    bus.publish(
        FabricEnvelope.from_dict(
            {
                "message_type": "commit",
                "channel": "fabric.commit.realtime",
                "mode": "realtime",
                "sender": "node-A",
                "payload_ref": "artifact://commit/realtime",
                "commit_ref": "node-A:realtime",
            }
        )
    )
    bus.publish(
        FabricEnvelope.from_dict(
            {
                "message_type": "commit",
                "channel": "fabric.commit.audit",
                "mode": "audit",
                "sender": "node-A",
                "payload_ref": "artifact://commit/audit",
                "commit_ref": "node-A:audit",
            }
        )
    )

    assert len(realtime_acks) == 2
    assert len(audit_acks) == 2
    assert {env.channel for env in realtime_acks} == {"fabric.ack.realtime"}
    assert {env.channel for env in audit_acks} == {"fabric.ack.audit"}
    assert service.dead_letters == []


def test_fabric_handshake_service_queues_failed_acks_to_outbox_and_flushes_later(tmp_path):
    bus = _FailingAckBus()
    validator = LocalFabricValidator(validator_id="validator-1")
    commit_store: Dict[str, CommitPacket] = {"artifact://commit/1": _make_commit("node-A:1", tick=1)}
    ack_store: Dict[str, ProofAck | TrustAck] = {}
    outbox = JsonlFabricEnvelopeOutbox(path=tmp_path / "fabric_outbox.jsonl")

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
        retry_policy=RetryPolicy(max_attempts=1),
        delivery_outbox=outbox,
    )
    service.start()

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

    snap_failed = outbox.snapshot()
    assert int(snap_failed["pending_count"]) == 2
    assert len(service.dead_letters) == 2
    assert {str(row.get("queued_to_outbox")) for row in service.dead_letters} == {"true"}

    delivered: list[FabricEnvelope] = []
    working_bus = InMemoryFabricBus()
    working_bus.subscribe("fabric.ack", lambda env: delivered.append(env))
    flush_report = outbox.flush(working_bus.publish)
    assert int(flush_report["sent"]) == 2
    assert len(delivered) == 2
    snap_ok = outbox.snapshot()
    assert int(snap_ok["pending_count"]) == 0


def test_fabric_handshake_service_treats_zero_delivery_as_failure_and_queues_outbox(tmp_path):
    bus = _DroppingAckBus()
    validator = LocalFabricValidator(validator_id="validator-1")
    commit_store: Dict[str, CommitPacket] = {"artifact://commit/1": _make_commit("node-A:1", tick=1)}
    ack_store: Dict[str, ProofAck | TrustAck] = {}
    outbox = JsonlFabricEnvelopeOutbox(path=tmp_path / "fabric_outbox.jsonl")

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
        retry_policy=RetryPolicy(max_attempts=1),
        delivery_outbox=outbox,
    )
    service.start()

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

    snap_failed = outbox.snapshot()
    assert int(snap_failed["pending_count"]) == 2
    assert len(service.dead_letters) == 2
    assert all("returned 0" in str(row.get("error")) for row in service.dead_letters)


def test_fabric_handshake_service_emits_delivery_ack_for_commit_envelope():
    bus = InMemoryFabricBus()
    validator = LocalFabricValidator(validator_id="validator-1")
    commit_store: Dict[str, CommitPacket] = {"artifact://commit/1": _make_commit("node-A:1", tick=1)}
    ack_store: Dict[str, ProofAck | TrustAck] = {}
    delivery_acks: list[FabricEnvelope] = []

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
        emit_delivery_ack=True,
        delivery_ack_channel="fabric.delivery.ack",
    )
    service.start()
    bus.subscribe("fabric.delivery.ack", lambda env: delivery_acks.append(env), mode="realtime")

    bus.publish(
        FabricEnvelope.from_dict(
            {
                "message_type": "commit",
                "channel": "fabric.commit",
                "mode": "realtime",
                "sender": "node-A",
                "payload_ref": "artifact://commit/1",
                "commit_ref": "node-A:1",
                "delivery_id": "delivery-1",
            }
        )
    )

    assert len(delivery_acks) == 1
    ack = delivery_acks[0]
    assert ack.message_type == "delivery_ack"
    assert ack.delivery_id == "delivery-1"
    payload = dict(ack.payload_inline or {})
    assert str(payload.get("delivery_id")) == "delivery-1"
