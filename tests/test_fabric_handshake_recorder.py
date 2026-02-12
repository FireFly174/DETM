from __future__ import annotations

import json

from detm_app.session import DetmSession
from detm_app.subscribers import CommitJsonlWriter, FabricHandshakeRecorder
from detm.runtime.config import DETMConfig
from detm.runtime.fabric_envelope import FabricEnvelope
from detm.runtime.level_policy import LevelPolicy


def test_fabric_handshake_recorder_emits_ack_artifacts(tmp_path):
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=6,
        height=6,
        initial_noise=0.01,
        level_policy=LevelPolicy(commit_stride=1, microsteps_per_global_tick=1),
    )
    session = DetmSession.create(cfg, seed=21)
    commits_path = tmp_path / "commits.jsonl"

    CommitJsonlWriter.attach(session.bus, commits_path, node_id="node-handshake", mode="realtime")
    FabricHandshakeRecorder.attach(session.bus, tmp_path, node_id="node-handshake", mode_filter="realtime")

    for _ in range(3):
        session.step(None, 1, rng=session.state.restore_rng())
    session.close()

    ack_path = tmp_path / "fabric_acks.jsonl"
    env_path = tmp_path / "fabric_ack_envelopes.jsonl"
    quorum_path = tmp_path / "fabric_quorum_report.json"
    dead_letters_path = tmp_path / "fabric_dead_letters.json"
    assert ack_path.exists()
    assert env_path.exists()
    assert quorum_path.exists()
    assert dead_letters_path.exists()

    acks = [json.loads(line) for line in ack_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    envs = [json.loads(line) for line in env_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    quorum = json.loads(quorum_path.read_text(encoding="utf-8"))
    dead_letters = json.loads(dead_letters_path.read_text(encoding="utf-8"))

    assert len(acks) == 6  # 3 commits * (proof_ack + trust_ack)
    assert len(envs) == 6
    assert {item["ack_type"] for item in acks} == {"proof_ack", "trust_ack"}
    assert {item["status"] for item in acks} == {"accepted"}
    assert {item["message_type"] for item in envs} == {"proof_ack", "trust_ack"}
    assert int(quorum["accepted_count"]) == 3
    assert int(quorum["pending_count"]) == 0
    assert dict(quorum["validator_registry"]) == {"validators": []}
    assert quorum["pending_timeout_ms"] is None
    assert int(quorum["epoch_watermark"]["node_count"]) == 1
    assert int(quorum["epoch_watermark"]["global"]["epoch"]) == 3
    assert int(quorum["epoch_watermark"]["global"]["watermark"]) == 3
    assert dict(quorum["replay_sampling"]) == {
        "enabled": False,
        "sample_stride": 0,
        "checks_total": 0,
        "checks_failed": 0,
    }
    assert dead_letters == []


def test_fabric_handshake_recorder_validator_set_enforcement_marks_pending(tmp_path):
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=6,
        height=6,
        initial_noise=0.01,
        level_policy=LevelPolicy(commit_stride=1, microsteps_per_global_tick=1),
    )
    session = DetmSession.create(cfg, seed=22)
    commits_path = tmp_path / "commits.jsonl"

    CommitJsonlWriter.attach(session.bus, commits_path, node_id="node-handshake", mode="realtime")
    FabricHandshakeRecorder.attach(
        session.bus,
        tmp_path,
        node_id="node-handshake",
        mode_filter="realtime",
        required_validator_ids=["validator.node-handshake", "validator.external-2"],
        enforce_required_validator_ids=True,
        required_unique_proof_validators=1,
        required_unique_trust_validators=1,
        pending_timeout_ms=0,
    )

    session.step(None, 1, rng=session.state.restore_rng())
    session.close()

    quorum = json.loads((tmp_path / "fabric_quorum_report.json").read_text(encoding="utf-8"))
    assert int(quorum["accepted_count"]) == 0
    assert int(quorum["pending_count"]) == 0
    assert int(quorum["rejected_count"]) == 1
    assert int(quorum["pending_timeout_ms"]) == 0
    assert dict(quorum["validator_registry"]) == {
        "validators": ["validator.external-2", "validator.node-handshake"]
    }
    assert int(quorum["epoch_watermark"]["node_count"]) == 1
    assert bool(quorum["replay_sampling"]["enabled"]) is False


def test_fabric_handshake_recorder_persists_artifacts_when_store_enabled(tmp_path):
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=6,
        height=6,
        initial_noise=0.01,
        level_policy=LevelPolicy(commit_stride=1, microsteps_per_global_tick=1),
    )
    session = DetmSession.create(cfg, seed=23)
    commits_path = tmp_path / "commits.jsonl"
    artifact_dir = tmp_path / "shared_artifacts"

    CommitJsonlWriter.attach(session.bus, commits_path, node_id="node-handshake", mode="realtime")
    FabricHandshakeRecorder.attach(
        session.bus,
        tmp_path,
        node_id="node-handshake",
        mode_filter="realtime",
        artifact_store_dir=str(artifact_dir),
        publish_inline_payload=False,
    )

    session.step(None, 1, rng=session.state.restore_rng())
    session.close()

    commit_files = list((artifact_dir / "commit").glob("*.json"))
    ack_files = list((artifact_dir / "ack").glob("*.json"))
    quorum = json.loads((tmp_path / "fabric_quorum_report.json").read_text(encoding="utf-8"))

    assert len(commit_files) >= 1
    assert len(ack_files) >= 2
    assert dict(quorum["artifact_store"]) == {"root_dir": str(artifact_dir)}
    assert bool(quorum["publish_inline_payload"]) is False
    assert str(quorum["epoch_watermark"]["state_path"]).endswith("epoch_state.json")
    assert str(quorum["epoch_watermark"]["lock"]["lock_path"]).endswith(".lock")


