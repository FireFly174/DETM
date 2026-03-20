from __future__ import annotations

from detm.runtime.watch_contract import AntiGoodhartSnapshot, WatchContractPacket


def test_anti_goodhart_snapshot_roundtrip_normalizes_types():
    raw = {
        "goodhart_flag": "true",
        "target_signal": "operator_reuse",
        "target_delta": "0.15",
        "degraded_signals": ("hold_rate", "transferability"),
        "degraded_signal_count": "2",
        "thresholds": {
            "target_signal": "operator_reuse",
            "min_target_delta": "0.0",
            "min_degraded_signals": "2",
            "degradation_epsilon": "0.01",
        },
        "policy_reaction": {
            "apply": 1,
            "actions": ("downweight_target_signal",),
        },
        "policy_reaction_enabled": "true",
        "preferred_runtime_profile": "stability",
        "runtime_profile_applied": "false",
        "applicability": "runtime_panel",
    }

    snapshot = AntiGoodhartSnapshot.from_dict(raw)
    payload = snapshot.to_dict()
    assert bool(payload.get("goodhart_flag")) is True
    assert str(payload.get("target_signal", "")) == "operator_reuse"
    assert float(payload.get("target_delta", 0.0)) == 0.15
    assert list(payload.get("degraded_signals", [])) == ["hold_rate", "transferability"]
    assert int(payload.get("degraded_signal_count", 0)) == 2
    thresholds = dict(payload.get("thresholds", {}))
    assert str(thresholds.get("target_signal", "")) == "operator_reuse"
    assert float(thresholds.get("min_target_delta", 0.0)) == 0.0
    assert int(thresholds.get("min_degraded_signals", 0)) == 2
    assert float(thresholds.get("degradation_epsilon", 0.0)) == 0.01
    reaction = dict(payload.get("policy_reaction", {}))
    assert bool(reaction.get("apply")) is True
    assert list(reaction.get("actions", [])) == ["downweight_target_signal"]


def test_watch_contract_packet_from_dict_normalizes_anti_goodhart_blocks():
    packet = WatchContractPacket.from_dict(
        {
            "tick": 3,
            "trace_ref": "trace://0003",
            "outerfields_ref": {
                "kind": "outerfields",
                "level_src": "L0",
                "base_level": "L0",
                "tick": 3,
                "window_ticks": 1,
                "stride_ticks": 1,
                "uri": "outerfields/outerfields_000003.npz",
                "schema": "OUTERFIELDS_V1",
            },
            "signature": {},
            "metrics": {
                "watchpoints": {
                    "anti_goodhart": {
                        "goodhart_flag": True,
                        "target_signal": "operator_reuse",
                        "degraded_signals": ["hold_rate"],
                        "degraded_signal_count": 1,
                        "policy_reaction": {"apply": True, "actions": ["prefer_stability_runtime_profile"]},
                    },
                }
            },
            "policy": {
                "anti_goodhart": {
                    "goodhart_flag": False,
                }
            },
        }
    )
    watchpoints = dict(dict(packet.metrics).get("watchpoints", {}))
    assert "anti_goodhart" in watchpoints
    assert "anti_goodhart_flag" in watchpoints
    assert "anti_goodhart_degraded_signal_count" in watchpoints
    assert "anti_goodhart_policy_reaction_applied" in watchpoints
    assert "anti_goodhart_runtime_profile_applied" in watchpoints
    anti = dict(watchpoints.get("anti_goodhart", {}))
    assert bool(anti.get("goodhart_flag")) is True
    policy = dict(packet.policy)
    assert "anti_goodhart" in policy


def test_watch_contract_packet_from_dict_normalizes_exploration_horizon_block():
    packet = WatchContractPacket.from_dict(
        {
            "tick": 4,
            "trace_ref": "trace://0004",
            "outerfields_ref": {
                "kind": "outerfields",
                "level_src": "L0",
                "base_level": "L0",
                "tick": 4,
                "window_ticks": 1,
                "stride_ticks": 1,
                "uri": "outerfields/outerfields_000004.npz",
                "schema": "OUTERFIELDS_V1",
            },
            "signature": {},
            "metrics": {
                "watchpoints": {
                    "exploration_horizon": {
                        "exploration_horizon_ticks": "3",
                        "horizon_start_tick": "2",
                        "horizon_break_reason": "goodhart_flag",
                        "horizon_recovery_cost_ticks": "1",
                    }
                }
            },
        }
    )
    watchpoints = dict(dict(packet.metrics).get("watchpoints", {}))
    assert "exploration_horizon" in watchpoints
    assert int(watchpoints.get("exploration_horizon_ticks", 0)) == 3
    assert int(watchpoints.get("horizon_start_tick", 0)) == 2
    assert str(watchpoints.get("horizon_break_reason", "")) == "goodhart_flag"
    assert int(watchpoints.get("horizon_recovery_cost_ticks", 0)) == 1
