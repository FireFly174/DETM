from __future__ import annotations

from detm.runtime.fabric import normalize_fabric_handshake_recorder_attach_kwargs


def test_normalize_fabric_handshake_recorder_attach_kwargs_clamps_and_filters():
    cfg = normalize_fabric_handshake_recorder_attach_kwargs(
        required_proof_accepts=0,
        required_trust_accepts=-2,
        enforce_active_validator_membership=True,
        enforce_ack_sender_validator_match=True,
        enforce_ack_auth_key_id_binding=True,
        validator_auth_key_ids=[
            "validator.a = key-a",
            "validator.b:key-b",
            "validator.b=key-b2",
            " ",
        ],
        enforce_ack_transport_identity_binding=True,
        validator_transport_identities=[
            "validator.a=cn:validator-a",
            "validator.b=sha256:abc",
            "validator.b=sha256:def",
        ],
        delivery_required_receipts=-5,
        delivery_guarantee_mode="AT-LEAST-ONCE",
        delivery_retry_interval_ms=-10,
        delivery_max_attempts=0,
        delivery_timeout_ms=0,
        pending_timeout_ms=-1,
        transport_backpressure_max_pending=0,
        transport_backpressure_block_timeout_ms=-7,
        transport_dedup_ttl_ms=0,
        transport_dedup_max_entries=0,
        transport_auth_key="  secret  ",
        transport_auth_key_id=" kid-1 ",
        transport_tls_server_hostname=" node.local ",
        transport_tls_ca_file=" ca.pem ",
        transport_tls_cert_file=" cert.pem ",
        transport_tls_key_file=" key.pem ",
        transport_tls_require_client_cert=True,
        transport_tls_client_ca_file=" client-ca.pem ",
        transport_tls_identity_source=" SAN ",
        transport_tls_identity_fallback_to_fingerprint=True,
        replay_sample_stride=-3,
        replay_policy_tier="strict-window",
        replay_strict_window_size=0,
        validator_coordination_state_path=" vc_state.json ",
        validator_coordination_replica_paths=["vc_a.json", " ", ""],
        validator_coordination_replica_read_quorum=0,
        validator_coordination_replica_write_quorum=0,
        epoch_replica_read_quorum=0,
        epoch_replica_write_quorum=0,
        epoch_lock_timeout_ms=0,
        epoch_lock_poll_ms=0,
        epoch_lock_stale_ms=0,
        epoch_consensus_required_total_accepts=0,
        epoch_consensus_timeout_ms=0,
        epoch_consensus_max_attempts=0,
        delivery_outbox_replica_read_quorum=0,
        delivery_outbox_replica_write_quorum=0,
        delivery_outbox_max_entries=0,
        delivery_outbox_flush_limit=0,
        fabric_acks_retention_window=-1,
        fabric_acks_compaction_budget=-2,
        fabric_ack_envelopes_retention_window=-3,
        fabric_ack_envelopes_compaction_budget=-4,
        fabric_delivery_acks_retention_window=-5,
        fabric_delivery_acks_compaction_budget=-6,
        fabric_dead_letters_retention_window=-7,
        fabric_dead_letters_compaction_budget=-8,
        fabric_quorum_report_retention_window=-9,
        fabric_quorum_report_compaction_budget=-10,
        required_validator_ids=["validator.a", " ", "", "validator.b"],
        delivery_required_validator_ids=["validator.c", " ", ""],
        epoch_replica_state_paths=["r1.json", " ", ""],
        delivery_outbox_replica_paths=["o1.jsonl", " ", ""],
    )

    assert int(cfg["required_proof_accepts"]) == 1
    assert int(cfg["required_trust_accepts"]) == 1
    assert bool(cfg["enforce_active_validator_membership"]) is True
    assert bool(cfg["enforce_ack_sender_validator_match"]) is True
    assert bool(cfg["enforce_ack_auth_key_id_binding"]) is True
    assert dict(cfg["validator_auth_key_ids"]) == {
        "validator.a": ["key-a"],
        "validator.b": ["key-b", "key-b2"],
    }
    assert bool(cfg["enforce_ack_transport_identity_binding"]) is True
    assert dict(cfg["validator_transport_identities"]) == {
        "validator.a": ["cn:validator-a"],
        "validator.b": ["sha256:abc", "sha256:def"],
    }
    assert int(cfg["delivery_required_receipts"]) == 0
    assert str(cfg["delivery_guarantee_mode"]) == "at_least_once"
    assert int(cfg["delivery_retry_interval_ms"]) == 0
    assert int(cfg["delivery_max_attempts"]) == 1
    assert int(cfg["delivery_timeout_ms"]) == 1
    assert int(cfg["pending_timeout_ms"]) == 0
    assert int(cfg["transport_backpressure_max_pending"]) == 1
    assert int(cfg["transport_backpressure_block_timeout_ms"]) == 0
    assert int(cfg["transport_dedup_ttl_ms"]) == 1
    assert int(cfg["transport_dedup_max_entries"]) == 1
    assert str(cfg["transport_auth_key"]) == "  secret  "
    assert str(cfg["transport_auth_key_id"]) == "kid-1"
    assert str(cfg["transport_tls_server_hostname"]) == "node.local"
    assert str(cfg["transport_tls_ca_file"]) == "ca.pem"
    assert str(cfg["transport_tls_cert_file"]) == "cert.pem"
    assert str(cfg["transport_tls_key_file"]) == "key.pem"
    assert bool(cfg["transport_tls_require_client_cert"]) is True
    assert str(cfg["transport_tls_client_ca_file"]) == "client-ca.pem"
    assert str(cfg["transport_tls_identity_source"]) == "san"
    assert bool(cfg["transport_tls_identity_fallback_to_fingerprint"]) is True
    assert int(cfg["replay_sample_stride"]) == 0
    assert str(cfg["replay_policy_tier"]) == "strict_window"
    assert int(cfg["replay_strict_window_size"]) == 1
    assert str(cfg["validator_coordination_state_path"]) == "vc_state.json"
    assert list(cfg["validator_coordination_replica_paths"]) == ["vc_a.json"]
    assert int(cfg["validator_coordination_replica_read_quorum"]) == 1
    assert int(cfg["validator_coordination_replica_write_quorum"]) == 1
    assert int(cfg["epoch_replica_read_quorum"]) == 1
    assert int(cfg["epoch_replica_write_quorum"]) == 1
    assert int(cfg["epoch_lock_timeout_ms"]) == 1
    assert int(cfg["epoch_lock_poll_ms"]) == 1
    assert int(cfg["epoch_lock_stale_ms"]) == 1
    assert int(cfg["epoch_consensus_required_total_accepts"]) == 1
    assert int(cfg["epoch_consensus_timeout_ms"]) == 1
    assert int(cfg["epoch_consensus_max_attempts"]) == 1
    assert int(cfg["delivery_outbox_replica_read_quorum"]) == 1
    assert int(cfg["delivery_outbox_replica_write_quorum"]) == 1
    assert int(cfg["delivery_outbox_max_entries"]) == 1
    assert int(cfg["delivery_outbox_flush_limit"]) == 1
    assert int(cfg["fabric_acks_retention_window"]) == 0
    assert int(cfg["fabric_acks_compaction_budget"]) == 0
    assert int(cfg["fabric_ack_envelopes_retention_window"]) == 0
    assert int(cfg["fabric_ack_envelopes_compaction_budget"]) == 0
    assert int(cfg["fabric_delivery_acks_retention_window"]) == 0
    assert int(cfg["fabric_delivery_acks_compaction_budget"]) == 0
    assert int(cfg["fabric_dead_letters_retention_window"]) == 0
    assert int(cfg["fabric_dead_letters_compaction_budget"]) == 0
    assert int(cfg["fabric_quorum_report_retention_window"]) == 0
    assert int(cfg["fabric_quorum_report_compaction_budget"]) == 0
    assert list(cfg["required_validator_ids"]) == ["validator.a", "validator.b"]
    assert list(cfg["delivery_required_validator_ids"]) == ["validator.c"]
    assert list(cfg["epoch_replica_state_paths"]) == ["r1.json"]
    assert list(cfg["delivery_outbox_replica_paths"]) == ["o1.jsonl"]