def test_fabric_handshake_recorder_replay_sampling_collects_stats(tmp_path):
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=6,
        height=6,
        initial_noise=0.01,
        level_policy=LevelPolicy(commit_stride=1, microsteps_per_global_tick=1),
    )
    session = DetmSession.create(cfg, seed=24)
    commits_path = tmp_path / "commits.jsonl"
    artifact_dir = tmp_path / "shared_artifacts"

    CommitJsonlWriter.attach(session.bus, commits_path, node_id="node-handshake", mode="realtime")
    FabricHandshakeRecorder.attach(
        session.bus,
        tmp_path,
        node_id="node-handshake",
        mode_filter="realtime",
        artifact_store_dir=str(artifact_dir),
        publish_inline_payload=False,
        replay_sample_stride=1,
    )

    for _ in range(3):
        session.step(None, 1, rng=session.state.restore_rng())
    session.close()

    quorum = json.loads((tmp_path / "fabric_quorum_report.json").read_text(encoding="utf-8"))
    replay = dict(quorum["replay_sampling"])
    assert bool(replay["enabled"]) is True
    assert int(replay["sample_stride"]) == 1
    assert int(replay["checks_total"]) == 3
    assert int(replay["checks_failed"]) == 0


def test_fabric_handshake_recorder_uses_explicit_epoch_state_path(tmp_path):
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=6,
        height=6,
        initial_noise=0.01,
        level_policy=LevelPolicy(commit_stride=1, microsteps_per_global_tick=1),
    )
    session = DetmSession.create(cfg, seed=25)
    commits_path = tmp_path / "commits.jsonl"
    epoch_state_path = tmp_path / "custom_epoch_state.json"

    CommitJsonlWriter.attach(session.bus, commits_path, node_id="node-handshake", mode="realtime")
    FabricHandshakeRecorder.attach(
        session.bus,
        tmp_path,
        node_id="node-handshake",
        mode_filter="realtime",
        epoch_state_path=str(epoch_state_path),
    )

    session.step(None, 1, rng=session.state.restore_rng())
    session.close()

    quorum = json.loads((tmp_path / "fabric_quorum_report.json").read_text(encoding="utf-8"))
    assert epoch_state_path.exists()
    assert str(quorum["epoch_watermark"]["state_path"]) == str(epoch_state_path)


