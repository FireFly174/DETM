from __future__ import annotations

import json

from detm_app.runner.headless import main


def _read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_cli_steps_mode_total_is_default(tmp_path):
    out_dir = tmp_path / "out_total"
    code = main(
        [
            "--backend",
            "numpy",
            "--device",
            "cpu",
            "--seed",
            "1",
            "--steps",
            "7",
            "--symbols",
            "pulse",
            "ring",
            "--out",
            str(out_dir),
        ]
    )
    assert int(code) == 0

    trace_entries = _read_jsonl(out_dir / "seed_0001" / "trace.jsonl")
    assert len(trace_entries) == 7


def test_cli_steps_mode_per_symbol_legacy_behavior(tmp_path):
    out_dir = tmp_path / "out_per_symbol"
    code = main(
        [
            "--backend",
            "numpy",
            "--device",
            "cpu",
            "--seed",
            "1",
            "--steps",
            "7",
            "--steps-mode",
            "per_symbol",
            "--symbols",
            "pulse",
            "ring",
            "--out",
            str(out_dir),
        ]
    )
    assert int(code) == 0

    trace_entries = _read_jsonl(out_dir / "seed_0001" / "trace.jsonl")
    assert len(trace_entries) == 14


def test_cli_accepts_fabric_replay_policy_tier_strict_window(tmp_path):
    out_dir = tmp_path / "out_fabric_replay_tier"
    code = main(
        [
            "--backend",
            "numpy",
            "--device",
            "cpu",
            "--seed",
            "1",
            "--steps",
            "1",
            "--symbols",
            "pulse",
            "--out",
            str(out_dir),
            "--fabric-handshake",
            "--fabric-replay-policy-tier",
            "strict_window",
            "--fabric-replay-strict-window-size",
            "3",
            "--fabric-replay-sample-stride",
            "0",
        ]
    )
    assert int(code) == 0
    report = json.loads((out_dir / "seed_0001" / "fabric_quorum_report.json").read_text(encoding="utf-8"))
    replay = dict(report["replay_sampling"])
    assert replay == {
        "enabled": True,
        "tier": "strict_window",
        "sample_stride": 0,
        "strict_window_size": 3,
        "checks_total": 1,
        "checks_failed": 0,
    }


def test_cli_accepts_validator_coordination_state_path(tmp_path):
    out_dir = tmp_path / "out_fabric_validator_coordination"
    state_path = tmp_path / "validator_coordination_state.json"
    code = main(
        [
            "--backend",
            "numpy",
            "--device",
            "cpu",
            "--seed",
            "1",
            "--steps",
            "1",
            "--symbols",
            "pulse",
            "--out",
            str(out_dir),
            "--fabric-handshake",
            "--fabric-validator-coordination-state-path",
            str(state_path),
        ]
    )
    assert int(code) == 0
    assert state_path.exists()
    report = json.loads((out_dir / "seed_0001" / "fabric_quorum_report.json").read_text(encoding="utf-8"))
    coordination = dict(report["validator_coordination_state"])
    assert bool(coordination["enabled"]) is True
    assert str(coordination["mode"]) == "single_file"
    assert str(coordination["state_path"]) == str(state_path)


def test_cli_accepts_fabric_epoch_consensus_max_attempts(tmp_path):
    out_dir = tmp_path / "out_fabric_epoch_consensus_retries"
    code = main(
        [
            "--backend",
            "numpy",
            "--device",
            "cpu",
            "--seed",
            "1",
            "--steps",
            "1",
            "--symbols",
            "pulse",
            "--out",
            str(out_dir),
            "--fabric-handshake",
            "--fabric-epoch-consensus",
            "--fabric-epoch-consensus-required-total-accepts",
            "2",
            "--fabric-epoch-consensus-timeout-ms",
            "20",
            "--fabric-epoch-consensus-max-attempts",
            "3",
        ]
    )
    assert int(code) == 0
    report = json.loads((out_dir / "seed_0001" / "fabric_quorum_report.json").read_text(encoding="utf-8"))
    consensus = dict(report["epoch_watermark"]["consensus"])
    assert int(consensus["max_attempts"]) == 3
    stats = dict(consensus["stats"])
    assert int(stats["proposals_total"]) == 3
    assert int(stats["retries_total"]) == 2


def test_cli_accepts_fabric_handshake_profile_production(tmp_path):
    out_dir = tmp_path / "out_fabric_handshake_profile_production"
    code = main(
        [
            "--backend",
            "numpy",
            "--device",
            "cpu",
            "--seed",
            "1",
            "--steps",
            "1",
            "--symbols",
            "pulse",
            "--out",
            str(out_dir),
            "--fabric-handshake",
            "--fabric-handshake-profile",
            "production",
            "--fabric-validator-set",
            "validator.seed_0001",
            "--fabric-validator-auth-key-id",
            "validator.seed_0001=kid-local",
        ]
    )
    assert int(code) == 0
    report = json.loads((out_dir / "seed_0001" / "fabric_quorum_report.json").read_text(encoding="utf-8"))
    profile = dict(report["handshake_profile"])
    assert str(profile["profile"]) == "production"
    assert bool(profile["strict_runtime_enforcement"]) is True


def test_cli_rejects_production_profile_without_validator_set(tmp_path):
    out_dir = tmp_path / "out_fabric_handshake_profile_invalid"
    try:
        main(
            [
                "--backend",
                "numpy",
                "--device",
                "cpu",
                "--seed",
                "1",
                "--steps",
                "1",
                "--symbols",
                "pulse",
                "--out",
                str(out_dir),
                "--fabric-handshake",
                "--fabric-handshake-profile",
                "production",
                "--fabric-validator-auth-key-id",
                "validator.seed_0001=kid-local",
            ]
        )
    except ValueError as exc:
        assert "requires non-empty required_validator_ids" in str(exc)
    else:
        raise AssertionError("Expected ValueError for production profile without validator set")


