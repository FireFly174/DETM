"""Delivery receipt policy implementations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import FrozenSet, Mapping, Sequence


def norm_status(value: object) -> str:
    raw = str(value).strip().lower()
    if raw in {"received", "accepted", "ok"}:
        return "accepted"
    if raw in {"rejected", "reject", "error", "failed"}:
        return "rejected"
    return "unknown"


def norm_validator_set(values: Sequence[str] | None) -> FrozenSet[str]:
    if not values:
        return frozenset()
    return frozenset(str(v).strip() for v in values if str(v).strip())


@dataclass(frozen=True)
class CountDeliveryReceiptPolicy:
    """Count-based receipt policy with optional reject-on-any-reject semantics."""

    required_receipts: int = 1
    reject_on_any_reject: bool = False

    def evaluate(self, status_by_sender: Mapping[str, str]) -> tuple[str, str | None, dict[str, object]]:
        accepted = sorted(str(s) for s, st in dict(status_by_sender).items() if norm_status(st) == "accepted")
        rejected = sorted(str(s) for s, st in dict(status_by_sender).items() if norm_status(st) == "rejected")
        if bool(self.reject_on_any_reject) and rejected:
            return (
                "rejected",
                "delivery rejected by at least one receipt under reject_on_any_reject policy",
                {
                    "accepted_senders": accepted,
                    "rejected_senders": rejected,
                    "required_receipts": int(self.required_receipts),
                    "missing_required_validators": [],
                },
            )
        if len(accepted) >= int(self.required_receipts):
            return (
                "accepted",
                None,
                {
                    "accepted_senders": accepted,
                    "rejected_senders": rejected,
                    "required_receipts": int(self.required_receipts),
                    "missing_required_validators": [],
                },
            )
        return (
            "pending",
            "delivery receipt threshold not reached",
            {
                "accepted_senders": accepted,
                "rejected_senders": rejected,
                "required_receipts": int(self.required_receipts),
                "missing_required_validators": [],
            },
        )


@dataclass(frozen=True)
class ValidatorSetDeliveryReceiptPolicy:
    """Count policy extended with required validator set enforcement."""

    required_receipts: int = 1
    required_validator_ids: FrozenSet[str] = field(default_factory=frozenset)
    enforce_required_validator_ids: bool = False
    reject_on_any_reject: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "required_validator_ids", norm_validator_set(self.required_validator_ids))

    def evaluate(self, status_by_sender: Mapping[str, str]) -> tuple[str, str | None, dict[str, object]]:
        accepted = sorted(str(s) for s, st in dict(status_by_sender).items() if norm_status(st) == "accepted")
        rejected = sorted(str(s) for s, st in dict(status_by_sender).items() if norm_status(st) == "rejected")
        if bool(self.reject_on_any_reject) and rejected:
            return (
                "rejected",
                "delivery rejected by at least one receipt under reject_on_any_reject policy",
                {
                    "accepted_senders": accepted,
                    "rejected_senders": rejected,
                    "required_receipts": int(self.required_receipts),
                    "missing_required_validators": sorted(self.required_validator_ids.difference(set(accepted))),
                },
            )

        if len(accepted) < int(self.required_receipts):
            return (
                "pending",
                "delivery receipt threshold not reached",
                {
                    "accepted_senders": accepted,
                    "rejected_senders": rejected,
                    "required_receipts": int(self.required_receipts),
                    "missing_required_validators": sorted(self.required_validator_ids.difference(set(accepted))),
                },
            )

        missing_required = sorted(self.required_validator_ids.difference(set(accepted)))
        if bool(self.enforce_required_validator_ids) and missing_required:
            return (
                "pending",
                f"required delivery validator set missing: {missing_required}",
                {
                    "accepted_senders": accepted,
                    "rejected_senders": rejected,
                    "required_receipts": int(self.required_receipts),
                    "missing_required_validators": missing_required,
                },
            )
        return (
            "accepted",
            None,
            {
                "accepted_senders": accepted,
                "rejected_senders": rejected,
                "required_receipts": int(self.required_receipts),
                "missing_required_validators": missing_required,
            },
        )


__all__ = [
    "CountDeliveryReceiptPolicy",
    "ValidatorSetDeliveryReceiptPolicy",
    "norm_status",
]
