from __future__ import annotations

import json

import numpy as np

from detm.core.entropy import DynamicsParameters
from detm.runtime.backends.numpy_backend import NumpyBackend
from detm.runtime.config import DETMConfig
from detm.runtime.level_policy import LevelPolicy
from detm.runtime.pattern_memory import get_pattern_runtime_for_state
from detm_app.runner.headless.subscribers.core import attach_core_subscribers
from detm_app.runtime.session import DetmSession
from detm_app.storage.analytics_db import ingest_run, open_run_db


def _read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _seed_hotspot(session: DetmSession, *, amplitude: float = 3.0) -> None:
    state = session.state
    h = int(state.lattice.height)
    w = int(state.lattice.width)
    energy = np.zeros((h, w), dtype=float)
    energy[h // 2, w // 2] = float(amplitude)
    state.field_state.energy = energy
    state.field_state.internal_time = np.zeros_like(energy)
    state.field_state.entropy = NumpyBackend._compute_entropy(energy, session.config.dynamics, boundary=state.lattice.boundary)


def _make_multiscale_run(tmp_path, *, redis_url: str | None = None):
    run_dir = tmp_path / "run_multiscale"
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=9,
        height=9,
        initial_noise=0.0,
        dynamics=DynamicsParameters(energy_bounds=None),
        watch_trace_enabled=True,
        level_policy=LevelPolicy(
            active_level="L0",
            commit_stride=1,
            microsteps_per_global_tick=1,
            audit_commit_enabled=False,
        ),
        multiscale_catalog={
            "enabled": True,
            "mode": "observe",
            "redis_url": redis_url,
            "window_ticks": 2,
            "patch_radius": 1,
            "horizons": [1],
            "quantization": 0.05,
            "candidate_min_support": 1,
            "candidate_min_confidence": 0.0,
            "jump_max_error": 0.05,
            "commit_only_sampling": True,
        },
    )
    session = DetmSession.create(cfg, seed=23)
    attach_core_subscribers(
        session=session,
        config=cfg,
        seed=23,
        out_dir=run_dir,
        level_name="L0",
        invariant_streams=None,
    )
    for idx in range(3):
        _seed_hotspot(session, amplitude=3.0 + (0.1 * idx))
        session.step(None, 1, rng=session.state.restore_rng())
    runtime = getattr(session.state, "_pattern_runtime", None)
    session.close()
    return run_dir, runtime


def _make_multiscale_runtime_with_store(tmp_path):
    store_path = tmp_path / "pattern_store.json"
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=5,
        height=5,
        initial_noise=0.0,
        dynamics=DynamicsParameters(energy_bounds=None),
        pattern_store_path=str(store_path),
        multiscale_catalog={
            "enabled": True,
            "mode": "observe",
            "window_ticks": 2,
            "patch_radius": 1,
            "horizons": [1],
            "quantization": 0.05,
            "candidate_min_support": 1,
            "candidate_min_confidence": 0.0,
            "commit_only_sampling": True,
        },
    )
    session = DetmSession.create(cfg, seed=11)
    runtime = get_pattern_runtime_for_state(state=session.state, config=cfg)
    return session, runtime, store_path


def test_multiscale_catalog_config_roundtrip():
    cfg = DETMConfig.from_dict(
        {
            "backend": "numpy",
            "device": "cpu",
            "shape": [8, 8],
            "multiscale_catalog": {
                "enabled": True,
                "mode": "hint",
                "redis_url": "redis://127.0.0.1:6379/0",
                "window_ticks": 7,
                "patch_radius": 2,
                "horizons": [1, 3, 5],
                "quantization": 0.125,
                "candidate_min_support": 4,
                "candidate_min_confidence": 0.7,
                "jump_max_error": 0.02,
                "commit_only_sampling": False,
            },
        }
    )

    restored = DETMConfig.from_dict(cfg.to_dict())

    assert restored.multiscale_catalog.enabled is True
    assert restored.multiscale_catalog.mode == "hint"
    assert restored.multiscale_catalog.redis_url == "redis://127.0.0.1:6379/0"
    assert restored.multiscale_catalog.window_ticks == 7
    assert restored.multiscale_catalog.patch_radius == 2
    assert restored.multiscale_catalog.horizons == (1, 3, 5)
    assert restored.multiscale_catalog.quantization == 0.125
    assert restored.multiscale_catalog.candidate_min_support == 4
    assert restored.multiscale_catalog.candidate_min_confidence == 0.7
    assert restored.multiscale_catalog.jump_max_error == 0.02
    assert restored.multiscale_catalog.commit_only_sampling is False


def test_multiscale_support_requires_temporal_reuse_not_same_tick_duplicates():
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=5,
        height=5,
        initial_noise=0.0,
        dynamics=DynamicsParameters(energy_bounds=None),
        multiscale_catalog={
            "enabled": True,
            "mode": "observe",
            "window_ticks": 2,
            "patch_radius": 1,
            "horizons": [1],
            "quantization": 0.05,
            "candidate_min_support": 2,
            "candidate_min_confidence": 1.0,
            "commit_only_sampling": True,
        },
    )
    session = DetmSession.create(cfg, seed=7)
    runtime = get_pattern_runtime_for_state(state=session.state, config=cfg)
    energy = np.zeros((5, 5), dtype=float)

    first = runtime.observe_multiscale(
        energy=energy,
        tick=1,
        boundary=str(session.state.lattice.boundary),
        level="L0",
        trace_ref="trace://tick/1",
    )
    second = runtime.observe_multiscale(
        energy=energy,
        tick=2,
        boundary=str(session.state.lattice.boundary),
        level="L0",
        trace_ref="trace://tick/2",
    )
    session.close()

    assert int(first["summary"]["coarsen_candidate_count"]) == 0
    assert int(first["hit_count"]) == 0
    assert int(second["summary"]["coarsen_candidate_count"]) > 0
    assert int(second["hit_count"]) > 0