def test_fabric_handshake_recorder_uses_replicated_epoch_state_paths(tmp_path):
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=6,
        height=6,
        initial_noise=0.01,
        level_policy=LevelPolicy(commit_stride=1, microsteps_per_global_tick=1),
    )
    session = DetmSession.create(cfg, seed=26)
    commits_path = tmp_path / "commits.jsonl"
    replica_paths = [
        tmp_path / "epoch_replica_1.json",
        tmp_path / "epoch_replica_2.json",
        tmp_path / "epoch_replica_3.json",
    ]

    CommitJsonlWriter.attach(session.bus, commits_path, node_id="node-handshake", mode="realtime")
    FabricHandshakeRecorder.attach(
        session.bus,
        tmp_path,
        node_id="node-handshake",
        mode_filter="realtime",
        epoch_replica_state_paths=[str(p) for p in replica_paths],
        epoch_replica_read_quorum=2,
        epoch_replica_write_quorum=2,
    )

    session.step(None, 1, rng=session.state.restore_rng())
    session.close()

    quorum = json.loads((tmp_path / "fabric_quorum_report.json").read_text(encoding="utf-8"))
    replication = dict(quorum["epoch_watermark"]["replication"])
    assert replication["mode"] == "replicated"
    assert int(replication["replica_count"]) == 3
    assert int(replication["read_quorum"]) == 2
    assert int(replication["write_quorum"]) == 2


