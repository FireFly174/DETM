from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from detm.runtime.fabric_runtime_composer import compose_fabric_handshake_runtime


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
        enforce_required_validator_ids=False,
        reject_on_any_reject=False,
        publish_retry_attempts=1,
        commit_publish_retry_attempts=1,
        delivery_required_receipts=0,
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
        artifact_store_dir=None,
        publish_inline_payload=True,
        replay_sample_stride=0,
        epoch_state_path=None,
        epoch_replica_state_paths=[],
        epoch_replica_read_quorum=None,
        epoch_replica_write_quorum=None,
        epoch_lock_timeout_ms=1000,
        epoch_lock_poll_ms=10,
        epoch_lock_stale_ms=30000,
        epoch_consensus_required_total_accepts=1,
        epoch_consensus_timeout_ms=100,
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
