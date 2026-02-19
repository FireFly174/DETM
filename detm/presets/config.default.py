"""Default single-file config for local development.

This file is a template. `python main.py` (with no args) will copy it into the
repo root as `config.example.py` if missing, and will use that local file on
subsequent launches.
"""

# Р СљР С•Р В¶Р Р…Р С• РЎвЂљР В°Р С”Р В¶Р Вµ РЎР‚Р ВµР В°Р В»Р С‘Р В·Р С•Р Р†Р В°РЎвЂљРЎРЉ `get_config()` / `load_config()` Р С‘ Р Р†Р ВµРЎР‚Р Р…РЎС“РЎвЂљРЎРЉ dict.
CONFIG = {
    "backend": "torch",  # torch | numpy  /// Р Р†РЎвЂ№РЎвЂЎР С‘РЎРѓР В»Р С‘РЎвЂљР ВµР В»РЎРЉР Р…РЎвЂ№Р в„– Р В±РЎРЊР С”Р ВµР Р…Р Т‘
    "device": "cuda",  # cuda | cpu | cuda:0  /// РЎС“РЎРѓРЎвЂљРЎР‚Р С•Р в„–РЎРѓРЎвЂљР Р†Р С• Р С‘РЎРѓР С—Р С•Р В»Р Р…Р ВµР Р…Р С‘РЎРЏ
    # minimal | cpu_full  /// РЎР‚Р ВµР В¶Р С‘Р С РЎвЂћР С•РЎР‚Р СР С‘РЎР‚Р С•Р Р†Р В°Р Р…Р С‘РЎРЏ observables (cpu_full РЎР‚Р В°Р В·РЎР‚Р ВµРЎв‚¬Р В°Р ВµРЎвЂљ РЎвЂљРЎРЏР В¶РЎвЂР В»РЎвЂ№Р Вµ CPU-Р В°Р Р…Р В°Р В»Р С‘Р В·РЎвЂ№)
    "observables_mode": "minimal",
    "trace_boundary_flux": False,  # False | True  /// log РћВ¦_boundary(t) proxies into trace.jsonl
    "watch_trace_enabled": True,  # False | True  /// Р Р†Р С”Р В»РЎР‹РЎвЂЎР С‘РЎвЂљРЎРЉ `watch_trace.jsonl` Р С—РЎР‚Р С•Р ВµР С”РЎвЂ Р С‘РЎР‹
    "trace_system_retention_window": 0,  # 0 | int > 0  /// Р С•Р С”Р Р…Р С• РЎвЂ¦РЎР‚Р В°Р Р…Р ВµР Р…Р С‘РЎРЏ System Trace (`trace.jsonl`)
    "trace_watch_retention_window": 0,  # 0 | int > 0  /// Р С•Р С”Р Р…Р С• РЎвЂ¦РЎР‚Р В°Р Р…Р ВµР Р…Р С‘РЎРЏ Watch Trace (`watch_trace.jsonl`)
    "trace_watch_compaction_budget": 0,  # 0 | int > 0  /// budget compaction Р Т‘Р В»РЎРЏ Watch Trace
    # policy РЎвЂ¦РЎР‚Р В°Р Р…Р ВµР Р…Р С‘РЎРЏ Р В°РЎР‚РЎвЂљР ВµРЎвЂћР В°Р С”РЎвЂљР С•Р Р† Р С—Р С• РЎС“РЎР‚Р С•Р Р†Р Р…РЎРЏР С `L0..Ln`; 0/0 = РЎвЂ¦РЎР‚Р В°Р Р…Р С‘РЎвЂљРЎРЉ Р Р†РЎРѓРЎвЂ
    "artifact_storage_policy": {
        "L0": {
            "trace": {"retention_window": 0, "compaction_budget": 0},
            "watch_trace": {"retention_window": 0, "compaction_budget": 0},
            "watch_contract": {"retention_window": 0, "compaction_budget": 0},
            "operator_decisions": {"retention_window": 0, "compaction_budget": 0},
            "outerfields": {"retention_window": 0, "compaction_budget": 0},
            "commits": {"retention_window": 0, "compaction_budget": 0},
            "commits_audit": {"retention_window": 0, "compaction_budget": 0},
            "invariants": {"retention_window": 0, "compaction_budget": 0},
            "history": {"retention_window": 0, "compaction_budget": 0},
            "commit_validation": {"retention_window": 0, "compaction_budget": 0},
            "fabric_acks": {"retention_window": 0, "compaction_budget": 0},
            "fabric_ack_envelopes": {"retention_window": 0, "compaction_budget": 0},
            "fabric_delivery_acks": {"retention_window": 0, "compaction_budget": 0},
            "fabric_dead_letters": {"retention_window": 0, "compaction_budget": 0},
            "fabric_quorum_report": {"retention_window": 0, "compaction_budget": 0},
        },
    },
    "pattern_reuse_enabled": True,  # False | True  /// Р Р†Р С”Р В»РЎР‹РЎвЂЎР С‘РЎвЂљРЎРЉ lookup/reuse Р С—Р В°РЎвЂљРЎвЂљР ВµРЎР‚Р Р…Р С•Р Р† Р Т‘Р С• refine
    # global | portable | strict  /// scope pattern reuse Р СР ВµР В¶Р Т‘РЎС“ РЎС“РЎР‚Р С•Р Р†Р Р…РЎРЏР СР С‘/РЎР‚Р ВµР В¶Р С‘Р СР В°Р СР С‘
    "pattern_reuse_scope": "portable",
    "pattern_store_path": None,  # None | path  /// file-backed PatternStore (MVP stub)
    "pattern_cache_capacity": 128,  # int >= 1  /// РЎвЂР СР С”Р С•РЎРѓРЎвЂљРЎРЉ LRU PatternCache
    "pattern_cache_ttl_steps": 4096,  # int >= 1  /// TTL PatternCache Р Р† РЎв‚¬Р В°Р С–Р В°РЎвЂ¦
    "pattern_prune_error_threshold": 0.05,  # float >= 0  /// pruning Р С—Р С•РЎР‚Р С•Р С– error
    "pattern_prune_deviation_threshold": 0.5,  # float >= 0  /// pruning Р С—Р С•РЎР‚Р С•Р С– deviation
    "level_policy": {
        "schema_version": "1.16.0",  # semver  /// Р Р†Р ВµРЎР‚РЎРѓР С‘РЎРЏ РЎРѓРЎвЂ¦Р ВµР СРЎвЂ№ LevelPolicy
        "active_level": "L0",  # Ln  /// Р В°Р С”РЎвЂљР С‘Р Р†Р Р…РЎвЂ№Р в„– РЎС“РЎР‚Р С•Р Р†Р ВµР Р…РЎРЉ Р С—РЎС“Р В±Р В»Р С‘Р С”Р В°РЎвЂ Р С‘Р С‘
        "microsteps_per_global_tick": 1,  # int >= 1  /// Р Р†Р Р…РЎС“РЎвЂљРЎР‚Р ВµР Р…Р Р…РЎРЏРЎРЏ РЎвЂЎР В°РЎРѓРЎвЂљР С•РЎвЂљР В° РЎв‚¬Р В°Р С–Р В°
        "batch_size": 1,  # int >= 1  /// РЎР‚Р В°Р В·Р СР ВµРЎР‚ batched-Р Р†РЎвЂ№Р С—Р С•Р В»Р Р…Р ВµР Р…Р С‘РЎРЏ
        "commit_stride": 1,  # int >= 1  /// Р С—РЎС“Р В±Р В»Р С‘Р С”Р В°РЎвЂ Р С‘РЎРЏ Р Р† trace/artefacts РЎР‚Р В°Р В· Р Р† N global ticks
        "audit_commit_enabled": False,  # False | True  /// Р Р†Р С”Р В»РЎР‹РЎвЂЎР С‘РЎвЂљРЎРЉ thick audit commits
        "audit_commit_stride": 10,  # int >= 1  /// Р С—Р ВµРЎР‚Р С‘Р С•Р Т‘ audit commits Р Р† global ticks
        "allow_refinement": True,  # False | True  /// РЎР‚Р В°Р В·РЎР‚Р ВµРЎв‚¬Р ВµР Р…Р С‘Р Вµ refine-Р С”Р С•Р Р…РЎвЂљРЎС“РЎР‚Р В°
        # float >= 0  /// Р С—Р С•РЎР‚Р С•Р С– Р Т‘Р С•Р В»Р С‘ overflow-Р С”Р В»Р ВµРЎвЂљР С•Р С” Р Т‘Р В»РЎРЏ detector=`capacity_pressure` (energy_overflow fallback Р Р…Р С‘Р В¶Р Вµ Р С—Р С•РЎР‚Р С•Р С–Р В°)
        "refinement_capacity_overflow_ratio_threshold": 0.15,
        # float >= 0  /// Р С—Р С•РЎР‚Р С•Р С– РЎРѓРЎР‚Р ВµР Т‘Р Р…Р ВµР в„– Р Р†Р ВµР В»Р С‘РЎвЂЎР С‘Р Р…РЎвЂ№ overflow (РЎРЊР Р…Р ВµРЎР‚Р С–Р ВµРЎвЂљР С‘РЎвЂЎР ВµРЎРѓР С”Р В°РЎРЏ "РЎвЂљРЎРЏР В¶Р ВµРЎРѓРЎвЂљРЎРЉ" Р С—Р ВµРЎР‚Р ВµР С–РЎР‚РЎС“Р В·Р В°)
        "refinement_capacity_overflow_mean_threshold": 0.5,
        # float >= 0  /// soft-boundary band around [0,1] for capacity pressure under clamped dynamics
        "refinement_capacity_saturation_band": 0.0,
        # int >= 1  /// Р СР С‘Р Р…Р С‘Р СР В°Р В»РЎРЉР Р…Р С•Р Вµ РЎвЂЎР С‘РЎРѓР В»Р С• capacity-signals (ratio + severity), Р Р…Р ВµР С•Р В±РЎвЂ¦Р С•Р Т‘Р С‘Р СРЎвЂ№РЎвЂ¦ Р Т‘Р В»РЎРЏ detector=`capacity_pressure`
        "refinement_capacity_min_signals": 1,
        # float >= 0  /// ratio-Р С—Р С•РЎР‚Р С•Р С– Р Т‘Р В»РЎРЏ temporal Р Р…Р В°Р С”Р С•Р С—Р В»Р ВµР Р…Р С‘РЎРЏ pressure-РЎРѓР С‘Р С–Р Р…Р В°Р В»Р В°
        "refinement_capacity_temporal_ratio_threshold": 0.1,
        # int >= 1  /// РЎР‚Р В°Р В·Р СР ВµРЎР‚ Р С•Р С”Р Р…Р В° temporal history Р Т‘Р В»РЎРЏ pressure-РЎРѓР С‘Р С–Р Р…Р В°Р В»Р В°
        "refinement_capacity_temporal_window": 4,
        # int >= 1  /// РЎРѓР С”Р С•Р В»РЎРЉР С”Р С• Р С—Р С•Р С—Р В°Р Т‘Р В°Р Р…Р С‘Р в„– Р Р† Р С•Р С”Р Р…Р С• РЎвЂљРЎР‚Р ВµР В±РЎС“Р ВµРЎвЂљРЎРѓРЎРЏ Р Т‘Р В»РЎРЏ temporal-signal
        "refinement_capacity_temporal_required_hits": 3,
        # int >= 0  /// learned-signal Р С—Р С• reuse hits (0 = disabled)
        "refinement_capacity_learned_hits_threshold": 0,
        # int >= 1  /// Р С•Р С”Р Р…Р С• Р Т‘Р В»РЎРЏ cross-level pressure-РЎРѓР С‘Р С–Р Р…Р В°Р В»Р В°
        "refinement_capacity_cross_level_window": 4,
        # int >= 1  /// Р СР С‘Р Р…Р С‘Р СРЎС“Р С РЎС“Р Р…Р С‘Р С”Р В°Р В»РЎРЉР Р…РЎвЂ№РЎвЂ¦ РЎС“РЎР‚Р С•Р Р†Р Р…Р ВµР в„– Р Р† Р С•Р С”Р Р…Р Вµ Р Т‘Р В»РЎРЏ cross-level signal
        "refinement_capacity_cross_level_min_levels": 2,
        # float >= 0  /// operator-driven РЎРѓР С‘Р С–Р Р…Р В°Р В» (Р Р†Р Р…Р ВµРЎв‚¬Р Р…Р С‘Р в„– score), threshold Р Т‘Р В»РЎРЏ capacity_secondary signal
        "refinement_capacity_operator_score_threshold": 1.0,
        # int >= 1  /// Р СР С‘Р Р…Р С‘Р СРЎС“Р С Р В°Р С”РЎвЂљР С‘Р Р†Р Р…РЎвЂ№РЎвЂ¦ cross-node Р С‘Р Р…Р Т‘Р С‘Р С”Р В°РЎвЂљР С•РЎР‚Р С•Р Р† (replay_failed/delivery_rejected/delivery_pending)
        "refinement_capacity_cross_node_min_signals": 1,
        # int >= 0  /// distributed-signal: Р СР С‘Р Р…Р С‘Р СРЎС“Р С accepted commits Р С‘Р В· quorum snapshot (0 = disabled)
        "refinement_capacity_distributed_accepted_min": 0,
        # int >= 0  /// signed-signal: Р СР С‘Р Р…Р С‘Р СРЎС“Р С РЎРѓРЎС“Р СР СР В°РЎР‚Р Р…РЎвЂ№РЎвЂ¦ accepted proof/trust ack Р Р† evaluations (0 = disabled)
        "refinement_capacity_signed_acks_min": 0,
        # int >= 0  /// consensus-grade signal: Р СР С‘Р Р…Р С‘Р СРЎС“Р С accepted commits Р С—РЎР‚Р С‘ Р Р…РЎС“Р В»Р ВµР Р†РЎвЂ№РЎвЂ¦ pending/rejected (0 = disabled)
        "refinement_capacity_consensus_accepted_min": 0,
        # float >= 0  /// cryptographic-grade signal: Р СР С‘Р Р…Р С‘Р СРЎС“Р С Р С—Р С•Р С”РЎР‚РЎвЂ№РЎвЂљР С‘РЎРЏ validator-set Р Р† accepted proof/trust
        "refinement_capacity_crypto_validator_coverage_min": 0.0,
        # list[str]  /// required validator ids for attestation-grade coverage check (empty -> registry-based)
        "refinement_capacity_attestation_validator_ids": [],
        # float >= 0  /// Р СР С‘Р Р…Р С‘Р СРЎС“Р С Р С—Р С•Р С”РЎР‚РЎвЂ№РЎвЂљР С‘РЎРЏ required validators Р Т‘Р В»РЎРЏ attestation-grade signal
        "refinement_capacity_attestation_min_coverage": 0.0,
        # int >= 0  /// byzantine-grade signal: Р СР С‘Р Р…Р С‘Р СРЎС“Р С accepted commits Р С—РЎР‚Р С‘ РЎвЂЎР С‘РЎРѓРЎвЂљР С•Р С consensus/replay/delivery (0 = disabled)
        "refinement_capacity_byzantine_clean_min": 0,
        # float >= 0  /// Р С—Р С•РЎР‚Р С•Р С– `discrete_torsion_v1.torsion_score` Р Т‘Р В»РЎРЏ operator-compatibility flag
        "refinement_operator_torsion_threshold": 1.0,
        # False | True  /// Р В±Р В»Р С•Р С”Р С‘РЎР‚Р С•Р Р†Р В°РЎвЂљРЎРЉ reuse Р С—РЎР‚Р С‘ Р С—РЎР‚Р ВµР Т‘РЎвЂ№Р Т‘РЎС“РЎвЂ°Р ВµР С torsion_flag Р Р† РЎвЂљР С•Р С Р В¶Р Вµ scope
        "refinement_operator_torsion_guard_enabled": True,
        # int >= 1  /// max Р Т‘Р В»Р С‘Р Р…Р В° runtime `operator_decision_history` (bounded persistence)
        "refinement_operator_history_limit": 256,
        # False | True  /// enable runtime anti-Goodhart detector in portability panel
        "anti_goodhart_enabled": True,
        # str  /// target signal for anti-Goodhart detector
        "anti_goodhart_target_signal": "operator_reuse",
        # float >= 0  /// minimum positive d_target required for goodhart_flag
        "anti_goodhart_min_target_delta": 0.0,
        # int >= 1  /// minimum degraded signals required for goodhart_flag
        "anti_goodhart_min_degraded_signals": 2,
        # float >= 0  /// degradation epsilon for panel signals
        "anti_goodhart_degradation_epsilon": 0.0,
        # False | True  /// apply policy reaction actions when goodhart_flag is raised
        "anti_goodhart_policy_reaction_enabled": True,
        # stability | throughput | manual  /// preferred runtime profile for reaction
        "anti_goodhart_prefer_runtime_profile": "stability",
        # [] | "*" | list[str]  /// РЎРѓР С•Р В±РЎвЂ№РЎвЂљР С‘РЎРЏ, Р В·Р В°Р С—РЎС“РЎРѓР С”Р В°РЎР‹РЎвЂ°Р С‘Р Вµ runtime adaptive Р С•Р С”Р Р…Р С• (microsteps/batch/commit_stride)
        "runtime_adaptive_signal_event_types": [],
        # int >= 1  /// Р СР С‘Р Р…Р С‘Р СР В°Р В»РЎРЉР Р…Р С•Р Вµ РЎвЂЎР С‘РЎРѓР В»Р С• runtime-adaptive РЎРѓР С‘Р С–Р Р…Р В°Р В»Р С•Р Р†, Р Р…РЎС“Р В¶Р Р…РЎвЂ№РЎвЂ¦ Р Т‘Р В»РЎРЏ trigger
        "runtime_adaptive_min_signals": 1,
        # float >= 0  /// runtime-adaptive signal Р С—Р С• quality.oscillation_score (0 = disabled)
        "runtime_adaptive_quality_oscillation_threshold": 0.0,
        # float >= 0  /// runtime-adaptive signal Р С—Р С• quality.jitter_signature (0 = disabled)
        "runtime_adaptive_quality_jitter_threshold": 0.0,
        # float >= 0  /// runtime-adaptive signal Р С—Р С• cost.cpu_time_ms (0 = disabled)
        "runtime_adaptive_cost_cpu_time_ms_threshold": 0.0,
        # False | True  /// auto profile selection: cost-signal -> throughput, event/quality -> stability
        "runtime_adaptive_auto_profile": False,
        # int  /// stability-profile delta Р Т‘Р В»РЎРЏ microsteps_per_global_tick
        "runtime_adaptive_stability_microsteps_delta": 1,
        # int  /// stability-profile delta Р Т‘Р В»РЎРЏ batch_size
        "runtime_adaptive_stability_batch_size_delta": 0,
        # int  /// stability-profile delta Р Т‘Р В»РЎРЏ commit_stride
        "runtime_adaptive_stability_commit_stride_delta": -1,
        # int  /// throughput-profile delta Р Т‘Р В»РЎРЏ microsteps_per_global_tick
        "runtime_adaptive_throughput_microsteps_delta": -1,
        # int  /// throughput-profile delta Р Т‘Р В»РЎРЏ batch_size
        "runtime_adaptive_throughput_batch_size_delta": 1,
        # int  /// throughput-profile delta Р Т‘Р В»РЎРЏ commit_stride
        "runtime_adaptive_throughput_commit_stride_delta": 1,
        # int >= 0  /// cooldown Р С—Р С•РЎРѓР В»Р Вµ runtime-adaptive trigger (anti-flap)
        "runtime_adaptive_cooldown_ticks": 0,
        # int >= 1  /// stride sampling Р Т‘Р В»РЎРЏ Р С—Р С•Р Т‘РЎР‚Р С•Р В±Р Р…РЎвЂ№РЎвЂ¦ `runtime_adaptive_signal_hits` Р Р† policy telemetry
        "runtime_adaptive_telemetry_sample_stride": 1,
        # int >= 1  /// Р С•Р С”Р Р…Р С• rolling aggregation Р Т‘Р В»РЎРЏ `runtime_adaptive_aggregate`
        "runtime_adaptive_telemetry_aggregation_window": 8,
        # int >= 1  /// guard: minimum microsteps_per_global_tick Р Т‘Р В»РЎРЏ runtime-adaptive Р С—РЎР‚Р С‘Р СР ВµР Р…Р ВµР Р…Р С‘РЎРЏ
        "runtime_adaptive_guard_microsteps_min": 1,
        # int >= 0  /// guard: maximum microsteps_per_global_tick (0 = no max)
        "runtime_adaptive_guard_microsteps_max": 0,
        # int >= 1  /// guard: minimum batch_size Р Т‘Р В»РЎРЏ runtime-adaptive Р С—РЎР‚Р С‘Р СР ВµР Р…Р ВµР Р…Р С‘РЎРЏ
        "runtime_adaptive_guard_batch_size_min": 1,
        # int >= 0  /// guard: maximum batch_size (0 = no max)
        "runtime_adaptive_guard_batch_size_max": 0,
        # int >= 1  /// guard: minimum commit_stride Р Т‘Р В»РЎРЏ runtime-adaptive Р С—РЎР‚Р С‘Р СР ВµР Р…Р ВµР Р…Р С‘РЎРЏ
        "runtime_adaptive_guard_commit_stride_min": 1,
        # int >= 0  /// guard: maximum commit_stride (0 = no max)
        "runtime_adaptive_guard_commit_stride_max": 0,
        # False | True  /// reject unsafe runtime-adaptive transition instead of clamping
        "runtime_adaptive_guard_reject_unsafe": False,
        # False | True  /// Р С‘РЎРѓР С—Р С•Р В»РЎРЉР В·Р С•Р Р†Р В°РЎвЂљРЎРЉ delta mode (relative tuning Р С•РЎвЂљ Р В±Р В°Р В·Р С•Р Р†Р С•Р С–Р С• policy) Р Р†Р СР ВµРЎРѓРЎвЂљР С• Р В°Р В±РЎРѓР С•Р В»РЎР‹РЎвЂљР Р…РЎвЂ№РЎвЂ¦ override
        "runtime_adaptive_use_deltas": False,
        # int  /// delta Р Т‘Р В»РЎРЏ microsteps_per_global_tick Р Р† runtime adaptive Р С•Р С”Р Р…Р Вµ (Р С‘РЎРѓР С—Р С•Р В»РЎРЉР В·РЎС“Р ВµРЎвЂљРЎРѓРЎРЏ Р С—РЎР‚Р С‘ runtime_adaptive_use_deltas=True)
        "runtime_adaptive_microsteps_delta": 0,
        # int  /// delta Р Т‘Р В»РЎРЏ batch_size Р Р† runtime adaptive Р С•Р С”Р Р…Р Вµ (Р С‘РЎРѓР С—Р С•Р В»РЎРЉР В·РЎС“Р ВµРЎвЂљРЎРѓРЎРЏ Р С—РЎР‚Р С‘ runtime_adaptive_use_deltas=True)
        "runtime_adaptive_batch_size_delta": 0,
        # int  /// delta Р Т‘Р В»РЎРЏ commit_stride Р Р† runtime adaptive Р С•Р С”Р Р…Р Вµ (Р С‘РЎРѓР С—Р С•Р В»РЎРЉР В·РЎС“Р ВµРЎвЂљРЎРѓРЎРЏ Р С—РЎР‚Р С‘ runtime_adaptive_use_deltas=True)
        "runtime_adaptive_commit_stride_delta": 0,
        # int >= 0  /// override microsteps_per_global_tick Р Р† runtime adaptive Р С•Р С”Р Р…Р Вµ (0 = base policy)
        "runtime_adaptive_microsteps_per_global_tick": 0,
        # int >= 0  /// override batch_size Р Р† runtime adaptive Р С•Р С”Р Р…Р Вµ (0 = base policy)
        "runtime_adaptive_batch_size": 0,
        # int >= 0  /// override commit_stride Р Р† runtime adaptive Р С•Р С”Р Р…Р Вµ (0 = base policy)
        "runtime_adaptive_commit_stride": 0,
        # int >= 0  /// РЎРѓР С”Р С•Р В»РЎРЉР С”Р С• РЎв‚¬Р В°Р С–Р С•Р Р† Р Т‘Р ВµРЎР‚Р В¶Р В°РЎвЂљРЎРЉ runtime adaptive Р С•Р С”Р Р…Р С• Р С—Р С•РЎРѓР В»Р Вµ trigger
        "runtime_adaptive_hold_ticks": 0,
        "observability_profile": {
            # "*" | list[str]  /// РЎвЂљР С‘Р С—РЎвЂ№ РЎРѓР С•Р В±РЎвЂ№РЎвЂљР С‘Р в„–, Р С”Р С•РЎвЂљР С•РЎР‚РЎвЂ№Р Вµ Р С—Р С•Р С—Р В°Р Т‘Р В°РЎР‹РЎвЂљ Р Р† trace
            "allowed_event_types": ["*"],
            # minimal | standard | debug  /// РЎС“РЎР‚Р С•Р Р†Р ВµР Р…РЎРЉ Р С—Р С•Р Т‘РЎР‚Р С•Р В±Р Р…Р С•РЎРѓРЎвЂљР С‘ trace
            "detail_mode": "standard",
            # [] | "*" | list[str]  /// adaptive signals (Р С—Р С• РЎвЂљР С‘Р С—Р В°Р С РЎРѓР С•Р В±РЎвЂ№РЎвЂљР С‘Р в„–), Р Р†Р С”Р В»РЎР‹РЎвЂЎР В°РЎР‹РЎвЂљ Р Р†РЎР‚Р ВµР СР ВµР Р…Р Р…РЎвЂ№Р в„– Р С—РЎР‚Р С•РЎвЂћР С‘Р В»РЎРЉ
            "adaptive_signal_event_types": [],
            # minimal | standard | debug  /// detail_mode Р С—РЎР‚Р С‘ adaptive trigger
            "adaptive_detail_mode": "debug",
            # int >= 0  /// РЎРѓР С”Р С•Р В»РЎРЉР С”Р С• L0-РЎвЂљР С‘Р С”Р С•Р Р† Р Т‘Р ВµРЎР‚Р В¶Р В°РЎвЂљРЎРЉ adaptive Р С—РЎР‚Р С•РЎвЂћР С‘Р В»РЎРЉ Р С—Р С•РЎРѓР В»Р Вµ trigger
            "adaptive_hold_ticks": 0,
            # "*" | list[str]  /// allowed_event_types Р Т‘Р В»РЎРЏ adaptive РЎР‚Р ВµР В¶Р С‘Р СР В°
            "adaptive_allowed_event_types": ["*"],
        },
    },
    "width": 24,  # int > 0  /// РЎв‚¬Р С‘РЎР‚Р С‘Р Р…Р В° РЎР‚Р ВµРЎв‚¬РЎвЂРЎвЂљР С”Р С‘
    "height": 24,  # int > 0  /// Р Р†РЎвЂ№РЎРѓР С•РЎвЂљР В° РЎР‚Р ВµРЎв‚¬РЎвЂРЎвЂљР С”Р С‘
    "boundary": "periodic",  # periodic | open  /// РЎС“РЎРѓР В»Р С•Р Р†Р С‘Р Вµ Р С–РЎР‚Р В°Р Р…Р С‘РЎвЂ РЎвЂ№
    "initial_noise": 0.08,  # float >= 0  /// РЎв‚¬РЎС“Р С Р Р…Р В°РЎвЂЎР В°Р В»РЎРЉР Р…Р С•Р С–Р С• E
    # a,b,k,g,t Р Р† UI: alpha,beta,kappa,gamma,lambda_t  /// Р С—Р В°РЎР‚Р В°Р СР ВµРЎвЂљРЎР‚РЎвЂ№ Р Т‘Р С‘Р Р…Р В°Р СР С‘Р С”Р С‘
    "dynamics": {
        "equilibrium_energy": 0.5,  # float 0..1  /// Р В±Р В°Р В·Р С•Р Р†РЎвЂ№Р в„– РЎС“РЎР‚Р С•Р Р†Р ВµР Р…РЎРЉ РЎРЊР Р…Р ВµРЎР‚Р С–Р С‘Р С‘
        "alpha": 0.3,  # float >= 0  /// Р С—Р С•Р Т‘Р В°Р Р†Р В»Р ВµР Р…Р С‘Р Вµ Р С—Р ВµРЎР‚Р ВµР Р…Р С•РЎРѓР В° РЎРЊР Р…РЎвЂљРЎР‚Р С•Р С—Р С‘Р ВµР в„–
        "beta": 0.8,  # float >= 0  /// Р Р†Р ВµРЎРѓ Р В»Р С•Р С”Р В°Р В»РЎРЉР Р…Р С•Р С–Р С• Р С•РЎвЂљР С”Р В»Р С•Р Р…Р ВµР Р…Р С‘РЎРЏ
        "gamma": 0.1,  # float >= 0  /// Р Р†Р ВµРЎРѓ Р С•РЎвЂљР С”Р В»Р С•Р Р…Р ВµР Р…Р С‘РЎРЏ РЎРѓР С•РЎРѓР ВµР Т‘Р ВµР в„–
        "kappa": 0.1,  # float >= 0  /// Р С—РЎР‚Р С•Р Р†Р С•Р Т‘Р С‘Р СР С•РЎРѓРЎвЂљРЎРЉ Р С—Р ВµРЎР‚Р ВµР Р…Р С•РЎРѓР В°
        "lambda_t": 1.0,  # float >= 0  /// Р Р†Р В»Р С‘РЎРЏР Р…Р С‘Р Вµ РЎРЊР Р…РЎвЂљРЎР‚Р С•Р С—Р С‘Р С‘ Р Р…Р В° Р Р†РЎР‚Р ВµР СРЎРЏ
        "activation_threshold": 1.0,  # float > 0  /// Р С—Р С•РЎР‚Р С•Р С– Р В°Р С”РЎвЂљР С‘Р Р†Р В°РЎвЂ Р С‘Р С‘ Р С—Р ВµРЎР‚Р ВµР Р…Р С•РЎРѓР В°
        "energy_bounds": (0.0, 1.0),  # (lo,hi) | None  /// Р С•Р С–РЎР‚Р В°Р Р…Р С‘РЎвЂЎР ВµР Р…Р С‘Р Вµ РЎРЊР Р…Р ВµРЎР‚Р С–Р С‘Р С‘
    },
    "ui": {
        "seed": 1,  # int >= 0  /// seed Р Т‘Р В»РЎРЏ UI-РЎРѓР ВµРЎРѓРЎРѓР С‘Р С‘
        "ticks_per_step": 4,  # int > 0  /// L0-РЎвЂљР С‘Р С”Р С•Р Р† Р Р…Р В° РЎв‚¬Р В°Р С– UI
        "tick_interval_ms": 60,  # int >= 1  /// Р В·Р В°Р Т‘Р ВµРЎР‚Р В¶Р С”Р В° Р СР ВµР В¶Р Т‘РЎС“ РЎв‚¬Р В°Р С–Р В°Р СР С‘
        # symbol | joystick_field | joystick_patch | source_sink | none  /// РЎР‚Р ВµР В¶Р С‘Р С Р Р†Р В»Р С‘РЎРЏР Р…Р С‘РЎРЏ
        "influence_mode": "symbol",
        "symbol_id": "pulse",  # list_symbols() | (none)  /// РЎРѓР С‘Р СР Р†Р С•Р В» Р Р†Р В»Р С‘РЎРЏР Р…Р С‘РЎРЏ
        "amplitude": 1.0,  # float  /// РЎРѓР С‘Р В»Р В° Р Р†Р В»Р С‘РЎРЏР Р…Р С‘РЎРЏ
        "influence_duration_steps": 0,  # 0 | int > 0  /// Р Т‘Р В»Р С‘РЎвЂљР ВµР В»РЎРЉР Р…Р С•РЎРѓРЎвЂљРЎРЉ Р Р†Р В»Р С‘РЎРЏР Р…Р С‘РЎРЏ
        "joy_dx": 0.0,  # float -1..1  /// Р Р…Р В°Р С”Р В»Р С•Р Р… Р С—Р С•Р В»РЎРЏ Р С—Р С• X
        "joy_dy": 0.0,  # float -1..1  /// Р Р…Р В°Р С”Р В»Р С•Р Р… Р С—Р С•Р В»РЎРЏ Р С—Р С• Y
        "patch_cx": 12,  # int 0..W-1  /// РЎвЂ Р ВµР Р…РЎвЂљРЎР‚ Р С—Р В°РЎвЂљРЎвЂЎР В° Р С—Р С• X
        "patch_cy": 12,  # int 0..H-1  /// РЎвЂ Р ВµР Р…РЎвЂљРЎР‚ Р С—Р В°РЎвЂљРЎвЂЎР В° Р С—Р С• Y
        "patch_radius": 6,  # int >= 0  /// РЎР‚Р В°Р Т‘Р С‘РЎС“РЎРѓ Р С—Р В°РЎвЂљРЎвЂЎР В°
        "source_x": 6,  # int 0..W-1  /// X Р С‘РЎРѓРЎвЂљР С•РЎвЂЎР Р…Р С‘Р С”Р В° РЎРЊР Р…Р ВµРЎР‚Р С–Р С‘Р С‘
        "source_y": 12,  # int 0..H-1  /// Y Р С‘РЎРѓРЎвЂљР С•РЎвЂЎР Р…Р С‘Р С”Р В° РЎРЊР Р…Р ВµРЎР‚Р С–Р С‘Р С‘
        "sink_x": 18,  # int 0..W-1  /// X РЎРѓРЎвЂљР С•Р С”Р В° РЎРЊР Р…Р ВµРЎР‚Р С–Р С‘Р С‘
        "sink_y": 12,  # int 0..H-1  /// Y РЎРѓРЎвЂљР С•Р С”Р В° РЎРЊР Р…Р ВµРЎР‚Р С–Р С‘Р С‘
        "source_value": 1.0,  # float 0..1  /// Р В·Р Р…Р В°РЎвЂЎР ВµР Р…Р С‘Р Вµ Р С‘РЎРѓРЎвЂљР С•РЎвЂЎР Р…Р С‘Р С”Р В°
        "sink_value": 0.0,  # float 0..1  /// Р В·Р Р…Р В°РЎвЂЎР ВµР Р…Р С‘Р Вµ РЎРѓРЎвЂљР С•Р С”Р В°
        "record_dir": "runs/out/ui_run",  # path | None  /// Р Т‘Р С‘РЎР‚Р ВµР С”РЎвЂљР С•РЎР‚Р С‘РЎРЏ Р В·Р В°Р С—Р С‘РЎРѓР С‘
        "record_fields": False,  # False | True  /// Р В·Р В°Р С—Р С‘РЎРѓРЎРЉ fields_hist.npz
        "invariant_streams": "",  # "" | "inv0=1/10,..."  /// Р С‘Р Р…Р Р†Р В°РЎР‚Р С‘Р В°Р Р…РЎвЂљР Р…РЎвЂ№Р Вµ РЎвЂљР С‘Р С”Р С‘
        "viz_enabled": True,  # False | True  /// Р Р†Р С”Р В»РЎР‹РЎвЂЎР С‘РЎвЂљРЎРЉ viz-Р Т‘Р ВµР СР С•Р Р…
        "viz_transport": "embedded",  # embedded | tcp | none  /// РЎвЂљРЎР‚Р В°Р Р…РЎРѓР С—Р С•РЎР‚РЎвЂљ Р Р†Р С‘Р В·РЎС“Р В°Р В»Р С‘Р В·Р В°РЎвЂ Р С‘Р С‘
        "viz_host": "127.0.0.1",  # host  /// Р В°Р Т‘РЎР‚Р ВµРЎРѓ viz-Р Т‘Р ВµР СР С•Р Р…Р В°
        "viz_port": 0,  # 0 | int > 0  /// Р С—Р С•РЎР‚РЎвЂљ viz-Р Т‘Р ВµР СР С•Р Р…Р В°
        "viz_connect": False,  # False | True  /// connect Р С” Р Р†Р Р…Р ВµРЎв‚¬Р Р…Р ВµР СРЎС“ daemon
        "viz_keep_open": False,  # False | True  /// Р Р…Р Вµ Р В·Р В°Р С”РЎР‚РЎвЂ№Р Р†Р В°РЎвЂљРЎРЉ daemon
        "viz_every_steps": 1,  # int > 0  /// Р С—Р ВµРЎР‚Р С‘Р С•Р Т‘ Р С•РЎвЂљР С—РЎР‚Р В°Р Р†Р С”Р С‘ Р С”Р В°Р Т‘РЎР‚Р С•Р Р†
    },
    "runner": {
        "seed": 1,  # int >= 0  /// seed Р С•Р Т‘Р С‘Р Р…Р С•РЎвЂЎР Р…Р С•Р С–Р С• Р В·Р В°Р С—РЎС“РЎРѓР С”Р В°
        "seed0": 0,  # int >= 0  /// РЎРѓРЎвЂљР В°РЎР‚РЎвЂљ seed Р Т‘Р В»РЎРЏ batch
        "steps": 4,  # int > 0  /// Р В±РЎР‹Р Т‘Р В¶Р ВµРЎвЂљ РЎвЂљР С‘Р С”Р С•Р Р†
        "steps_mode": "total",  # total | per_symbol  /// Р С”Р В°Р С” Р С—РЎР‚Р С‘Р СР ВµР Р…РЎРЏРЎвЂљРЎРЉ budget: РЎРѓРЎС“Р СР СР В°РЎР‚Р Р…Р С• Р С‘Р В»Р С‘ Р Р…Р В° Р С”Р В°Р В¶Р Т‘РЎвЂ№Р в„– РЎРѓР С‘Р СР Р†Р С•Р В»
        # None | list[str] | "a,b"  /// РЎРѓР С—Р С‘РЎРѓР С•Р С” РЎРѓР С‘Р СР Р†Р С•Р В»Р С•Р Р†
        "symbols": None,
        "out": None,  # path | None  /// Р С”Р С•РЎР‚Р ВµР Р…РЎРЉ Р Р†РЎвЂ№РЎвЂ¦Р С•Р Т‘Р Р…РЎвЂ№РЎвЂ¦ Р Т‘Р В°Р Р…Р Р…РЎвЂ№РЎвЂ¦
        "viz": False,  # False | True  /// Р Р†Р С”Р В»РЎР‹РЎвЂЎР С‘РЎвЂљРЎРЉ viz Р Р† headless
        "viz_transport": "tcp",  # tcp | none  /// РЎвЂљРЎР‚Р В°Р Р…РЎРѓР С—Р С•РЎР‚РЎвЂљ viz
        "viz_host": "127.0.0.1",  # host  /// Р В°Р Т‘РЎР‚Р ВµРЎРѓ viz
        "viz_port": 0,  # 0 | int > 0  /// Р С—Р С•РЎР‚РЎвЂљ viz
        "viz_connect": False,  # False | True  /// connect Р С” Р Р†Р Р…Р ВµРЎв‚¬Р Р…Р ВµР СРЎС“ daemon
        "viz_keep_open": False,  # False | True  /// Р Р…Р Вµ Р В·Р В°Р С”РЎР‚РЎвЂ№Р Р†Р В°РЎвЂљРЎРЉ daemon
        "viz_every_steps": 1,  # int > 0  /// Р С—Р ВµРЎР‚Р С‘Р С•Р Т‘ Р С•РЎвЂљР С—РЎР‚Р В°Р Р†Р С”Р С‘ Р С”Р В°Р Т‘РЎР‚Р С•Р Р†
        "record_fields": False,  # False | True  /// Р В·Р В°Р С—Р С‘РЎРѓРЎРЉ fields_hist.npz
        "fields_every_steps": 1,  # int > 0  /// Р С—Р ВµРЎР‚Р С‘Р С•Р Т‘ Р В·Р В°Р С—Р С‘РЎРѓР С‘ Р С—Р С•Р В»Р ВµР в„–
        # None | list[str] | "inv0=1/10,..."  /// Р С‘Р Р…Р Р†Р В°РЎР‚Р С‘Р В°Р Р…РЎвЂљР Р…РЎвЂ№Р Вµ Р С—Р С•РЎвЂљР С•Р С”Р С‘
        "invariant_streams": None,
        "fabric_handshake": False,  # False | True  /// Р Р†Р С”Р В»РЎР‹РЎвЂЎР С‘РЎвЂљРЎРЉ Р В»Р С•Р С”Р В°Р В»РЎРЉР Р…РЎвЂ№Р в„– fabric handshake
        "fabric_required_proof_accepts": 1,  # int >= 1  /// quorum Р Т‘Р В»РЎРЏ proof_ack
        "fabric_required_trust_accepts": 1,  # int >= 1  /// quorum Р Т‘Р В»РЎРЏ trust_ack
        "fabric_required_unique_proof_validators": 1,  # int >= 1  /// РЎС“Р Р…Р С‘Р С”Р В°Р В»РЎРЉР Р…РЎвЂ№Р Вµ proof validators
        "fabric_required_unique_trust_validators": 1,  # int >= 1  /// РЎС“Р Р…Р С‘Р С”Р В°Р В»РЎРЉР Р…РЎвЂ№Р Вµ trust validators
        "fabric_required_validator_ids": None,  # None | list[str] | "v1,v2"  /// Р С•Р В±РЎРЏР В·Р В°РЎвЂљР ВµР В»РЎРЉР Р…РЎвЂ№Р в„– Р Р…Р В°Р В±Р С•РЎР‚ validator ids
        "fabric_handshake_profile": "mvp",  # mvp | production  /// profile-level handshake hardening preset
        "fabric_enforce_required_validator_ids": False,  # False | True  /// Р В¶РЎвЂРЎРѓРЎвЂљР С”Р С• РЎвЂљРЎР‚Р ВµР В±Р С•Р Р†Р В°РЎвЂљРЎРЉ validator_set
        "fabric_enforce_active_validator_membership": False,  # False | True  /// drop ack Р Р†Р Р…Р Вµ active validator registry
        # False | True  /// РЎвЂљРЎР‚Р ВµР В±Р С•Р Р†Р В°РЎвЂљРЎРЉ sender==ack.validator_id Р Т‘Р В»РЎРЏ inline ack payload
        "fabric_enforce_ack_sender_validator_match": False,
        "fabric_enforce_ack_auth_key_id_binding": False,  # False | True  /// bind ack to configured auth_key_id
        # None | list[str] | "v1=kid1,v2=kid2"  /// validator/auth key-id binding rules
        "fabric_validator_auth_key_ids": None,
        "fabric_enforce_ack_transport_identity_binding": False,  # False | True  /// bind ack to transport identity
        # None | list[str] | "v1=cn:validator1,v2=sha256:..."  /// validator/transport-identity binding rules
        "fabric_validator_transport_identities": None,
        "fabric_reject_on_any_reject": False,  # False | True  /// reject quorum Р С—РЎР‚Р С‘ Р В»РЎР‹Р В±Р С•Р С rejected ack
        "fabric_retry_attempts": 2,  # int >= 1  /// retry publish Р Т‘Р В»РЎРЏ ack envelopes
        "fabric_commit_retry_attempts": 2,  # int >= 1  /// retry publish Р Т‘Р В»РЎРЏ commit envelopes
        "fabric_pending_timeout_ms": None,  # None | int >= 0  /// timeout pending quorum (ms), None=off
        "fabric_transport": "memory",  # memory | tcp  /// РЎвЂљРЎР‚Р В°Р Р…РЎРѓР С—Р С•РЎР‚РЎвЂљ fabric
        "fabric_transport_host": "127.0.0.1",  # host  /// Р В°Р Т‘РЎР‚Р ВµРЎРѓ fabric relay
        "fabric_transport_port": 0,  # 0 | int > 0  /// Р С—Р С•РЎР‚РЎвЂљ fabric relay
        "fabric_transport_connect": False,  # False | True  /// connect Р С” Р Р†Р Р…Р ВµРЎв‚¬Р Р…Р ВµР СРЎС“ relay
        "fabric_transport_keep_open": False,  # False | True  /// Р Р…Р Вµ Р В·Р В°Р С”РЎР‚РЎвЂ№Р Р†Р В°РЎвЂљРЎРЉ Р В»Р С•Р С”Р В°Р В»РЎРЉР Р…РЎвЂ№Р в„– relay
        "fabric_transport_backpressure_max_pending": None,  # None | int >= 1  /// live transport queue limit
        "fabric_transport_backpressure_policy": "block",  # block | drop_oldest | drop_newest | fail
        "fabric_transport_backpressure_block_timeout_ms": 200,  # int >= 0  /// block timeout for live queue
        "fabric_transport_dedup_ingress_enabled": False,  # False | True  /// ingress dedup/idempotency cache
        "fabric_transport_dedup_ttl_ms": 30000,  # int >= 1  /// dedup cache TTL (ms)
        "fabric_transport_dedup_max_entries": 10000,  # int >= 1  /// dedup cache capacity
        "fabric_transport_auth_enabled": False,  # False | True  /// HMAC auth for TCP envelopes
        "fabric_transport_auth_key": None,  # None | str  /// shared HMAC key
        "fabric_transport_auth_key_id": None,  # None | str  /// optional key id
        "fabric_transport_tls_enabled": False,  # False | True  /// enable TLS for TCP transport
        "fabric_transport_tls_server_hostname": None,  # None | str  /// TLS server hostname override
        "fabric_transport_tls_ca_file": None,  # None | path  /// CA bundle path
        "fabric_transport_tls_cert_file": None,  # None | path  /// client cert chain (optional mTLS)
        "fabric_transport_tls_key_file": None,  # None | path  /// client key (optional mTLS)
        # False | True  /// require client cert verification for locally started TLS relay
        "fabric_transport_tls_require_client_cert": False,
        "fabric_transport_tls_client_ca_file": None,  # None | path  /// CA bundle for client cert verification
        "fabric_transport_tls_insecure_skip_verify": False,  # False | True  /// disable TLS verification (dev only)
        # auto | cn | san | fingerprint  /// source for envelope transport_identity extraction on TLS relay
        "fabric_transport_tls_identity_source": "auto",
        # False | True  /// fallback to cert fingerprint when selected identity source is missing
        "fabric_transport_tls_identity_fallback_to_fingerprint": False,
        "fabric_artifact_dir": None,  # None | path  /// shared artifact store directory
        "fabric_inline_bridge": True,  # False | True  /// inline payload bridge fallback
        "fabric_replay_sample_stride": 0,  # int >= 0  /// replay-check sampling stride (0=off)
        "fabric_replay_policy_tier": "sampled",  # off | sampled | strict_window  /// validator replay policy tier
        "fabric_replay_strict_window_size": 128,  # int >= 1  /// strict_window replay window size (ticks)
        "fabric_validator_coordination_state_path": None,  # None | path  /// validator coordination state file
        # None | list[path] | "a,b,c"  /// replicated validator coordination state files
        "fabric_validator_coordination_replica_state_paths": None,
        # None | int >= 1  /// read quorum for replicated validator coordination state
        "fabric_validator_coordination_replica_read_quorum": None,
        # None | int >= 1  /// write quorum for replicated validator coordination state
        "fabric_validator_coordination_replica_write_quorum": None,
        "fabric_epoch_state_path": None,  # None | path  /// shared epoch/watermark state file
        "fabric_epoch_replica_state_paths": None,  # None | list[path] | "a,b,c"  /// replicated epoch state files
        "fabric_epoch_replica_read_quorum": None,  # None | int >= 1  /// read quorum for replicated epoch-state
        "fabric_epoch_replica_write_quorum": None,  # None | int >= 1  /// write quorum for replicated epoch-state
        "fabric_epoch_lock_timeout_ms": 5000,  # int >= 1  /// timeout lock epoch-state file
        "fabric_epoch_lock_poll_ms": 10,  # int >= 1  /// poll interval for epoch-state lock
        "fabric_epoch_lock_stale_ms": 30000,  # None | int >= 1  /// stale lock cleanup threshold
        "fabric_epoch_consensus_enabled": False,  # False | True  /// transport pre-consensus for epoch decisions
        "fabric_epoch_consensus_required_total_accepts": 1,  # int >= 1  /// total accepts (incl local)
        "fabric_epoch_consensus_timeout_ms": 200,  # int >= 1  /// timeout proposal/vote collection
        "fabric_epoch_consensus_max_attempts": 1,  # int >= 1  /// max retry rounds for epoch proposal consensus
        "fabric_epoch_consensus_reject_on_any_reject": False,  # False | True  /// reject when any peer rejects
        "fabric_epoch_consensus_channel": "fabric.epoch",  # str  /// channel for epoch consensus envelopes
        "fabric_split_mode_channels": False,  # False | True  /// separate commit/ack channels per mode
        "fabric_delivery_required_receipts": 0,  # int >= 0  /// required delivery_ack receipts (0=off)
        # best_effort | at_least_once | at_least_once_idempotent  /// explicit delivery guarantee profile for report/config contract
        "fabric_delivery_guarantee_mode": "at_least_once_idempotent",
        "fabric_delivery_required_validator_ids": None,  # None | list[str] | "v1,v2"  /// required delivery validators
        "fabric_delivery_enforce_required_validator_ids": False,  # False | True  /// require full delivery validator set
        "fabric_delivery_reject_on_any_reject": False,  # False | True  /// reject delivery on any rejected receipt
        "fabric_delivery_retry_interval_ms": 100,  # int >= 0  /// retry interval for pending delivery receipts
        "fabric_delivery_max_attempts": 3,  # int >= 1  /// max publish attempts per tracked delivery
        "fabric_delivery_timeout_ms": 500,  # int >= 1  /// timeout for tracked delivery receipts
        # None | path  /// persisted delivery tracking/receipt state file (default: <run>/fabric_delivery_tracking_state.json)
        "fabric_delivery_tracking_state_path": None,
        "fabric_delivery_ack_channel": "fabric.delivery.ack",  # str  /// channel for delivery_ack envelopes
        "fabric_delivery_emit_ack": True,  # False | True  /// emit delivery_ack on commit receive
        "fabric_delivery_outbox_path": None,  # None | path  /// file-backed outbox path for undelivered envelopes
        "fabric_delivery_outbox_max_entries": None,  # None | int >= 1  /// max pending envelopes in outbox
        "fabric_delivery_outbox_flush_limit": None,  # None | int >= 1  /// max outbox flush items per cycle
        "fabric_delivery_outbox_drop_policy": "audit_first",  # audit_first | oldest | newest  /// overflow policy
    },
}