def test_normalize_fabric_handshake_recorder_attach_kwargs_policies_and_paths():
    cfg = normalize_fabric_handshake_recorder_attach_kwargs(
        transport_backpressure_policy="unknown",
        delivery_outbox_drop_policy="invalid",
        enforce_active_validator_membership=False,
        enforce_ack_sender_validator_match=False,
        enforce_ack_auth_key_id_binding=False,
        validator_auth_key_ids={"validator.a": "key-a,key-a2", "validator.b": ["key-b", ""]},
        enforce_ack_transport_identity_binding=False,
        validator_transport_identities="validator.a=cn:a,validator.b=cn:b",
        transport_dedup_ingress_enabled=True,
        delivery_guarantee_mode="unknown-mode",
        transport_auth_enabled=True,
        transport_auth_key=" ",
        transport_auth_key_id=" ",
        transport_tls_enabled=True,
        transport_tls_server_hostname=" ",
        transport_tls_ca_file=" ",
        transport_tls_cert_file=" ",
        transport_tls_key_file=" ",
        transport_tls_require_client_cert=False,
        transport_tls_client_ca_file=" ",
        transport_tls_insecure_skip_verify=True,
        transport_tls_identity_source="unknown",
        transport_tls_identity_fallback_to_fingerprint=False,
        replay_policy_tier="unknown-tier",
        replay_strict_window_size=-5,
        validator_coordination_state_path=" ",
        validator_coordination_replica_paths=[" ", ""],
        artifact_store_dir=" ",
        delivery_tracking_state_path=" ",
        delivery_outbox_path=" ",
        epoch_state_path=" ",
        mode_filter=None,
    )

    assert str(cfg["transport_backpressure_policy"]) == "block"
    assert str(cfg["delivery_outbox_drop_policy"]) == "audit_first"
    assert cfg["enforce_active_validator_membership"] is False
    assert cfg["enforce_ack_sender_validator_match"] is False
    assert cfg["enforce_ack_auth_key_id_binding"] is False
    assert dict(cfg["validator_auth_key_ids"]) == {
        "validator.a": ["key-a", "key-a2"],
        "validator.b": ["key-b"],
    }
    assert cfg["enforce_ack_transport_identity_binding"] is False
    assert dict(cfg["validator_transport_identities"]) == {
        "validator.a": ["cn:a"],
        "validator.b": ["cn:b"],
    }
    assert cfg["transport_dedup_ingress_enabled"] is True
    assert cfg["delivery_guarantee_mode"] == "at_least_once_idempotent"
    assert cfg["transport_auth_enabled"] is True
    assert cfg["transport_auth_key"] is None
    assert cfg["transport_auth_key_id"] is None
    assert cfg["transport_tls_enabled"] is True
    assert cfg["transport_tls_server_hostname"] is None
    assert cfg["transport_tls_ca_file"] is None
    assert cfg["transport_tls_cert_file"] is None
    assert cfg["transport_tls_key_file"] is None
    assert cfg["transport_tls_require_client_cert"] is False
    assert cfg["transport_tls_client_ca_file"] is None
    assert cfg["transport_tls_insecure_skip_verify"] is True
    assert cfg["transport_tls_identity_source"] == "auto"
    assert cfg["transport_tls_identity_fallback_to_fingerprint"] is False
    assert cfg["replay_policy_tier"] == "sampled"
    assert int(cfg["replay_strict_window_size"]) == 1
    assert cfg["validator_coordination_state_path"] is None
    assert list(cfg["validator_coordination_replica_paths"]) == []
    assert cfg["validator_coordination_replica_read_quorum"] is None
    assert cfg["validator_coordination_replica_write_quorum"] is None
    assert cfg["artifact_store_dir"] is None
    assert cfg["delivery_tracking_state_path"] is None
    assert cfg["delivery_outbox_path"] is None
    assert cfg["epoch_state_path"] is None
    assert cfg["mode_filter"] is None


