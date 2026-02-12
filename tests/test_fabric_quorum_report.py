from __future__ import annotations

from detm.runtime.fabric_quorum_report import FabricQuorumReportBuilder


class _QuorumRuntime:
    def snapshot(self) -> dict[str, object]:
        return {
            "accepted_count": 1,
            "pending_count": 0,
            "rejected_count": 0,
            "validator_registry": {"validators": ["validator-1"]},
            "pending_timeout_ms": 200,
        }


class _ArtifactStore:
    def to_dict(self) -> dict[str, object]:
        return {"root_dir": "artifacts"}


class _Transport:
    def snapshot(self) -> dict[str, object]:
        return {"enabled": True, "policy": "drop_newest", "max_pending": 8}


class _FailingTransport:
    def snapshot(self) -> dict[str, object]:
        raise RuntimeError("transport snapshot failed")


class _Outbox:
    def snapshot(self) -> dict[str, object]:
        return {"enabled": True, "pending_count": 2}


class _DeliveryRuntime:
    def delivery_tracking_enabled(self) -> bool:
        return True

    def snapshot(self) -> dict[str, object]:
        return {
            "accepted_count": 3,
            "rejected_count": 1,
            "pending_count": 2,
            "retries_total": 7,
            "pending": [{"delivery_id": "d1"}],
        }


class _Epoch:
    def snapshot(self) -> dict[str, object]:
        return {"global": {"epoch": 10, "watermark": 10}}


def test_quorum_report_builder_builds_expected_sections():
    builder = FabricQuorumReportBuilder(
        quorum_runtime=_QuorumRuntime(),  # type: ignore[arg-type]
        artifact_store=_ArtifactStore(),  # type: ignore[arg-type]
        publish_inline_payload=False,
        split_mode_channels=True,
        commit_channels_by_mode={"realtime": "fabric.commit.realtime"},
        ack_channels_by_mode={"realtime": "fabric.ack.realtime"},
        delivery_ack_channels_by_mode={"realtime": "fabric.delivery.ack.realtime"},
        mode_filter="realtime",
        transport=_Transport(),  # type: ignore[arg-type]
        delivery_outbox=_Outbox(),  # type: ignore[arg-type]
        delivery_runtime=_DeliveryRuntime(),  # type: ignore[arg-type]
        delivery_required_receipts=2,
        delivery_required_validator_ids=["validator-1"],
        delivery_enforce_required_validator_ids=True,
        delivery_reject_on_any_reject=True,
        delivery_retry_interval_ms=10,
        delivery_max_attempts=5,
        delivery_timeout_ms=300,
        epoch_coordinator=_Epoch(),  # type: ignore[arg-type]
    )

    report = builder.build(replay_sample_stride=2, replay_checks_total=5, replay_checks_failed=1)
    assert int(report["accepted_count"]) == 1
    assert dict(report["artifact_store"]) == {"root_dir": "artifacts"}
    assert bool(report["publish_inline_payload"]) is False
    assert bool(report["mode_channels"]["split_mode_channels"]) is True
    assert dict(report["transport_backpressure"]) == {"enabled": True, "policy": "drop_newest", "max_pending": 8}
    assert dict(report["delivery_outbox"]) == {"enabled": True, "pending_count": 2}
    delivery = dict(report["delivery_receipts"])
    assert bool(delivery["enabled"]) is True
    assert int(delivery["accepted_count"]) == 3
    assert int(delivery["retries_total"]) == 7
    assert list(delivery["required_validator_ids"]) == ["validator-1"]
    assert dict(report["epoch_watermark"]) == {"global": {"epoch": 10, "watermark": 10}}
    replay = dict(report["replay_sampling"])
    assert bool(replay["enabled"]) is True
    assert int(replay["checks_total"]) == 5
    assert int(replay["checks_failed"]) == 1


def test_quorum_report_builder_transport_and_epoch_errors_are_reported():
    class _FailingEpoch:
        def snapshot(self) -> dict[str, object]:
            raise RuntimeError("epoch snapshot failed")

    builder = FabricQuorumReportBuilder(
        quorum_runtime=_QuorumRuntime(),  # type: ignore[arg-type]
        transport=_FailingTransport(),  # type: ignore[arg-type]
        epoch_coordinator=_FailingEpoch(),  # type: ignore[arg-type]
    )
    report = builder.build(replay_sample_stride=0, replay_checks_total=0, replay_checks_failed=0)
    backpressure = dict(report["transport_backpressure"])
    assert bool(backpressure["enabled"]) is True
    assert "transport snapshot failed" in str(backpressure["error"])
    epoch = dict(report["epoch_watermark"])
    assert "epoch snapshot failed" in str(epoch["error"])
