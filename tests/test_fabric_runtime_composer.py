from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from detm.runtime.fabric import compose_fabric_handshake_runtime
from detm.runtime.fabric import FabricEnvelope
from detm.runtime.fabric import InMemoryFabricBus
from detm.runtime.fabric import ReplicatedJsonlFabricEnvelopeOutbox


def _mode_channels(_base: str):
    return None


def _rec_stub(tmp_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        out_dir=tmp_path,
        node_id="node-A",
        commit_channel="fabric.commit",
        ack_channel="fabric.ack",
        mode_filter="realtime",
        split_mode_channels=False,
        required_proof_accepts=1,
        required_trust_accepts=1,
        required_unique_proof_validators=1,
        required_unique_trust_validators=1,
        required_validator_ids=[],
        handshake_profile="mvp",
        enforce_required_validator_ids=False,
        enforce_active_validator_membership=False,
        enforce_ack_sender_validator_match=False,
        enforce_ack_auth_key_id_binding=False,
        validator_auth_key_ids={},
        enforce_ack_transport_identity_binding=False,
        validator_transport_identities={},
        reject_on_any_reject=False,
        publish_retry_attempts=1,
        commit_publish_retry_attempts=1,
        delivery_required_receipts=0,
        delivery_guarantee_mode="at_least_once_idempotent",
        delivery_required_validator_ids=[],
        delivery_enforce_required_validator_ids=False,
        delivery_reject_on_any_reject=False,
        delivery_retry_interval_ms=0,
        delivery_max_attempts=1,
        delivery_timeout_ms=100,
        delivery_ack_channel="fabric.delivery.ack",
        delivery_emit_ack=True,
        pending_timeout_ms=None,
        transport="memory",
        transport_host="127.0.0.1",
        transport_port=0,
        transport_connect=False,
        transport_keep_open=False,
        transport_backpressure_max_pending=None,
        transport_backpressure_policy="block",
        transport_backpressure_block_timeout_ms=50,
        transport_dedup_ingress_enabled=False,
        transport_dedup_ttl_ms=30_000,
        transport_dedup_max_entries=10_000,
        transport_auth_enabled=False,
        transport_auth_key=None,
        transport_auth_key_id=None,
        transport_tls_enabled=False,
        transport_tls_server_hostname=None,
        transport_tls_ca_file=None,
        transport_tls_cert_file=None,
        transport_tls_key_file=None,
        transport_tls_require_client_cert=False,
        transport_tls_client_ca_file=None,
        transport_tls_insecure_skip_verify=False,
        transport_tls_identity_source="auto",
        transport_tls_identity_fallback_to_fingerprint=False,
        artifact_store_dir=None,
        publish_inline_payload=True,
        replay_sample_stride=0,
        replay_policy_tier="sampled",
        replay_strict_window_size=128,
        validator_coordination_state_path=None,
        validator_coordination_replica_paths=[],
        validator_coordination_replica_read_quorum=None,
        validator_coordination_replica_write_quorum=None,
        epoch_state_path=None,
        epoch_replica_state_paths=[],
        epoch_replica_read_quorum=None,
        epoch_replica_write_quorum=None,
        epoch_lock_timeout_ms=1000,
        epoch_lock_poll_ms=10,
        epoch_lock_stale_ms=30000,
        epoch_consensus_required_total_accepts=1,
        epoch_consensus_timeout_ms=100,
        epoch_consensus_max_attempts=1,
        epoch_consensus_reject_on_any_reject=False,
        epoch_consensus_channel="fabric.epoch",
        epoch_consensus_enabled=False,
        delivery_outbox_path=None,
        delivery_outbox_max_entries=None,
        delivery_outbox_flush_limit=None,
        delivery_outbox_drop_policy="audit_first",
    )


def test_runtime_composer_builds_components_for_memory_transport(tmp_path):
    rec = _rec_stub(tmp_path)

    composition = compose_fabric_handshake_runtime(
        rec=rec,
        mode_channels=_mode_channels,
    )

    assert composition.transport is not None
    assert composition.service is not None
    assert composition.ack_runtime is not None
    assert composition.delivery_runtime is not None
    assert composition.commit_ingress is not None
    assert composition.quorum_runtime is not None
    assert composition.runtime_bundle is not None

    composition.runtime_bundle.start()
    composition.runtime_bundle.stop()


def test_runtime_composer_uses_replicated_outbox_when_replica_paths_provided(tmp_path):
    rec = _rec_stub(tmp_path)
    rec.delivery_outbox_replica_paths = [
        str(tmp_path / "replica_a.jsonl"),
        str(tmp_path / "replica_b.jsonl"),
        str(tmp_path / "replica_c.jsonl"),
    ]
    rec.delivery_outbox_replica_read_quorum = 2
    rec.delivery_outbox_replica_write_quorum = 2

    composition = compose_fabric_handshake_runtime(
        rec=rec,
        mode_channels=_mode_channels,
    )

    assert isinstance(composition.delivery_outbox, ReplicatedJsonlFabricEnvelopeOutbox)
    composition.runtime_bundle.start()
    composition.runtime_bundle.stop()