def test_multiscale_observe_only_writes_artifacts_and_keeps_ring_buffer_bounded(tmp_path):
    run_dir, runtime = _make_multiscale_run(tmp_path)

    candidates = _read_jsonl(run_dir / "multiscale_candidates.jsonl")
    sources = _read_jsonl(run_dir / "bridge_record_sources.jsonl")
    tensions = _read_jsonl(run_dir / "scale_tension.jsonl")
    hits = _read_jsonl(run_dir / "operator_catalog_hits.jsonl")

    assert len(candidates) == 3
    assert len(sources) == 3
    assert len(tensions) == 3
    assert len(hits) == 3
    assert all(row["mode"] == "observe" for row in candidates)
    assert all(isinstance(row["sources"], list) for row in sources)
    assert any(row["sources"] for row in sources)
    assert candidates[-1]["candidates"][0]["source_id"]
    assert any(int(row["summary"]["coarsen_candidate_count"]) > 0 for row in tensions)
    assert int(hits[-1]["hit_count"]) >= 0
    assert runtime is not None
    assert int(runtime.multiscale_snapshot_count()) == 2
    assert int(hits[-1]["source_count"]) >= 0


def test_multiscale_bridge_sources_persist_to_local_source_store(tmp_path):
    session, runtime, store_path = _make_multiscale_runtime_with_store(tmp_path)
    energy = np.zeros((5, 5), dtype=float)

    runtime.observe_multiscale(
        energy=energy,
        tick=1,
        boundary=str(session.state.lattice.boundary),
        level="L0",
        trace_ref="trace://tick/1",
    )
    session.close()

    source_store_path = store_path.with_name("pattern_store.bridge_sources.json")
    payload = json.loads(source_store_path.read_text(encoding="utf-8"))

    assert source_store_path.exists()
    assert payload
    first = next(iter(payload.values()))
    assert first["schema_version"] == "bridge_record_source/v1"
    assert first["source_id"]
    assert first["forward_body"]["type"] == "forward_body_observe_placeholder"
    assert first["reverse_body"]["type"] == "reverse_refine_placeholder"


def test_multiscale_artifacts_and_config_redact_redis_credentials(tmp_path):
    secret_url = "redis://user:secret@127.0.0.1:6379/0"
    run_dir, _runtime = _make_multiscale_run(tmp_path, redis_url=secret_url)

    config_payload = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
    candidates = _read_jsonl(run_dir / "multiscale_candidates.jsonl")

    assert config_payload["multiscale_catalog"]["redis_url"] == "redis://127.0.0.1:6379/0"
    assert "secret" not in json.dumps(candidates[-1], ensure_ascii=False)
    assert candidates[-1]["catalog_backend"]["endpoint"] == "redis://127.0.0.1:6379/0"


def test_multiscale_observe_only_degrades_gracefully_without_redis_dependency(tmp_path):
    run_dir, _runtime = _make_multiscale_run(tmp_path, redis_url="redis://127.0.0.1:6379/0")

    candidates = _read_jsonl(run_dir / "multiscale_candidates.jsonl")

    assert len(candidates) == 3
    assert candidates[-1]["catalog_backend"]["kind"] == "redis"
    assert candidates[-1]["catalog_backend"]["available"] is False


def test_analytics_ingest_indexes_multiscale_artifacts(tmp_path):
    run_dir, _runtime = _make_multiscale_run(tmp_path)

    report = ingest_run(run_dir)

    assert report.status == "ok"
    summary = json.loads((run_dir / "analytics" / "run_summary.json").read_text(encoding="utf-8"))
    assert int(summary["artifact_inventory"]["multiscale_candidates_file_count"]) == 1
    assert int(summary["artifact_inventory"]["bridge_record_sources_file_count"]) == 1
    assert int(summary["artifact_inventory"]["scale_tension_file_count"]) == 1
    assert int(summary["artifact_inventory"]["operator_catalog_hits_file_count"]) == 1

    with open_run_db(run_dir) as conn:
        counts = {
            row["artifact_kind"]: int(row["n"])
            for row in conn.execute(
                """
                SELECT artifact_kind, COUNT(*) AS n
                FROM artifact_refs
                WHERE artifact_kind IN ('multiscale_candidates', 'bridge_record_sources', 'scale_tension', 'operator_catalog_hits')
                GROUP BY artifact_kind
                """
            ).fetchall()
        }
    assert counts == {
        "bridge_record_sources": 3,
        "multiscale_candidates": 3,
        "operator_catalog_hits": 3,
        "scale_tension": 3,
    }
    with open_run_db(run_dir) as conn:
        row = conn.execute(
            """
            SELECT path, size_bytes, sha256, meta_json
            FROM artifact_refs
            WHERE artifact_kind = 'multiscale_candidates' AND tick = 1
            """
        ).fetchone()
    assert row is not None
    meta = json.loads(str(row["meta_json"]))
    assert str(row["path"]) == "multiscale_candidates.jsonl"
    assert row["size_bytes"] is None
    assert row["sha256"] is None
    assert meta["kind"] == "logical_row"
    assert meta["source_artifact_kind"] == "multiscale_candidates_file"
    assert isinstance(meta["row_sha256"], str) and meta["row_sha256"]
