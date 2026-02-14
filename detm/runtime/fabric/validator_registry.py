"""Validator registry contracts for fabric quorum policies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, FrozenSet, Protocol, Sequence

# ARCH-MARKERS:
# - LAYER_BAND: L5
# - ABSTRACT_DISTANCE: 0 (validator registry abstraction exists)
# - OOP_TECH_DEBT: signed dynamic membership updates + remote discovery


class ValidatorRegistry(Protocol):
    """Abstract source of active validators for quorum policies."""

    def required_validator_ids(self) -> FrozenSet[str]:
        ...

    def is_active(self, validator_id: str) -> bool:
        ...


@dataclass(frozen=True)
class StaticValidatorRegistry:
    """Static in-memory validator set (MVP)."""

    validators: FrozenSet[str]

    @classmethod
    def from_ids(cls, validator_ids: Sequence[str] | None) -> "StaticValidatorRegistry":
        ids = frozenset(str(v).strip() for v in (validator_ids or []) if str(v).strip())
        return cls(validators=ids)

    def required_validator_ids(self) -> FrozenSet[str]:
        return frozenset(self.validators)

    def is_active(self, validator_id: str) -> bool:
        return str(validator_id).strip() in self.validators

    def to_dict(self) -> Dict[str, object]:
        return {"validators": sorted(self.validators)}


__all__ = ["StaticValidatorRegistry", "ValidatorRegistry"]
