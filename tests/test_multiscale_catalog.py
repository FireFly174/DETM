from __future__ import annotations

import json

import numpy as np
import pytest

from detm.core.entropy import DynamicsParameters
from detm.runtime.backends.numpy_backend import NumpyBackend
from detm.runtime.config import DETMConfig
from detm.runtime.level_policy import LevelPolicy
from detm.runtime.pattern_memory import FileVerificationRunStore, get_pattern_runtime_for_state
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


def _make_multiscale_runtime_for_store_path(store_path):
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
    return session, runtime


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
    bodies = _read_jsonl(run_dir / "trajectory_bodies.jsonl")
    verifications = _read_jsonl(run_dir / "bridge_verifications.jsonl")
    tensions = _read_jsonl(run_dir / "scale_tension.jsonl")
    hits = _read_jsonl(run_dir / "operator_catalog_hits.jsonl")

    assert len(candidates) == 3
    assert len(sources) == 3
    assert len(bodies) == 3
    assert len(verifications) == 3
    assert len(tensions) == 3
    assert len(hits) == 3
    assert all(row["mode"] == "observe" for row in candidates)
    assert all(isinstance(row["sources"], list) for row in sources)
    assert all(isinstance(row["bodies"], list) for row in bodies)
    assert all(isinstance(row["verifications"], list) for row in verifications)
    assert any(row["sources"] for row in sources)
    assert any(row["bodies"] for row in bodies)
    assert candidates[-1]["candidates"][0]["source_id"]
    assert verifications[-1]["verifications"]
    assert bodies[-1]["bodies"][0]["body_id"]
    assert verifications[-1]["verifications"][0]["source_id"]
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
    assert first["db_refs"]["forward_body_id"]
    assert first["db_refs"]["reverse_body_id"]
    assert first["verification_summary"]["verification_count"] >= 0


def test_multiscale_trajectory_bodies_persist_to_local_store(tmp_path):
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

    body_store_path = store_path.with_name("pattern_store.trajectory_bodies.json")
    payload = json.loads(body_store_path.read_text(encoding="utf-8"))

    assert body_store_path.exists()
    assert payload
    roles = {item["body_role"] for item in payload.values()}
    assert roles == {"forward", "reverse"}
    first = next(iter(payload.values()))
    assert first["schema_version"] == "trajectory_body/v1"
    assert first["body_id"]
    assert first["source_id"]


def test_multiscale_bridge_source_verification_summary_updates_on_reuse(tmp_path):
    session, runtime, store_path = _make_multiscale_runtime_with_store(tmp_path)
    energy = np.zeros((5, 5), dtype=float)

    runtime.observe_multiscale(
        energy=energy,
        tick=1,
        boundary=str(session.state.lattice.boundary),
        level="L0",
        trace_ref="trace://tick/1",
    )
    runtime.observe_multiscale(
        energy=energy,
        tick=2,
        boundary=str(session.state.lattice.boundary),
        level="L0",
        trace_ref="trace://tick/2",
    )
    session.close()

    source_store_path = store_path.with_name("pattern_store.bridge_sources.json")
    payload = json.loads(source_store_path.read_text(encoding="utf-8"))
    first = next(iter(payload.values()))

    assert int(first["verification_summary"]["verification_count"]) > 0
    assert int(first["verification_summary"]["success_count"]) > 0
    assert first["verification_summary"]["last_status"] == "matched"


def test_multiscale_verification_runs_persist_to_local_store(tmp_path):
    session, runtime, store_path = _make_multiscale_runtime_with_store(tmp_path)
    energy = np.zeros((5, 5), dtype=float)

    runtime.observe_multiscale(
        energy=energy,
        tick=1,
        boundary=str(session.state.lattice.boundary),
        level="L0",
        trace_ref="trace://tick/1",
    )
    runtime.observe_multiscale(
        energy=energy,
        tick=2,
        boundary=str(session.state.lattice.boundary),
        level="L0",
        trace_ref="trace://tick/2",
    )
    session.close()

    verification_store_path = store_path.with_name("pattern_store.bridge_verification_runs.json")
    payload = json.loads(verification_store_path.read_text(encoding="utf-8"))

    assert verification_store_path.exists()
    assert payload
    matched = next(item for item in payload.values() if item["status"] == "matched")
    assert matched["verification_id"]
    assert matched["schema_version"] == "verification_run/v1"
    assert matched["source_id"]
    assert matched["trace_ref"] == "trace://tick/2"
    assert matched["matched"] is True


def test_multiscale_runtime_flushes_verification_runs_in_batch(tmp_path, monkeypatch):
    session, runtime, _store_path = _make_multiscale_runtime_with_store(tmp_path)
    energy = np.zeros((5, 5), dtype=float)
    calls: list[int] = []

    def _unexpected_upsert(self, record):
        raise AssertionError("verification runs should be flushed in batch")

    def _record_replace_all(self, records):
        calls.append(len(records))

    monkeypatch.setattr(FileVerificationRunStore, "upsert", _unexpected_upsert)
    monkeypatch.setattr(FileVerificationRunStore, "replace_all", _record_replace_all, raising=False)

    runtime.observe_multiscale(
        energy=energy,
        tick=1,
        boundary=str(session.state.lattice.boundary),
        level="L0",
        trace_ref="trace://tick/1",
    )
    session.close()

    assert calls and calls[0] > 0


