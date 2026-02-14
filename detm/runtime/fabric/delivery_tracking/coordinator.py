"""Delivery retry/timeout tracking for commit envelope acknowledged delivery."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict

from detm.runtime.fabric import InMemoryDeliveryReceiptCoordinator
from detm.runtime.fabric.delivery_tracking.contracts import RepublishFn
from detm.runtime.fabric import FabricEnvelope

# ARCH-MARKERS:
# - LAYER_BAND: L5
# - ABSTRACT_DISTANCE: 0 (retry/timeout state-machine extracted as dedicated coordinator)
# - OOP_TECH_DEBT: distributed durable coordinator and replicated commit-delivery state


@dataclass
class DeliveryTrackingCoordinator:
    """Tracks pending commit deliveries and drives retry/timeout transitions."""

    receipt_coordinator: InMemoryDeliveryReceiptCoordinator
    required_receipts: int = 0
    retry_interval_ms: int = 100
    max_attempts: int = 3
    timeout_ms: int = 500
    tracking_enabled: bool = False
    pending: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    accepted_count: int = 0
    rejected_count: int = 0
    retries_total: int = 0
    state_path: str | None = None

    def __post_init__(self) -> None:
        self._load_state()

    def enabled(self) -> bool:
        return bool(self.tracking_enabled)

    def register_delivery(self, envelope: FabricEnvelope, *, now_ms: int | None = None) -> str | None:
        if not self.enabled():
            return None
        delivery_id = str(envelope.delivery_id or "").strip()
        if not delivery_id:
            return None
        row = self.pending.get(delivery_id)
        if row is None:
            now = int(now_ms) if now_ms is not None else int(time.time() * 1000)
            row = {
                "delivery_id": delivery_id,
                "commit_ref": str(envelope.commit_ref or ""),
                "mode": str(envelope.mode),
                "first_sent_ms": 0,
                "last_sent_ms": 0,
                "attempts": 0,
                "envelope": envelope,
                "reason": None,
                "created_at_ms": now,
            }
            self.pending[delivery_id] = row
            self.receipt_coordinator.register_delivery(
                delivery_id,
                commit_ref=str(envelope.commit_ref or ""),
                created_at_ms=now,
            )
            self._persist_state()
        return delivery_id

    def mark_publish_attempt(self, delivery_id: str, *, now_ms: int | None = None) -> None:
        did = str(delivery_id).strip()
        row = self.pending.get(did)
        if row is None:
            return
        now = int(now_ms) if now_ms is not None else int(time.time() * 1000)
        row["attempts"] = int(row.get("attempts", 0)) + 1
        row["last_sent_ms"] = now
        if int(row.get("first_sent_ms", 0)) <= 0:
            row["first_sent_ms"] = now
        self._persist_state()

    def on_delivery_ack_envelope(self, envelope: FabricEnvelope) -> None:
        self.receipt_coordinator.on_delivery_ack_envelope(envelope)
        self._persist_state()

    def tick(self, republish: RepublishFn, *, now_ms: int | None = None) -> None:
        if not self.enabled():
            return
        if not self.pending:
            return
        now = int(now_ms) if now_ms is not None else int(time.time() * 1000)
        timeout_ms = max(1, int(self.timeout_ms))
        max_attempts = max(1, int(self.max_attempts))
        retry_interval_ms = max(0, int(self.retry_interval_ms))
        required_receipts = max(0, int(self.required_receipts))

        to_remove: list[str] = []
        for delivery_id, row in list(self.pending.items()):
            eval_row = self.receipt_coordinator.evaluate(delivery_id)
            status = str(eval_row.get("status", "pending"))
            reason = None if eval_row.get("reason") is None else str(eval_row.get("reason"))
            accepted_senders = [str(v) for v in list(eval_row.get("accepted_senders", []))]
            missing_required = [str(v) for v in list(eval_row.get("missing_required_validators", []))]
            if status == "accepted":
                self.accepted_count += 1
                to_remove.append(delivery_id)
                continue
            if status == "rejected":
                row["reason"] = reason or "delivery rejected by receipt policy"
                self.rejected_count += 1
                to_remove.append(delivery_id)
                continue

            first_sent = int(row.get("first_sent_ms", 0))
            if first_sent <= 0:
                first_sent = int(row.get("created_at_ms", now))
            last_sent = int(row.get("last_sent_ms", first_sent))
            attempts = int(row.get("attempts", 0))

            if (now - first_sent) >= timeout_ms:
                row["reason"] = f"delivery timeout ({now - first_sent}ms >= {timeout_ms}ms)"
                self.rejected_count += 1
                to_remove.append(delivery_id)
                continue
            if attempts >= max_attempts:
                row["reason"] = f"delivery max attempts exceeded ({attempts} >= {max_attempts})"
                self.rejected_count += 1
                to_remove.append(delivery_id)
                continue

            if (now - last_sent) < retry_interval_ms:
                continue
            env = row.get("envelope")
            if not isinstance(env, FabricEnvelope):
                row["reason"] = "delivery retry failed: envelope missing"
                self.rejected_count += 1
                to_remove.append(delivery_id)
                continue
            self.mark_publish_attempt(delivery_id, now_ms=now)
            if bool(republish(env)):
                self.retries_total += 1
            if int(row.get("attempts", 0)) >= max_attempts:
                row["reason"] = (
                    f"delivery max attempts exceeded ({int(row.get('attempts', 0))} >= {max_attempts}); "
                    f"accepted={len(accepted_senders)}/{required_receipts}, missing_required={missing_required}"
                )
                self.rejected_count += 1
                to_remove.append(delivery_id)

        for delivery_id in to_remove:
            self.pending.pop(delivery_id, None)
            self.receipt_coordinator.remove(delivery_id)
        self._persist_state()

    def snapshot(self) -> Dict[str, object]:
        pending_rows: list[dict[str, object]] = []
        for row in list(self.pending.values()):
            delivery_id = str(row.get("delivery_id", ""))
            eval_row = self.receipt_coordinator.evaluate(delivery_id)
            pending_rows.append(
                {
                    "delivery_id": delivery_id,
                    "commit_ref": str(row.get("commit_ref", "")),
                    "attempts": int(row.get("attempts", 0)),
                    "receipt_count": len(list(eval_row.get("accepted_senders", []))),
                    "receipt_status_by_sender": dict(eval_row.get("status_by_sender", {}))
                    if isinstance(eval_row.get("status_by_sender"), dict)
                    else {},
                    "missing_required_validators": list(eval_row.get("missing_required_validators", [])),
                    "first_sent_ms": int(row.get("first_sent_ms", 0)),
                    "last_sent_ms": int(row.get("last_sent_ms", 0)),
                    "reason": row.get("reason"),
                }
            )
        return {
            "accepted_count": int(self.accepted_count),
            "rejected_count": int(self.rejected_count),
            "pending_count": len(self.pending),
            "retries_total": int(self.retries_total),
            "pending": pending_rows,
        }

    def clear(self) -> None:
        for did in list(self.pending.keys()):
            self.receipt_coordinator.remove(did)
        self.pending.clear()
        self._persist_state()

    def _state_file(self) -> Path | None:
        if self.state_path is None:
            return None
        text = str(self.state_path).strip()
        if not text:
            return None
        return Path(text)

    def _persist_state(self) -> None:
        path = self._state_file()
        if path is None:
            return
        payload = {
            "schema_version": "detm.fabric.delivery_tracking_state.v1",
            "accepted_count": int(self.accepted_count),
            "rejected_count": int(self.rejected_count),
            "retries_total": int(self.retries_total),
            "pending": {
                str(delivery_id): {
                    "delivery_id": str(row.get("delivery_id", delivery_id)),
                    "commit_ref": str(row.get("commit_ref", "")),
                    "mode": str(row.get("mode", "")),
                    "first_sent_ms": int(row.get("first_sent_ms", 0)),
                    "last_sent_ms": int(row.get("last_sent_ms", 0)),
                    "attempts": int(row.get("attempts", 0)),
                    "reason": row.get("reason"),
                    "created_at_ms": int(row.get("created_at_ms", 0)),
                    "envelope": row["envelope"].to_dict()
                    if isinstance(row.get("envelope"), FabricEnvelope)
                    else None,
                }
                for delivery_id, row in dict(self.pending).items()
                if str(delivery_id).strip()
            },
            "receipt_state": self.receipt_coordinator.snapshot_state()
            if hasattr(self.receipt_coordinator, "snapshot_state")
            else {},
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_path.replace(path)

    def _load_state(self) -> None:
        path = self._state_file()
        if path is None or not path.exists():
            return
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return
        if not isinstance(payload, dict):
            return

        self.accepted_count = max(0, int(payload.get("accepted_count", 0)))
        self.rejected_count = max(0, int(payload.get("rejected_count", 0)))
        self.retries_total = max(0, int(payload.get("retries_total", 0)))
        self.pending.clear()

        pending_rows = dict(payload.get("pending", {})) if isinstance(payload.get("pending"), dict) else {}
        for delivery_id, row in pending_rows.items():
            did = str(delivery_id).strip()
            if not did or not isinstance(row, dict):
                continue
            envelope_raw = row.get("envelope")
            envelope = None
            if isinstance(envelope_raw, dict):
                try:
                    envelope = FabricEnvelope.from_dict(envelope_raw)
                except Exception:
                    envelope = None
            if envelope is None:
                continue
            self.pending[did] = {
                "delivery_id": str(row.get("delivery_id", did)),
                "commit_ref": str(row.get("commit_ref", "")),
                "mode": str(row.get("mode", "")),
                "first_sent_ms": max(0, int(row.get("first_sent_ms", 0))),
                "last_sent_ms": max(0, int(row.get("last_sent_ms", 0))),
                "attempts": max(0, int(row.get("attempts", 0))),
                "envelope": envelope,
                "reason": row.get("reason"),
                "created_at_ms": max(0, int(row.get("created_at_ms", 0))),
            }

        if hasattr(self.receipt_coordinator, "load_snapshot"):
            try:
                self.receipt_coordinator.load_snapshot(payload.get("receipt_state", {}))
            except Exception:
                pass


__all__ = ["DeliveryTrackingCoordinator", "RepublishFn"]



