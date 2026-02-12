"""Default single-file config for local development.

This file is a template. `python main.py` (with no args) will copy it into the
repo root as `config.example.py` if missing, and will use that local file on
subsequent launches.
"""

# Можно также реализовать `get_config()` / `load_config()` и вернуть dict.
CONFIG = {
    "backend": "torch",  # torch | numpy  /// вычислительный бэкенд
    "device": "cuda",  # cuda | cpu | cuda:0  /// устройство исполнения
    # minimal | cpu_full  /// режим формирования observables (cpu_full разрешает тяжёлые CPU-анализы)
    "observables_mode": "minimal",
    "trace_boundary_flux": False,  # False | True  /// log Φ_boundary(t) proxies into trace.jsonl
    "watch_trace_enabled": True,  # False | True  /// включить `watch_trace.jsonl` проекцию
    "trace_system_retention_window": 0,  # 0 | int > 0  /// окно хранения System Trace (`trace.jsonl`)
    "trace_watch_retention_window": 0,  # 0 | int > 0  /// окно хранения Watch Trace (`watch_trace.jsonl`)
    "trace_watch_compaction_budget": 0,  # 0 | int > 0  /// budget compaction для Watch Trace
    # policy хранения артефактов по уровням `L0..Ln`; 0/0 = хранить всё
    "artifact_storage_policy": {
        "L0": {
            "trace": {"retention_window": 0, "compaction_budget": 0},
            "watch_trace": {"retention_window": 0, "compaction_budget": 0},
            "watch_contract": {"retention_window": 0, "compaction_budget": 0},
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
    "pattern_reuse_enabled": True,  # False | True  /// включить lookup/reuse паттернов до refine
    # global | portable | strict  /// scope pattern reuse между уровнями/режимами
    "pattern_reuse_scope": "portable",
    "pattern_store_path": None,  # None | path  /// file-backed PatternStore (MVP stub)
    "pattern_cache_capacity": 128,  # int >= 1  /// ёмкость LRU PatternCache
    "pattern_cache_ttl_steps": 4096,  # int >= 1  /// TTL PatternCache в шагах
    "pattern_prune_error_threshold": 0.05,  # float >= 0  /// pruning порог error
    "pattern_prune_deviation_threshold": 0.5,  # float >= 0  /// pruning порог deviation
    "level_policy": {
        "schema_version": "1.16.0",  # semver  /// версия схемы LevelPolicy
        "active_level": "L0",  # Ln  /// активный уровень публикации
        "microsteps_per_global_tick": 1,  # int >= 1  /// внутренняя частота шага
        "batch_size": 1,  # int >= 1  /// размер batched-выполнения
        "commit_stride": 1,  # int >= 1  /// публикация в trace/artefacts раз в N global ticks
        "audit_commit_enabled": False,  # False | True  /// включить thick audit commits
        "audit_commit_stride": 10,  # int >= 1  /// период audit commits в global ticks
        "allow_refinement": True,  # False | True  /// разрешение refine-контура
        # float >= 0  /// порог доли overflow-клеток для detector=`capacity_pressure` (energy_overflow fallback ниже порога)
        "refinement_capacity_overflow_ratio_threshold": 0.15,
        # float >= 0  /// порог средней величины overflow (энергетическая "тяжесть" перегруза)
        "refinement_capacity_overflow_mean_threshold": 0.5,
        # int >= 1  /// минимальное число capacity-signals (ratio + severity), необходимых для detector=`capacity_pressure`
        "refinement_capacity_min_signals": 1,
        # float >= 0  /// ratio-порог для temporal накопления pressure-сигнала
        "refinement_capacity_temporal_ratio_threshold": 0.1,
        # int >= 1  /// размер окна temporal history для pressure-сигнала
        "refinement_capacity_temporal_window": 4,
        # int >= 1  /// сколько попаданий в окно требуется для temporal-signal
        "refinement_capacity_temporal_required_hits": 3,
        # int >= 0  /// learned-signal по reuse hits (0 = disabled)
        "refinement_capacity_learned_hits_threshold": 0,
        # int >= 1  /// окно для cross-level pressure-сигнала
        "refinement_capacity_cross_level_window": 4,
        # int >= 1  /// минимум уникальных уровней в окне для cross-level signal
        "refinement_capacity_cross_level_min_levels": 2,
        # float >= 0  /// operator-driven сигнал (внешний score), threshold для capacity_secondary signal
        "refinement_capacity_operator_score_threshold": 1.0,
        # int >= 1  /// минимум активных cross-node индикаторов (replay_failed/delivery_rejected/delivery_pending)
        "refinement_capacity_cross_node_min_signals": 1,
        # int >= 0  /// distributed-signal: минимум accepted commits из quorum snapshot (0 = disabled)
        "refinement_capacity_distributed_accepted_min": 0,
        # int >= 0  /// signed-signal: минимум суммарных accepted proof/trust ack в evaluations (0 = disabled)
        "refinement_capacity_signed_acks_min": 0,
        # int >= 0  /// consensus-grade signal: минимум accepted commits при нулевых pending/rejected (0 = disabled)
        "refinement_capacity_consensus_accepted_min": 0,
        # float >= 0  /// cryptographic-grade signal: минимум покрытия validator-set в accepted proof/trust
        "refinement_capacity_crypto_validator_coverage_min": 0.0,
        # list[str]  /// required validator ids for attestation-grade coverage check (empty -> registry-based)
        "refinement_capacity_attestation_validator_ids": [],
        # float >= 0  /// минимум покрытия required validators для attestation-grade signal
        "refinement_capacity_attestation_min_coverage": 0.0,
        # int >= 0  /// byzantine-grade signal: минимум accepted commits при чистом consensus/replay/delivery (0 = disabled)
        "refinement_capacity_byzantine_clean_min": 0,
        # [] | "*" | list[str]  /// события, запускающие runtime adaptive окно (microsteps/batch/commit_stride)
        "runtime_adaptive_signal_event_types": [],
        # int >= 1  /// минимальное число runtime-adaptive сигналов, нужных для trigger
        "runtime_adaptive_min_signals": 1,
        # float >= 0  /// runtime-adaptive signal по quality.oscillation_score (0 = disabled)
        "runtime_adaptive_quality_oscillation_threshold": 0.0,
        # float >= 0  /// runtime-adaptive signal по quality.jitter_signature (0 = disabled)
        "runtime_adaptive_quality_jitter_threshold": 0.0,
        # float >= 0  /// runtime-adaptive signal по cost.cpu_time_ms (0 = disabled)
        "runtime_adaptive_cost_cpu_time_ms_threshold": 0.0,
        # False | True  /// auto profile selection: cost-signal -> throughput, event/quality -> stability
        "runtime_adaptive_auto_profile": False,
        # int  /// stability-profile delta для microsteps_per_global_tick
        "runtime_adaptive_stability_microsteps_delta": 1,
        # int  /// stability-profile delta для batch_size
        "runtime_adaptive_stability_batch_size_delta": 0,
        # int  /// stability-profile delta для commit_stride
        "runtime_adaptive_stability_commit_stride_delta": -1,
        # int  /// throughput-profile delta для microsteps_per_global_tick
        "runtime_adaptive_throughput_microsteps_delta": -1,
        # int  /// throughput-profile delta для batch_size
        "runtime_adaptive_throughput_batch_size_delta": 1,
        # int  /// throughput-profile delta для commit_stride
        "runtime_adaptive_throughput_commit_stride_delta": 1,
        # int >= 0  /// cooldown после runtime-adaptive trigger (anti-flap)
        "runtime_adaptive_cooldown_ticks": 0,
        # int >= 1  /// stride sampling для подробных `runtime_adaptive_signal_hits` в policy telemetry
        "runtime_adaptive_telemetry_sample_stride": 1,
        # int >= 1  /// окно rolling aggregation для `runtime_adaptive_aggregate`
        "runtime_adaptive_telemetry_aggregation_window": 8,
        # int >= 1  /// guard: minimum microsteps_per_global_tick для runtime-adaptive применения
        "runtime_adaptive_guard_microsteps_min": 1,
        # int >= 0  /// guard: maximum microsteps_per_global_tick (0 = no max)
        "runtime_adaptive_guard_microsteps_max": 0,
        # int >= 1  /// guard: minimum batch_size для runtime-adaptive применения
        "runtime_adaptive_guard_batch_size_min": 1,
        # int >= 0  /// guard: maximum batch_size (0 = no max)
        "runtime_adaptive_guard_batch_size_max": 0,
        # int >= 1  /// guard: minimum commit_stride для runtime-adaptive применения
        "runtime_adaptive_guard_commit_stride_min": 1,
        # int >= 0  /// guard: maximum commit_stride (0 = no max)
        "runtime_adaptive_guard_commit_stride_max": 0,
        # False | True  /// reject unsafe runtime-adaptive transition instead of clamping
        "runtime_adaptive_guard_reject_unsafe": False,
        # False | True  /// использовать delta mode (relative tuning от базового policy) вместо абсолютных override
        "runtime_adaptive_use_deltas": False,
        # int  /// delta для microsteps_per_global_tick в runtime adaptive окне (используется при runtime_adaptive_use_deltas=True)
        "runtime_adaptive_microsteps_delta": 0,
        # int  /// delta для batch_size в runtime adaptive окне (используется при runtime_adaptive_use_deltas=True)
        "runtime_adaptive_batch_size_delta": 0,
        # int  /// delta для commit_stride в runtime adaptive окне (используется при runtime_adaptive_use_deltas=True)
        "runtime_adaptive_commit_stride_delta": 0,
        # int >= 0  /// override microsteps_per_global_tick в runtime adaptive окне (0 = base policy)
        "runtime_adaptive_microsteps_per_global_tick": 0,
        # int >= 0  /// override batch_size в runtime adaptive окне (0 = base policy)
        "runtime_adaptive_batch_size": 0,
        # int >= 0  /// override commit_stride в runtime adaptive окне (0 = base policy)
        "runtime_adaptive_commit_stride": 0,
        # int >= 0  /// сколько шагов держать runtime adaptive окно после trigger
        "runtime_adaptive_hold_ticks": 0,
        "observability_profile": {
            # "*" | list[str]  /// типы событий, которые попадают в trace
            "allowed_event_types": ["*"],
            # minimal | standard | debug  /// уровень подробности trace
            "detail_mode": "standard",
            # [] | "*" | list[str]  /// adaptive signals (по типам событий), включают временный профиль
            "adaptive_signal_event_types": [],
            # minimal | standard | debug  /// detail_mode при adaptive trigger
            "adaptive_detail_mode": "debug",
            # int >= 0  /// сколько L0-тиков держать adaptive профиль после trigger
            "adaptive_hold_ticks": 0,
            # "*" | list[str]  /// allowed_event_types для adaptive режима
            "adaptive_allowed_event_types": ["*"],
        },
    },
    "width": 24,  # int > 0  /// ширина решётки
    "height": 24,  # int > 0  /// высота решётки
    "boundary": "periodic",  # periodic | open  /// условие границы
    "initial_noise": 0.08,  # float >= 0  /// шум начального E
    # a,b,k,g,t в UI: alpha,beta,kappa,gamma,lambda_t  /// параметры динамики
    "dynamics": {
        "equilibrium_energy": 0.5,  # float 0..1  /// базовый уровень энергии
        "alpha": 0.3,  # float >= 0  /// подавление переноса энтропией
        "beta": 0.8,  # float >= 0  /// вес локального отклонения
        "gamma": 0.1,  # float >= 0  /// вес отклонения соседей
        "kappa": 0.1,  # float >= 0  /// проводимость переноса
        "lambda_t": 1.0,  # float >= 0  /// влияние энтропии на время
        "activation_threshold": 1.0,  # float > 0  /// порог активации переноса
        "energy_bounds": (0.0, 1.0),  # (lo,hi) | None  /// ограничение энергии
    },
    "ui": {
        "seed": 1,  # int >= 0  /// seed для UI-сессии
        "ticks_per_step": 4,  # int > 0  /// L0-тиков на шаг UI
        "tick_interval_ms": 60,  # int >= 1  /// задержка между шагами
        # symbol | joystick_field | joystick_patch | source_sink | none  /// режим влияния
        "influence_mode": "symbol",
        "symbol_id": "pulse",  # list_symbols() | (none)  /// символ влияния
        "amplitude": 1.0,  # float  /// сила влияния
        "influence_duration_steps": 0,  # 0 | int > 0  /// длительность влияния
        "joy_dx": 0.0,  # float -1..1  /// наклон поля по X
        "joy_dy": 0.0,  # float -1..1  /// наклон поля по Y
        "patch_cx": 12,  # int 0..W-1  /// центр патча по X
        "patch_cy": 12,  # int 0..H-1  /// центр патча по Y
        "patch_radius": 6,  # int >= 0  /// радиус патча
        "source_x": 6,  # int 0..W-1  /// X источника энергии
        "source_y": 12,  # int 0..H-1  /// Y источника энергии
        "sink_x": 18,  # int 0..W-1  /// X стока энергии
        "sink_y": 12,  # int 0..H-1  /// Y стока энергии
        "source_value": 1.0,  # float 0..1  /// значение источника
        "sink_value": 0.0,  # float 0..1  /// значение стока
        "record_dir": "runs/out/ui_run",  # path | None  /// директория записи
        "record_fields": False,  # False | True  /// запись fields_hist.npz
        "invariant_streams": "",  # "" | "inv0=1/10,..."  /// инвариантные тики
        "viz_enabled": True,  # False | True  /// включить viz-демон
        "viz_transport": "embedded",  # embedded | tcp | none  /// транспорт визуализации
        "viz_host": "127.0.0.1",  # host  /// адрес viz-демона
        "viz_port": 0,  # 0 | int > 0  /// порт viz-демона
        "viz_connect": False,  # False | True  /// connect к внешнему daemon
        "viz_keep_open": False,  # False | True  /// не закрывать daemon
        "viz_every_steps": 1,  # int > 0  /// период отправки кадров
    },
    "runner": {
        "seed": 1,  # int >= 0  /// seed одиночного запуска
        "seed0": 0,  # int >= 0  /// старт seed для batch
        "steps": 4,  # int > 0  /// тиков на влияние
        # None | list[str] | "a,b"  /// список символов
        "symbols": None,
        "out": None,  # path | None  /// корень выходных данных
        "viz": False,  # False | True  /// включить viz в headless
        "viz_transport": "tcp",  # tcp | none  /// транспорт viz
        "viz_host": "127.0.0.1",  # host  /// адрес viz
        "viz_port": 0,  # 0 | int > 0  /// порт viz
        "viz_connect": False,  # False | True  /// connect к внешнему daemon
        "viz_keep_open": False,  # False | True  /// не закрывать daemon
        "viz_every_steps": 1,  # int > 0  /// период отправки кадров
        "record_fields": False,  # False | True  /// запись fields_hist.npz
        "fields_every_steps": 1,  # int > 0  /// период записи полей
        # None | list[str] | "inv0=1/10,..."  /// инвариантные потоки
        "invariant_streams": None,
        "fabric_handshake": False,  # False | True  /// включить локальный fabric handshake
        "fabric_required_proof_accepts": 1,  # int >= 1  /// quorum для proof_ack
        "fabric_required_trust_accepts": 1,  # int >= 1  /// quorum для trust_ack
        "fabric_required_unique_proof_validators": 1,  # int >= 1  /// уникальные proof validators
        "fabric_required_unique_trust_validators": 1,  # int >= 1  /// уникальные trust validators
        "fabric_required_validator_ids": None,  # None | list[str] | "v1,v2"  /// обязательный набор validator ids
        "fabric_enforce_required_validator_ids": False,  # False | True  /// жёстко требовать validator_set
        "fabric_reject_on_any_reject": False,  # False | True  /// reject quorum при любом rejected ack
        "fabric_retry_attempts": 2,  # int >= 1  /// retry publish для ack envelopes
        "fabric_commit_retry_attempts": 2,  # int >= 1  /// retry publish для commit envelopes
        "fabric_pending_timeout_ms": None,  # None | int >= 0  /// timeout pending quorum (ms), None=off
        "fabric_transport": "memory",  # memory | tcp  /// транспорт fabric
        "fabric_transport_host": "127.0.0.1",  # host  /// адрес fabric relay
        "fabric_transport_port": 0,  # 0 | int > 0  /// порт fabric relay
        "fabric_transport_connect": False,  # False | True  /// connect к внешнему relay
        "fabric_transport_keep_open": False,  # False | True  /// не закрывать локальный relay
        "fabric_transport_backpressure_max_pending": None,  # None | int >= 1  /// live transport queue limit
        "fabric_transport_backpressure_policy": "block",  # block | drop_oldest | drop_newest | fail
        "fabric_transport_backpressure_block_timeout_ms": 200,  # int >= 0  /// block timeout for live queue
        "fabric_artifact_dir": None,  # None | path  /// shared artifact store directory
        "fabric_inline_bridge": True,  # False | True  /// inline payload bridge fallback
        "fabric_replay_sample_stride": 0,  # int >= 0  /// replay-check sampling stride (0=off)
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
        "fabric_epoch_consensus_reject_on_any_reject": False,  # False | True  /// reject when any peer rejects
        "fabric_epoch_consensus_channel": "fabric.epoch",  # str  /// channel for epoch consensus envelopes
        "fabric_split_mode_channels": False,  # False | True  /// separate commit/ack channels per mode
        "fabric_delivery_required_receipts": 0,  # int >= 0  /// required delivery_ack receipts (0=off)
        "fabric_delivery_required_validator_ids": None,  # None | list[str] | "v1,v2"  /// required delivery validators
        "fabric_delivery_enforce_required_validator_ids": False,  # False | True  /// require full delivery validator set
        "fabric_delivery_reject_on_any_reject": False,  # False | True  /// reject delivery on any rejected receipt
        "fabric_delivery_retry_interval_ms": 100,  # int >= 0  /// retry interval for pending delivery receipts
        "fabric_delivery_max_attempts": 3,  # int >= 1  /// max publish attempts per tracked delivery
        "fabric_delivery_timeout_ms": 500,  # int >= 1  /// timeout for tracked delivery receipts
        "fabric_delivery_ack_channel": "fabric.delivery.ack",  # str  /// channel for delivery_ack envelopes
        "fabric_delivery_emit_ack": True,  # False | True  /// emit delivery_ack on commit receive
        "fabric_delivery_outbox_path": None,  # None | path  /// file-backed outbox path for undelivered envelopes
        "fabric_delivery_outbox_max_entries": None,  # None | int >= 1  /// max pending envelopes in outbox
        "fabric_delivery_outbox_flush_limit": None,  # None | int >= 1  /// max outbox flush items per cycle
        "fabric_delivery_outbox_drop_policy": "audit_first",  # audit_first | oldest | newest  /// overflow policy
    },
}
