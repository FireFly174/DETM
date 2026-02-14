from __future__ import annotations

import json
import sys
import types

import pytest

from detm_app.runner.shell import build_shell_contract, main


def test_build_shell_contract_external_mode():
    contract = build_shell_contract(
        controller="external",
        runner="headless",
        viewer="napari",
        forwarded_args=["--seed", "7"],
        napari_options={"host": "127.0.0.1", "port": 5588},
    )
    assert dict(contract["roles"]) == {"controller": "external", "runner": "headless", "viewer": "napari"}
    assert bool(dict(contract["compatibility"])["supported"]) is True
    execution = dict(contract["execution"])
    assert str(execution["mode"]) == "contract_only"
    assert str(execution["producer_entrypoint"]) == "detm_app.runner.headless.main"


def test_shell_orchestrate_local_headless_none_routes_to_cli(monkeypatch):
    calls: dict[str, object] = {}
    fake_cli = types.ModuleType("detm_app.runner.headless")

    def _fake_cli_main(argv=None):
        calls["argv"] = list(argv or [])
        return 5

    fake_cli.main = _fake_cli_main  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "detm_app.runner.headless", fake_cli)

    rc = int(main(["--controller", "local", "--runner", "headless", "--viewer", "none", "--", "--seed", "9"]))
    assert rc == 5
    assert calls["argv"] == ["--seed", "9"]


def test_shell_orchestrate_local_headless_napari_routes_to_napari_lab(monkeypatch):
    calls: dict[str, object] = {}
    fake_napari_lab = types.ModuleType("detm_app.ui.napari.lab")

    def _fake_napari_main(argv=None):
        calls["argv"] = list(argv or [])
        return 6

    fake_napari_lab.main = _fake_napari_main  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "detm_app.ui.napari.lab", fake_napari_lab)

    rc = int(
        main(
            [
                "--controller",
                "local",
                "--runner",
                "headless",
                "--viewer",
                "napari",
                "--host",
                "127.0.0.1",
                "--port",
                "5599",
                "--",
                "--seed",
                "1",
                "--fabric-handshake",
            ]
        )
    )
    assert rc == 6
    argv = list(calls["argv"])
    assert "--host" in argv
    assert "127.0.0.1" in argv
    assert "--port" in argv
    assert "5599" in argv
    assert "--" in argv
    assert "--seed" in argv
    assert "--fabric-handshake" in argv


def test_shell_orchestrate_external_prints_contract(capsys):
    rc = int(
        main(
            [
                "--controller",
                "external",
                "--runner",
                "headless",
                "--viewer",
                "napari",
                "--",
                "--seed",
                "7",
            ]
        )
    )
    assert rc == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert dict(payload["roles"]) == {"controller": "external", "runner": "headless", "viewer": "napari"}
    assert bool(dict(payload["compatibility"])["supported"]) is True


def test_shell_orchestrate_rejects_invalid_role_combination():
    with pytest.raises(SystemExit):
        main(["--controller", "local", "--runner", "headless", "--viewer", "tk"])


def test_shell_orchestrate_rejects_ui_runner_choice():
    with pytest.raises(SystemExit):
        main(["--controller", "local", "--runner", "ui", "--viewer", "none"])

