"""Runtime builder for fabric quorum report payload."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, Sequence

from detm.runtime.fabric_commit_delivery import FabricCommitDeliveryService
from detm.runtime.fabric_quorum_runtime import FabricQuorumRuntimeService

# ARCH-MARKERS:
# - LAYER_BAND: L5
# - ABSTRACT_DISTANCE: 0 (report composition extracted from subscriber orchestration)
# - OOP_TECH_DEBT: distributed report aggregation and signed multi-node report bundles


class SnapshotProvider(Protocol):
    def snapshot(self) -> object:
        ...


class ToDictProvider(Protocol):
    def to_dict(self) -> dict[str, object]:
        ...


@dataclass
class FabricQuorumReportBuilder:
    """Builds `fabric_quorum_report.json` payload from runtime components."""

    quorum_runtime: FabricQuorumRuntimeService | None = None
    artifact_store: ToDictProvider | None = None
    publish_inline_payload: bool = True
    split_mode_channels: bool = False
    commit_channels_by_mode: dict[str, str] | None = None
    ack_channels_by_mode: dict[str, str] | None = None
    delivery_ack_channels_by_mode: dict[str, str] | None = None
    mode_filter: str | None = None
    transport: SnapshotProvider | None = None
    delivery_outbox: SnapshotProvider | None = None
    delivery_runtime: FabricCommitDeliveryService | None = None
    delivery_required_receipts: int = 0
    delivery_required_validator_ids: Sequence[str] | None = None
    delivery_enforce_required_validator_ids: bool = False
    delivery_reject_on_any_reject: bool = False
    delivery_retry_interval_ms: int = 100
    delivery_max_attempts: int = 3
    delivery_timeout_ms: int = 500
    epoch_coordinator: SnapshotProvider | None = None

    def _epoch_snapshot(self) -> dict[str, object] | None:
        if self.epoch_coordinator is None:
            return None
        try:
            snap = self.epoch_coordinator.snapshot()
            return snap if isinstance(snap, dict) else {"snapshot": snap}
        except Exception as exc:
            return {"error": str(exc)}

    def _transport_backpressure(self) -> dict[str, object]:
        if self.transport is None or not hasattr(self.transport, "snapshot"):
            return {"enabled": False}
        try:
            snap = self.transport.snapshot()
            if isinstance(snap, dict):
                return snap
            return {"enabled": True, "snapshot": snap}
        except Exception as exc:
            return {"enabled": True, "error": str(exc)}

    def _delivery_tracking(self) -> dict[str, object]:
        if self.delivery_runtime is None:
            return {
                "enabled": False,
                "accepted_count": 0,
                "rejected_count": 0,
                "pending_count": 0,
                "retries_total": 0,
                "pending": [],
            }
        snap = self.delivery_runtime.snapshot()
        return {
            "enabled": bool(self.delivery_runtime.delivery_tracking_enabled()),
            "accepted_count": int(snap.get("accepted_count", 0)),
            "rejected_count": int(snap.get("rejected_count", 0)),
            "pending_count": int(snap.get("pending_count", 0)),
            "retries_total": int(snap.get("retries_total", 0)),
            "pending": list(snap.get("pending", [])),
        }

    def build(
        self,
        *,
        replay_sample_stride: int,
        replay_checks_total: int,
        replay_checks_failed: int,
    ) -> dict[str, object]:
        quorum_report = self.quorum_runtime.snapshot() if self.quorum_runtime is not None else {}
        if not isinstance(quorum_report, dict):
            quorum_report = {"snapshot": quorum_report}

        quorum_report["artifact_store"] = (
            self.artifact_store.to_dict() if self.artifact_store is not None else None
        )
        quorum_report["publish_inline_payload"] = bool(self.publish_inline_payload)
        quorum_report["mode_channels"] = {
            "split_mode_channels": bool(self.split_mode_channels),
            "commit_channels_by_mode": self.commit_channels_by_mode,
            "ack_channels_by_mode": self.ack_channels_by_mode,
            "delivery_ack_channels_by_mode": self.delivery_ack_channels_by_mode,
            "mode_filter": self.mode_filter,
        }
        quorum_report["transport_backpressure"] = self._transport_backpressure()
        quorum_report["delivery_outbox"] = (
            self.delivery_outbox.snapshot() if self.delivery_outbox is not None else {"enabled": False}
        )

        delivery_tracking = self._delivery_tracking()
        quorum_report["delivery_receipts"] = {
            "enabled": bool(delivery_tracking.get("enabled", False)),
            "required_receipts": int(self.delivery_required_receipts),
            "required_validator_ids": sorted(
                {str(v).strip() for v in list(self.delivery_required_validator_ids or []) if str(v).strip()}
            ),
            "enforce_required_validator_ids": bool(self.delivery_enforce_required_validator_ids),
            "reject_on_any_reject": bool(self.delivery_reject_on_any_reject),
            "retry_interval_ms": int(self.delivery_retry_interval_ms),
            "max_attempts": int(self.delivery_max_attempts),
            "timeout_ms": int(self.delivery_timeout_ms),
            "accepted_count": int(delivery_tracking.get("accepted_count", 0)),
            "rejected_count": int(delivery_tracking.get("rejected_count", 0)),
            "pending_count": int(delivery_tracking.get("pending_count", 0)),
            "retries_total": int(delivery_tracking.get("retries_total", 0)),
            "pending": list(delivery_tracking.get("pending", [])),
        }
        quorum_report["epoch_watermark"] = self._epoch_snapshot()
        quorum_report["replay_sampling"] = {
            "enabled": bool(int(replay_sample_stride) > 0),
            "sample_stride": int(replay_sample_stride),
            "checks_total": int(replay_checks_total),
            "checks_failed": int(replay_checks_failed),
        }
        return quorum_report


__all__ = ["FabricQuorumReportBuilder", "SnapshotProvider", "ToDictProvider"]