def test_multiscale_verification_ids_are_unique_across_runs_for_same_store(tmp_path):
    store_path = tmp_path / "shared_pattern_store.json"
    session_a, runtime_a = _make_multiscale_runtime_for_store_path(store_path)
    energy = np.zeros((5, 5), dtype=float)
    runtime_a.observe_multiscale(
        energy=energy,
        tick=1,
        boundary=str(session_a.state.lattice.boundary),
        level="L0",
        trace_ref="trace://tick/1",
    )
    session_a.close()

    verification_store_path = store_path.with_name("shared_pattern_store.bridge_verification_runs.json")
    first_payload = json.loads(verification_store_path.read_text(encoding="utf-8"))
    first_count = len(first_payload)

    session_b, runtime_b = _make_multiscale_runtime_for_store_path(store_path)
    runtime_b.observe_multiscale(
        energy=energy,
        tick=1,
        boundary=str(session_b.state.lattice.boundary),
        level="L0",
        trace_ref="trace://tick/1",
    )
    session_b.close()

    second_payload = json.loads(verification_store_path.read_text(encoding="utf-8"))

    assert first_count > 0
    assert len(second_payload) == first_count * 2


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
    verification_artifact_rows = _read_jsonl(run_dir / "bridge_verifications.jsonl")
    expected_verification_run_count = sum(len(row.get("verifications", [])) for row in verification_artifact_rows)
    expected_last_verification = sorted(
        [
            item
            for row in verification_artifact_rows
            for item in list(row.get("verifications", []))
            if isinstance(item, dict)
        ],
        key=lambda item: (int(item.get("tick", -1)), str(item.get("verification_id", ""))),
    )[-1]

    report = ingest_run(run_dir)

    assert report.status == "ok"
    summary = json.loads((run_dir / "analytics" / "run_summary.json").read_text(encoding="utf-8"))
    assert int(summary["artifact_inventory"]["multiscale_candidates_file_count"]) == 1
    assert int(summary["artifact_inventory"]["bridge_record_sources_file_count"]) == 1
    assert int(summary["artifact_inventory"]["trajectory_bodies_file_count"]) == 1
    assert int(summary["artifact_inventory"]["bridge_verifications_file_count"]) == 1
    assert int(summary["artifact_inventory"]["scale_tension_file_count"]) == 1
    assert int(summary["artifact_inventory"]["operator_catalog_hits_file_count"]) == 1
    assert int(summary["counts"]["verification_run_count"]) == expected_verification_run_count
    assert summary["final_verification_run"]["verification_id"]
    assert summary["final_verification_run"]["schema_version"] == "verification_run/v1"
    assert summary["final_verification_run"]["status"] in {"observed", "matched", "mismatch"}

    verification_windows = _read_jsonl(run_dir / "analytics" / "verification_windows.jsonl")
    assert len(verification_windows) == expected_verification_run_count
    assert verification_windows[-1]["verification_id"]
    assert verification_windows[-1]["source_id"]
    assert verification_windows[-1]["status"] in {"observed", "matched", "mismatch"}

    with open_run_db(run_dir) as conn:
        counts = {
            row["artifact_kind"]: int(row["n"])
            for row in conn.execute(
                """
                SELECT artifact_kind, COUNT(*) AS n
                FROM artifact_refs
                WHERE artifact_kind IN ('multiscale_candidates', 'bridge_record_sources', 'trajectory_bodies', 'bridge_verifications', 'scale_tension', 'operator_catalog_hits')
                GROUP BY artifact_kind
                """
            ).fetchall()
        }
    assert counts == {
        "bridge_record_sources": 3,
        "bridge_verifications": 3,
        "multiscale_candidates": 3,
        "operator_catalog_hits": 3,
        "scale_tension": 3,
        "trajectory_bodies": 3,
    }
    with open_run_db(run_dir) as conn:
        verification_rows = conn.execute(
            """
            SELECT verification_id, source_id, tick, trace_ref, status, matched, confidence, support, usage_count
            FROM bridge_verification_runs
            ORDER BY tick, verification_id
            """
        ).fetchall()
    assert len(verification_rows) == expected_verification_run_count
    assert verification_rows[-1]["verification_id"]
    assert verification_rows[-1]["source_id"]
    assert int(verification_rows[-1]["tick"]) == int(expected_last_verification["tick"])
    assert str(verification_rows[-1]["trace_ref"]) == str(expected_last_verification["trace_ref"])
    assert str(verification_rows[-1]["status"]) in {"observed", "matched", "mismatch"}
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

    with open_run_db(run_dir) as conn:
        verification_row = conn.execute(
            """
            SELECT path, meta_json
            FROM artifact_refs
            WHERE artifact_kind = 'bridge_verifications' AND tick = 2
            """
        ).fetchone()
    assert verification_row is not None
    verification_meta = json.loads(str(verification_row["meta_json"]))
    assert str(verification_row["path"]) == "bridge_verifications.jsonl"
    assert verification_meta["verifications"][0]["verification_id"]
    assert verification_meta["verifications"][0]["status"] in {"observed", "matched", "mismatch"}


def test_analytics_ingest_skips_invalid_verification_rows(tmp_path):
    run_dir, _runtime = _make_multiscale_run(tmp_path)
    invalid_rows = [
        {
            "tick": 1,
            "trace_ref": "trace://tick/1",
            "mode": "observe",
            "catalog_backend": {"kind": "local", "available": True},
            "verifications": [
                {"verification_id": "", "tick": 1, "status": "observed"},
                {"verification_id": "", "tick": 1, "status": "observed"},
            ],
        }
    ]
    (run_dir / "bridge_verifications.jsonl").write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in invalid_rows) + "\n",
        encoding="utf-8",
    )

    report = ingest_run(run_dir)

    assert report.status == "partial"
    assert any(issue.code == "invalid_bridge_verification_row" for issue in report.issues)
    with open_run_db(run_dir) as conn:
        count = conn.execute("SELECT COUNT(*) AS n FROM bridge_verification_runs").fetchone()["n"]
    assert int(count) == 0
