from __future__ import annotations

from detm.runtime.fabric_handshake_recorder_config import normalize_fabric_handshake_recorder_attach_kwargs


def test_normalize_fabric_handshake_recorder_attach_kwargs_clamps_and_filters():
    cfg = normalize_fabric_handshake_recorder_attach_kwargs(
        required_proof_accepts=0,
        required_trust_accepts=-2,
        delivery_required_receipts=-5,
        delivery_retry_interval_ms=-10,
        delivery_max_attempts=0,
        delivery_timeout_ms=0,
        pending_timeout_ms=-1,
        transport_backpressure_max_pending=0,
        transport_backpressure_block_timeout_ms=-7,
        replay_sample_stride=-3,
        epoch_replica_read_quorum=0,
        epoch_replica_write_quorum=0,
        epoch_lock_timeout_ms=0,
        epoch_lock_poll_ms=0,
        epoch_lock_stale_ms=0,
        epoch_consensus_required_total_accepts=0,
        epoch_consensus_timeout_ms=0,
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
    )

    assert int(cfg["required_proof_accepts"]) == 1
    assert int(cfg["required_trust_accepts"]) == 1
    assert int(cfg["delivery_required_receipts"]) == 0
    assert int(cfg["delivery_retry_interval_ms"]) == 0
    assert int(cfg["delivery_max_attempts"]) == 1
    assert int(cfg["delivery_timeout_ms"]) == 1
    assert int(cfg["pending_timeout_ms"]) == 0
    assert int(cfg["transport_backpressure_max_pending"]) == 1
    assert int(cfg["transport_backpressure_block_timeout_ms"]) == 0
    assert int(cfg["replay_sample_stride"]) == 0
    assert int(cfg["epoch_replica_read_quorum"]) == 1
    assert int(cfg["epoch_replica_write_quorum"]) == 1
    assert int(cfg["epoch_lock_timeout_ms"]) == 1
    assert int(cfg["epoch_lock_poll_ms"]) == 1
    assert int(cfg["epoch_lock_stale_ms"]) == 1
    assert int(cfg["epoch_consensus_required_total_accepts"]) == 1
    assert int(cfg["epoch_consensus_timeout_ms"]) == 1
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


def test_normalize_fabric_handshake_recorder_attach_kwargs_policies_and_paths():
    cfg = normalize_fabric_handshake_recorder_attach_kwargs(
        transport_backpressure_policy="unknown",
        delivery_outbox_drop_policy="invalid",
        artifact_store_dir=" ",
        delivery_outbox_path=" ",
        epoch_state_path=" ",
        mode_filter=None,
    )

    assert str(cfg["transport_backpressure_policy"]) == "block"
    assert str(cfg["delivery_outbox_drop_policy"]) == "audit_first"
    assert cfg["artifact_store_dir"] is None
    assert cfg["delivery_outbox_path"] is None
    assert cfg["epoch_state_path"] is None
    assert cfg["mode_filter"] is None