def test_fabric_handshake_recorder_epoch_consensus_timeout_marks_rejected(tmp_path):
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=6,
        height=6,
        initial_noise=0.01,
        level_policy=LevelPolicy(commit_stride=1, microsteps_per_global_tick=1),
    )
    session = DetmSession.create(cfg, seed=27)
    commits_path = tmp_path / "commits.jsonl"

    CommitJsonlWriter.attach(session.bus, commits_path, node_id="node-handshake", mode="realtime")
    FabricHandshakeRecorder.attach(
        session.bus,
        tmp_path,
        node_id="node-handshake",
        mode_filter="realtime",
        reject_on_any_reject=True,
        epoch_consensus_enabled=True,
        epoch_consensus_required_total_accepts=2,
        epoch_consensus_timeout_ms=20,
    )

    session.step(None, 1, rng=session.state.restore_rng())
    session.close()

    acks = [
        json.loads(line)
        for line in (tmp_path / "fabric_acks.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    quorum = json.loads((tmp_path / "fabric_quorum_report.json").read_text(encoding="utf-8"))
    assert int(quorum["rejected_count"]) == 1
    assert {str(ack["status"]) for ack in acks} == {"rejected"}
    assert any("consensus timeout" in str(ack.get("reason")) for ack in acks)
    consensus = dict(quorum["epoch_watermark"]["consensus"])
    assert int(consensus["required_total_accepts"]) == 2


def test_fabric_handshake_recorder_split_mode_channels_routes_realtime_and_audit(tmp_path):
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=6,
        height=6,
        initial_noise=0.01,
        level_policy=LevelPolicy(
            commit_stride=1,
            microsteps_per_global_tick=1,
            audit_commit_enabled=True,
            audit_commit_stride=1,
        ),
    )
    session = DetmSession.create(cfg, seed=28)

    CommitJsonlWriter.attach(session.bus, tmp_path / "commits.jsonl", node_id="node-handshake", mode="realtime")
    CommitJsonlWriter.attach(
        session.bus,
        tmp_path / "commits_audit.jsonl",
        node_id="node-handshake",
        commit_type="proof",
        mode="audit",
    )
    FabricHandshakeRecorder.attach(
        session.bus,
        tmp_path,
        node_id="node-handshake",
        mode_filter=None,
        split_mode_channels=True,
    )

    for _ in range(2):
        session.step(None, 1, rng=session.state.restore_rng())
    session.close()

    envs = [
        json.loads(line)
        for line in (tmp_path / "fabric_ack_envelopes.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    quorum = json.loads((tmp_path / "fabric_quorum_report.json").read_text(encoding="utf-8"))
    channels = {str(row["channel"]) for row in envs}
    assert "fabric.ack.realtime" in channels
    assert "fabric.ack.audit" in channels
    assert len(envs) == 8
    assert int(quorum["accepted_count"]) == 2
    mode_channels = dict(quorum["mode_channels"])
    assert bool(mode_channels["split_mode_channels"]) is True


def test_fabric_handshake_recorder_reports_transport_backpressure_snapshot(tmp_path):
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=6,
        height=6,
        initial_noise=0.01,
        level_policy=LevelPolicy(commit_stride=1, microsteps_per_global_tick=1),
    )
    session = DetmSession.create(cfg, seed=29)
    commits_path = tmp_path / "commits.jsonl"

    CommitJsonlWriter.attach(session.bus, commits_path, node_id="node-handshake", mode="realtime")
    FabricHandshakeRecorder.attach(
        session.bus,
        tmp_path,
        node_id="node-handshake",
        mode_filter="realtime",
        transport_backpressure_max_pending=8,
        transport_backpressure_policy="drop_newest",
        transport_backpressure_block_timeout_ms=50,
    )

    session.step(None, 1, rng=session.state.restore_rng())
    session.close()

    quorum = json.loads((tmp_path / "fabric_quorum_report.json").read_text(encoding="utf-8"))
    backpressure = dict(quorum["transport_backpressure"])
    assert bool(backpressure["enabled"]) is True
    assert int(backpressure["max_pending"]) == 8
    assert str(backpressure["policy"]) == "drop_newest"
    assert int(backpressure["block_timeout_ms"]) == 50


def test_fabric_handshake_recorder_delivery_receipts_accepted(tmp_path):
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=6,
        height=6,
        initial_noise=0.01,
        level_policy=LevelPolicy(commit_stride=1, microsteps_per_global_tick=1),
    )
    session = DetmSession.create(cfg, seed=30)
    commits_path = tmp_path / "commits.jsonl"

    CommitJsonlWriter.attach(session.bus, commits_path, node_id="node-handshake", mode="realtime")
    FabricHandshakeRecorder.attach(
        session.bus,
        tmp_path,
        node_id="node-handshake",
        mode_filter="realtime",
        delivery_required_receipts=1,
        delivery_max_attempts=2,
        delivery_retry_interval_ms=0,
        delivery_timeout_ms=500,
    )

    session.step(None, 1, rng=session.state.restore_rng())
    session.close()

    quorum = json.loads((tmp_path / "fabric_quorum_report.json").read_text(encoding="utf-8"))
    delivery = dict(quorum["delivery_receipts"])
    assert bool(delivery["enabled"]) is True
    assert int(delivery["accepted_count"]) == 1
    assert int(delivery["rejected_count"]) == 0
    assert int(delivery["pending_count"]) == 0


def test_fabric_handshake_recorder_delivery_receipts_rejected_when_emit_ack_disabled(tmp_path):
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=6,
        height=6,
        initial_noise=0.01,
        level_policy=LevelPolicy(commit_stride=1, microsteps_per_global_tick=1),
    )
    session = DetmSession.create(cfg, seed=31)
    commits_path = tmp_path / "commits.jsonl"

    CommitJsonlWriter.attach(session.bus, commits_path, node_id="node-handshake", mode="realtime")
    FabricHandshakeRecorder.attach(
        session.bus,
        tmp_path,
        node_id="node-handshake",
        mode_filter="realtime",
        delivery_required_receipts=1,
        delivery_max_attempts=1,
        delivery_retry_interval_ms=0,
        delivery_timeout_ms=500,
        delivery_emit_ack=False,
    )

    session.step(None, 1, rng=session.state.restore_rng())
    session.close()

    quorum = json.loads((tmp_path / "fabric_quorum_report.json").read_text(encoding="utf-8"))
    delivery = dict(quorum["delivery_receipts"])
    assert bool(delivery["enabled"]) is True
    assert int(delivery["accepted_count"]) == 0
    assert int(delivery["rejected_count"]) == 1