def test_runtime_composer_forwards_transport_security_settings(monkeypatch, tmp_path):
    rec = _rec_stub(tmp_path)
    rec.transport = "tcp"
    rec.transport_port = 32001
    rec.transport_connect = True
    rec.transport_dedup_ingress_enabled = True
    rec.transport_dedup_ttl_ms = 1234
    rec.transport_dedup_max_entries = 4321
    rec.transport_auth_enabled = True
    rec.transport_auth_key = "secret"
    rec.transport_auth_key_id = "kid-1"
    rec.transport_tls_enabled = True
    rec.transport_tls_server_hostname = "node.local"
    rec.transport_tls_ca_file = "ca.pem"
    rec.transport_tls_cert_file = "cert.pem"
    rec.transport_tls_key_file = "key.pem"
    rec.transport_tls_require_client_cert = True
    rec.transport_tls_client_ca_file = "client-ca.pem"
    rec.transport_tls_insecure_skip_verify = True
    rec.transport_tls_identity_source = "san"
    rec.transport_tls_identity_fallback_to_fingerprint = True

    seen: dict[str, object] = {}

    def _fake_open_fabric_transport(**kwargs):
        seen.update(kwargs)
        return InMemoryFabricBus()

    monkeypatch.setattr("detm.runtime.fabric.runtime_composer.composer.open_fabric_transport", _fake_open_fabric_transport)
    composition = compose_fabric_handshake_runtime(
        rec=rec,
        mode_channels=_mode_channels,
    )
    try:
        assert seen.get("transport") == "tcp"
        assert seen.get("connect") is True
        assert int(seen.get("dedup_ttl_ms", 0)) == 1234
        assert int(seen.get("dedup_max_entries", 0)) == 4321
        assert seen.get("auth_enabled") is True
        assert seen.get("auth_key") == "secret"
        assert seen.get("auth_key_id") == "kid-1"
        assert seen.get("tls_enabled") is True
        assert seen.get("tls_server_hostname") == "node.local"
        assert seen.get("tls_ca_file") == "ca.pem"
        assert seen.get("tls_cert_file") == "cert.pem"
        assert seen.get("tls_key_file") == "key.pem"
        assert seen.get("tls_require_client_cert") is True
        assert seen.get("tls_client_ca_file") == "client-ca.pem"
        assert seen.get("tls_insecure_skip_verify") is True
        assert seen.get("tls_identity_source") == "san"
        assert seen.get("tls_identity_fallback_to_fingerprint") is True
    finally:
        composition.transport.close()


def test_runtime_composer_forwards_membership_hardening_settings(monkeypatch, tmp_path):
    rec = _rec_stub(tmp_path)
    rec.required_validator_ids = ["validator-1"]
    rec.enforce_required_validator_ids = True
    rec.enforce_active_validator_membership = True
    rec.enforce_ack_sender_validator_match = True
    rec.enforce_ack_auth_key_id_binding = True
    rec.validator_auth_key_ids = {"validator-1": ["kid-1"]}
    rec.enforce_ack_transport_identity_binding = True
    rec.validator_transport_identities = {"validator-1": ["cn:validator-1"]}

    seen: dict[str, object] = {}

    real_from_policy = (
        __import__("detm.runtime.fabric.quorum_runtime", fromlist=["FabricQuorumRuntimeService"])
        .FabricQuorumRuntimeService.from_policy_settings
    )

    def _wrapped_from_policy_settings(**kwargs):
        seen.update(kwargs)
        return real_from_policy(**kwargs)

    monkeypatch.setattr(
        "detm.runtime.fabric.runtime_composer.composer.FabricQuorumRuntimeService.from_policy_settings",
        _wrapped_from_policy_settings,
    )

    composition = compose_fabric_handshake_runtime(
        rec=rec,
        mode_channels=_mode_channels,
    )
    try:
        assert seen.get("enforce_required_validator_ids") is True
        assert seen.get("enforce_active_validator_membership") is True
        assert seen.get("enforce_ack_sender_validator_match") is True
        assert seen.get("enforce_ack_auth_key_id_binding") is True
        assert seen.get("validator_auth_key_ids") == {"validator-1": ["kid-1"]}
        assert seen.get("enforce_ack_transport_identity_binding") is True
        assert seen.get("validator_transport_identities") == {"validator-1": ["cn:validator-1"]}
    finally:
        composition.transport.close()


def test_runtime_composer_forwards_delivery_guarantee_mode(tmp_path):
    rec = _rec_stub(tmp_path)
    rec.delivery_guarantee_mode = "at_least_once"
    rec.transport_dedup_ingress_enabled = True
    rec.delivery_required_receipts = 1

    composition = compose_fabric_handshake_runtime(
        rec=rec,
        mode_channels=_mode_channels,
    )
    try:
        assert composition.quorum_report_builder.delivery_guarantee_mode == "at_least_once"
        assert composition.quorum_report_builder.transport_dedup_ingress_enabled is True
    finally:
        composition.transport.close()


