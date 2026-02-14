"""Local validator policy primitives."""

from __future__ import annotations

from dataclasses import dataclass

from detm.runtime.commit_packet import CommitPacket


def normalize_replay_policy_tier(raw: str | object) -> str:
    tier = str(raw).strip().lower()
    aliases = {
        "off": "off",
        "disabled": "off",
        "sampled": "sampled",
        "sample": "sampled",
        "strict_window": "strict_window",
        "strict-window": "strict_window",
        "strict": "strict_window",
    }
    return aliases.get(tier, "sampled")


@dataclass(frozen=True)
class ReplaySamplePolicy:
    """Sampling policy for optional replay checks in validator flow."""

    tier: str = "sampled"
    enabled: bool = False
    sample_stride: int = 1
    sample_offset: int = 0
    strict_window_size: int = 128

    def normalized_tier(self) -> str:
        return normalize_replay_policy_tier(self.tier)

    def should_check(self, packet: CommitPacket) -> bool:
        tier = self.normalized_tier()
        if tier == "off":
            return False
        if tier == "strict_window":
            return True
        if not bool(self.enabled):
            return False
        stride = max(1, int(self.sample_stride))
        tick = int(packet.tick_ref.tick)
        offset = int(self.sample_offset)
        return ((tick - offset) % stride) == 0

    def strict_window_violation_reason(self, packet: CommitPacket, *, max_seen_tick: int | None) -> str | None:
        if self.normalized_tier() != "strict_window":
            return None
        if max_seen_tick is None:
            return None
        window = max(1, int(self.strict_window_size))
        tick = int(packet.tick_ref.tick)
        min_allowed_tick = int(max_seen_tick) - window + 1
        if int(tick) >= int(min_allowed_tick):
            return None
        return (
            f"replay strict_window violation: tick={tick} is older than "
            f"min_allowed_tick={min_allowed_tick} (window={window}, max_seen_tick={int(max_seen_tick)})"
        )


__all__ = ["ReplaySamplePolicy", "normalize_replay_policy_tier"]