def test_fabric_handshake_recorder_delivery_receipts_enforce_validator_set(tmp_path):
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=6,
        height=6,
        initial_noise=0.01,
        level_policy=LevelPolicy(commit_stride=1, microsteps_per_global_tick=1),
    )
    session = DetmSession.create(cfg, seed=32)
    commits_path = tmp_path / "commits.jsonl"

    CommitJsonlWriter.attach(session.bus, commits_path, node_id="node-handshake", mode="realtime")
    FabricHandshakeRecorder.attach(
        session.bus,
        tmp_path,
        node_id="node-handshake",
        mode_filter="realtime",
        delivery_required_receipts=1,
        delivery_required_validator_ids=["validator.external-1"],
        delivery_enforce_required_validator_ids=True,
        delivery_max_attempts=1,
        delivery_retry_interval_ms=0,
        delivery_timeout_ms=500,
        delivery_emit_ack=True,
    )

    session.step(None, 1, rng=session.state.restore_rng())
    session.close()

    quorum = json.loads((tmp_path / "fabric_quorum_report.json").read_text(encoding="utf-8"))
    delivery = dict(quorum["delivery_receipts"])
    assert bool(delivery["enabled"]) is True
    assert int(delivery["accepted_count"]) == 0
    assert int(delivery["rejected_count"]) == 1
    assert bool(delivery["enforce_required_validator_ids"]) is True
    assert list(delivery["required_validator_ids"]) == ["validator.external-1"]


def test_fabric_handshake_recorder_delivery_receipts_reject_on_any_reject(tmp_path):
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=6,
        height=6,
        initial_noise=0.01,
        level_policy=LevelPolicy(commit_stride=1, microsteps_per_global_tick=1),
    )
    session = DetmSession.create(cfg, seed=33)
    commits_path = tmp_path / "commits.jsonl"

    CommitJsonlWriter.attach(session.bus, commits_path, node_id="node-handshake", mode="realtime")
    recorder = FabricHandshakeRecorder.attach(
        session.bus,
        tmp_path,
        node_id="node-handshake",
        mode_filter="realtime",
        delivery_required_receipts=1,
        delivery_reject_on_any_reject=True,
        delivery_max_attempts=2,
        delivery_retry_interval_ms=0,
        delivery_timeout_ms=500,
        delivery_emit_ack=False,
    )

    session.step(None, 1, rng=session.state.restore_rng())
    pending_ids = list(getattr(recorder, "_delivery_pending", {}).keys())
    assert len(pending_ids) == 1
    delivery_id = str(pending_ids[0])
    recorder._on_delivery_ack_envelope(  # type: ignore[attr-defined]
        FabricEnvelope.from_dict(
            {
                "message_type": "delivery_ack",
                "channel": "fabric.delivery.ack",
                "mode": "realtime",
                "sender": "validator.remote",
                "payload_ref": "artifact://delivery_ack/remote/1",
                "payload_inline": {"delivery_id": delivery_id, "status": "rejected"},
                "delivery_id": delivery_id,
            }
        )
    )
    session.close()

    quorum = json.loads((tmp_path / "fabric_quorum_report.json").read_text(encoding="utf-8"))
    delivery = dict(quorum["delivery_receipts"])
    assert bool(delivery["enabled"]) is True
    assert bool(delivery["reject_on_any_reject"]) is True
    assert int(delivery["accepted_count"]) == 0
    assert int(delivery["rejected_count"]) == 1