def test_runtime_composer_sets_replay_policy_tier_on_validator(tmp_path):
    rec = _rec_stub(tmp_path)
    rec.replay_policy_tier = "strict_window"
    rec.replay_strict_window_size = 3
    rec.replay_sample_stride = 0

    composition = compose_fabric_handshake_runtime(
        rec=rec,
        mode_channels=_mode_channels,
    )
    try:
        policy = composition.validator.replay_policy
        assert policy.normalized_tier() == "strict_window"
        assert int(policy.strict_window_size) == 3
        assert policy.should_check(
            __import__("detm.runtime.commit_packet", fromlist=["CommitPacket"]).CommitPacket.from_dict(
                {
                    "commit_type": "state",
                    "mode": "realtime",
                    "node_id": "node-A",
                    "commit_id": "node-A:1",
                    "tick_ref": {"base_level": "L0", "tick": 1},
                    "delta_ref": "artifact://delta/1",
                    "trace_ref": "trace://run/1",
                    "signature": "sig://node-A/1",
                }
            )
        )
    finally:
        composition.transport.close()


def test_runtime_composer_forwards_handshake_profile_to_report(tmp_path):
    rec = _rec_stub(tmp_path)
    rec.handshake_profile = "production"

    composition = compose_fabric_handshake_runtime(
        rec=rec,
        mode_channels=_mode_channels,
    )
    try:
        report = composition.quorum_report_builder.build(
            replay_sample_stride=0,
            replay_checks_total=0,
            replay_checks_failed=0,
        )
        profile = dict(report["handshake_profile"])
        assert str(profile["profile"]) == "production"
    finally:
        composition.transport.close()


def test_runtime_composer_sets_epoch_consensus_max_attempts(tmp_path):
    rec = _rec_stub(tmp_path)
    rec.epoch_consensus_enabled = True
    rec.epoch_consensus_required_total_accepts = 2
    rec.epoch_consensus_timeout_ms = 50
    rec.epoch_consensus_max_attempts = 3

    composition = compose_fabric_handshake_runtime(
        rec=rec,
        mode_channels=_mode_channels,
    )
    try:
        assert composition.epoch_consensus is not None
        snap = composition.epoch_consensus.snapshot()
        consensus = dict(snap["consensus"])
        assert int(consensus["required_total_accepts"]) == 2
        assert int(consensus["timeout_ms"]) == 50
        assert int(consensus["max_attempts"]) == 3
    finally:
        composition.runtime_bundle.stop()


def test_runtime_composer_forwards_validator_coordination_settings(monkeypatch, tmp_path):
    rec = _rec_stub(tmp_path)
    rec.validator_coordination_state_path = str(tmp_path / "validator_coordination_state.json")
    rec.validator_coordination_replica_paths = [
        str(tmp_path / "coord_a.json"),
        str(tmp_path / "coord_b.json"),
        str(tmp_path / "coord_c.json"),
    ]
    rec.validator_coordination_replica_read_quorum = 2
    rec.validator_coordination_replica_write_quorum = 2

    seen: dict[str, object] = {}

    real_from_policy = (
        __import__("detm.runtime.fabric.quorum_runtime", fromlist=["FabricQuorumRuntimeService"])
        .FabricQuorumRuntimeService.from_policy_settings
    )

    def _wrapped_from_policy_settings(**kwargs):
        seen.update(kwargs)
        return real_from_policy(**kwargs)

    monkeypatch.setattr(
        "detm.runtime.fabric.runtime_composer.composer.FabricQuorumRuntimeService.from_policy_settings",
        _wrapped_from_policy_settings,
    )
    composition = compose_fabric_handshake_runtime(
        rec=rec,
        mode_channels=_mode_channels,
    )
    try:
        assert seen.get("validator_coordination_state_path") == str(tmp_path / "validator_coordination_state.json")
        assert seen.get("validator_coordination_replica_paths") == [
            str(tmp_path / "coord_a.json"),
            str(tmp_path / "coord_b.json"),
            str(tmp_path / "coord_c.json"),
        ]
        assert int(seen.get("validator_coordination_replica_read_quorum", 0)) == 2
        assert int(seen.get("validator_coordination_replica_write_quorum", 0)) == 2
    finally:
        composition.transport.close()


def test_runtime_composer_sets_default_delivery_tracking_state_path(tmp_path):
    rec = _rec_stub(tmp_path)
    rec.delivery_required_receipts = 1

    composition = compose_fabric_handshake_runtime(
        rec=rec,
        mode_channels=_mode_channels,
    )
    try:
        state_path = Path(str(composition.delivery_tracker.state_path or ""))
        assert state_path == (tmp_path / "fabric_delivery_tracking_state.json")

        env = FabricEnvelope.from_dict(
            {
                "message_type": "commit",
                "channel": "fabric.commit",
                "mode": "realtime",
                "sender": "node-A",
                "payload_ref": "artifact://commit/node-A/durable",
                "commit_ref": "node-A:durable",
                "delivery_id": "node-A:durable:1",
            }
        )
        composition.delivery_tracker.register_delivery(env, now_ms=1)
        composition.delivery_tracker.mark_publish_attempt("node-A:durable:1", now_ms=2)
        assert state_path.exists()
    finally:
        composition.transport.close()

