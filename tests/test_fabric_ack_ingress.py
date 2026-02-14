from __future__ import annotations

from detm.runtime.fabric import FabricAckIngressService
from detm.runtime.fabric import FabricEnvelope
from detm.runtime.fabric import InMemoryFabricBus
from detm.runtime.fabric import FabricQuorumRuntimeService


def _ack_env(*, channel: str = "fabric.ack", mode: str = "realtime", sender: str = "validator-1") -> FabricEnvelope:
    return FabricEnvelope.from_dict(
        {
            "message_type": "proof_ack",
            "channel": channel,
            "mode": mode,
            "sender": sender,
            "payload_ref": f"artifact://ack/{sender}/{mode}",
            "commit_ref": "node-A:1",
        }
    )


class _Collector:
    def __init__(self) -> None:
        self.rows: list[FabricEnvelope] = []

    def on_ack_envelope(self, envelope: FabricEnvelope) -> None:
        self.rows.append(envelope)


def test_ack_ingress_subscribes_mode_specific_channels():
    bus = InMemoryFabricBus()
    collector = _Collector()
    service = FabricAckIngressService(
        transport=bus,
        ack_channel="fabric.ack",
        ack_channels_by_mode={
            "realtime": "fabric.ack.realtime",
            "audit": "fabric.ack.audit",
        },
        mode_filter="audit",
        consumer=collector,
    )
    service.start()

    bus.publish(_ack_env(channel="fabric.ack.realtime", mode="realtime"))
    bus.publish(_ack_env(channel="fabric.ack.audit", mode="audit"))

    assert [str(env.mode) for env in service.ack_envelopes] == ["audit"]
    assert [str(env.mode) for env in collector.rows] == ["audit"]
    service.stop()


def test_ack_ingress_forwards_envelopes_to_consumer():
    bus = InMemoryFabricBus()
    collector = _Collector()
    service = FabricAckIngressService(transport=bus, consumer=collector)
    service.start()

    bus.publish(_ack_env())

    assert len(service.ack_envelopes) == 1
    assert len(collector.rows) == 1
    assert str(collector.rows[0].message_type) == "proof_ack"
    service.stop()


def test_ack_ingress_stop_unsubscribes_handlers():
    bus = InMemoryFabricBus()
    service = FabricAckIngressService(transport=bus)
    service.start()
    service.stop()

    bus.publish(_ack_env())

    assert service.ack_envelopes == []


def test_ack_ingress_runtime_consumer_can_drop_inactive_validator_ack():
    bus = InMemoryFabricBus()
    runtime = FabricQuorumRuntimeService.from_policy_settings(
        required_proof_accepts=1,
        required_trust_accepts=1,
        required_validator_ids=["validator-1"],
        enforce_active_validator_membership=True,
    )
    runtime.register_commit("node-A:1")
    service = FabricAckIngressService(transport=bus, consumer=runtime)
    service.start()
    bus.publish(_ack_env(sender="validator-unknown"))

    snap = runtime.snapshot()
    hardening = dict(snap["membership_hardening"])
    assert int(hardening["dropped_inactive_validator_total"]) == 1
    assert int(snap["pending_count"]) == 1
    service.stop()


def test_ack_ingress_runtime_consumer_can_drop_ack_by_auth_key_id_binding():
    bus = InMemoryFabricBus()
    runtime = FabricQuorumRuntimeService.from_policy_settings(
        required_proof_accepts=1,
        required_trust_accepts=1,
        required_validator_ids=["validator-1"],
        enforce_active_validator_membership=True,
        enforce_ack_auth_key_id_binding=True,
        validator_auth_key_ids={"validator-1": ["kid-1"]},
    )
    runtime.register_commit("node-A:1")
    service = FabricAckIngressService(transport=bus, consumer=runtime)
    service.start()
    bad = _ack_env(sender="validator-1").to_dict()
    bad["auth_key_id"] = "kid-bad"
    bus.publish(FabricEnvelope.from_dict(bad))

    snap = runtime.snapshot()
    hardening = dict(snap["membership_hardening"])
    assert int(hardening["dropped_auth_key_id_mismatch_total"]) == 1
    assert int(snap["pending_count"]) == 1
    service.stop()


def test_ack_ingress_runtime_consumer_can_drop_ack_by_transport_identity_binding():
    bus = InMemoryFabricBus()
    runtime = FabricQuorumRuntimeService.from_policy_settings(
        required_proof_accepts=1,
        required_trust_accepts=1,
        required_validator_ids=["validator-1"],
        enforce_active_validator_membership=True,
        enforce_ack_transport_identity_binding=True,
        validator_transport_identities={"validator-1": ["cn:validator-1"]},
    )
    runtime.register_commit("node-A:1")
    service = FabricAckIngressService(transport=bus, consumer=runtime)
    service.start()
    bad = _ack_env(sender="validator-1").to_dict()
    bad["transport_identity"] = "cn:spoofed"
    bus.publish(FabricEnvelope.from_dict(bad))

    snap = runtime.snapshot()
    hardening = dict(snap["membership_hardening"])
    assert int(hardening["dropped_transport_identity_mismatch_total"]) == 1
    assert int(snap["pending_count"]) == 1
    service.stop()