def test_normalize_fabric_handshake_recorder_attach_kwargs_production_profile_enables_hardening():
    cfg = normalize_fabric_handshake_recorder_attach_kwargs(
        handshake_profile="production",
        required_validator_ids=["validator.a", "validator.b"],
        validator_auth_key_ids={"validator.a": "kid-a", "validator.b": "kid-b"},
    )

    assert cfg["handshake_profile"] == "production"
    assert cfg["enforce_required_validator_ids"] is True
    assert cfg["enforce_active_validator_membership"] is True
    assert cfg["enforce_ack_sender_validator_match"] is True
    assert cfg["enforce_ack_auth_key_id_binding"] is True
    assert cfg["enforce_ack_transport_identity_binding"] is False
    assert cfg["reject_on_any_reject"] is True


def test_normalize_fabric_handshake_recorder_attach_kwargs_production_profile_requires_bindings():
    try:
        normalize_fabric_handshake_recorder_attach_kwargs(
            handshake_profile="production",
            required_validator_ids=["validator.a"],
            validator_auth_key_ids={},
            validator_transport_identities={},
        )
    except ValueError as exc:
        assert "requires validator_auth_key_ids and/or validator_transport_identities" in str(exc)
    else:
        raise AssertionError("Expected ValueError for production profile without bindings")


def test_normalize_fabric_handshake_recorder_attach_kwargs_production_profile_requires_binding_coverage():
    try:
        normalize_fabric_handshake_recorder_attach_kwargs(
            handshake_profile="production",
            required_validator_ids=["validator.a", "validator.b"],
            validator_auth_key_ids={"validator.a": "kid-a"},
        )
    except ValueError as exc:
        assert "requires auth key-id bindings for required validators" in str(exc)
    else:
        raise AssertionError("Expected ValueError for incomplete auth binding coverage")

