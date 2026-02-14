from __future__ import annotations

import json
import sys
import types

from detm_app.ui.napari import lab as napari_lab
from detm_app.ui.napari.lab import _build_producer_command, _normalize_forwarded_args


def test_normalize_forwarded_args_strips_separator():
    assert _normalize_forwarded_args(["--", "--seed", "7"]) == ["--seed", "7"]
    assert _normalize_forwarded_args(["--seed", "7"]) == ["--seed", "7"]


def test_build_producer_command_contains_viz_tcp_defaults():
    cmd = _build_producer_command(
        host="127.0.0.1",
        port=5588,
        producer_args=["--", "--seed", "11", "--steps", "200"],
    )
    assert cmd[:2] == [sys.executable, "-c"]
    assert "detm_app.runner.headless" in cmd[2]
    assert "--viz" in cmd
    assert "--viz-transport" in cmd
    assert "tcp" in cmd
    assert "--viz-host" in cmd
    assert "--viz-port" in cmd
    assert "--viz-keep-open" in cmd
    assert "--seed" in cmd
    assert "11" in cmd
    assert "--steps" in cmd
    assert "200" in cmd


def test_napari_lab_main_forwards_fabric_args_to_producer(monkeypatch):
    captured: dict[str, object] = {}

    class _FakePopen:
        def __init__(self, cmd):
            captured["producer_cmd"] = list(cmd)
            self._terminated = False

        def poll(self):
            return None

        def terminate(self):
            self._terminated = True
            captured["terminated"] = True

        def wait(self, timeout=None):
            captured["wait_timeout"] = timeout
            return 0

        def kill(self):
            captured["killed"] = True
            return None

    def _fake_wait_for_endpoint(*, host, port, timeout_s, producer):
        captured["wait_args"] = {
            "host": str(host),
            "port": int(port),
            "timeout_s": float(timeout_s),
            "producer_type": type(producer).__name__,
        }

    def _fake_run_napari_subscriber(**kwargs):
        captured["subscriber_kwargs"] = dict(kwargs)
        return 0

    fake_subscriber_module = types.ModuleType("detm_app.ui.napari.subscriber")
    fake_subscriber_module.run_napari_subscriber = _fake_run_napari_subscriber
    monkeypatch.setitem(sys.modules, "detm_app.ui.napari.subscriber", fake_subscriber_module)
    monkeypatch.setattr(napari_lab.subprocess, "Popen", _FakePopen)
    monkeypatch.setattr(napari_lab, "_wait_for_tcp_endpoint", _fake_wait_for_endpoint)

    rc = napari_lab.main(
        [
            "--host",
            "127.0.0.1",
            "--port",
            "5589",
            "--",
            "--seed",
            "7",
            "--steps",
            "200",
            "--steps-mode",
            "total",
            "--fabric-handshake",
        ]
    )

    assert int(rc) == 0
    cmd = list(captured.get("producer_cmd", []))
    assert "--seed" in cmd
    assert "7" in cmd
    assert "--steps" in cmd
    assert "200" in cmd
    assert "--steps-mode" in cmd
    assert "total" in cmd
    assert "--fabric-handshake" in cmd
    wait_args = dict(captured.get("wait_args", {}))
    assert wait_args.get("host") == "127.0.0.1"
    assert int(wait_args.get("port", 0)) == 5589
    subscriber_kwargs = dict(captured.get("subscriber_kwargs", {}))
    assert subscriber_kwargs.get("host") == "127.0.0.1"
    assert int(subscriber_kwargs.get("port", 0)) == 5589
    assert subscriber_kwargs.get("startup_only") is False
    startup_profile = dict(subscriber_kwargs.get("startup_profile", {}))
    assert isinstance(startup_profile, dict)
    assert startup_profile.get("viewer_only") is False
    assert startup_profile.get("startup_only") is False
    assert isinstance(startup_profile.get("producer_wait_s"), float)
    assert bool(captured.get("terminated")) is True


def test_napari_lab_main_forwards_config_and_preset_to_producer(monkeypatch):
    captured: dict[str, object] = {}

    class _FakePopen:
        def __init__(self, cmd):
            captured["producer_cmd"] = list(cmd)

        def poll(self):
            return None

        def terminate(self):
            return None

        def wait(self, timeout=None):
            return 0

        def kill(self):
            return None

    def _fake_wait_for_endpoint(*, host, port, timeout_s, producer):
        captured["wait_args"] = (str(host), int(port), float(timeout_s), type(producer).__name__)

    def _fake_run_napari_subscriber(**kwargs):
        captured["subscriber_kwargs"] = dict(kwargs)
        return 0

    fake_subscriber_module = types.ModuleType("detm_app.ui.napari.subscriber")
    fake_subscriber_module.run_napari_subscriber = _fake_run_napari_subscriber
    monkeypatch.setitem(sys.modules, "detm_app.ui.napari.subscriber", fake_subscriber_module)
    monkeypatch.setattr(napari_lab.subprocess, "Popen", _FakePopen)
    monkeypatch.setattr(napari_lab, "_wait_for_tcp_endpoint", _fake_wait_for_endpoint)

    rc = napari_lab.main(
        [
            "--preset",
            "default",
            "--config",
            "config.local.py",
            "--host",
            "127.0.0.1",
            "--port",
            "5592",
            "--",
            "--seed",
            "3",
        ]
    )

    assert int(rc) == 0
    cmd = list(captured.get("producer_cmd", []))
    assert "--preset" in cmd
    assert "default" in cmd
    assert "--config" in cmd
    assert "config.local.py" in cmd
    assert "--seed" in cmd
    assert "3" in cmd


def test_napari_lab_main_viewer_only_skips_producer(monkeypatch):
    captured: dict[str, object] = {"popen_called": False}

    class _FailPopen:
        def __init__(self, _cmd):
            captured["popen_called"] = True
            raise AssertionError("Popen must not be called in --viewer-only mode")

    def _fake_run_napari_subscriber(**kwargs):
        captured["subscriber_kwargs"] = dict(kwargs)
        return 0

    fake_subscriber_module = types.ModuleType("detm_app.ui.napari.subscriber")
    fake_subscriber_module.run_napari_subscriber = _fake_run_napari_subscriber
    monkeypatch.setitem(sys.modules, "detm_app.ui.napari.subscriber", fake_subscriber_module)
    monkeypatch.setattr(napari_lab.subprocess, "Popen", _FailPopen)

    rc = napari_lab.main(["--viewer-only", "--host", "127.0.0.1", "--port", "5590"])

    assert int(rc) == 0
    assert bool(captured.get("popen_called")) is False
    subscriber_kwargs = dict(captured.get("subscriber_kwargs", {}))
    assert subscriber_kwargs.get("host") == "127.0.0.1"
    assert int(subscriber_kwargs.get("port", 0)) == 5590
    assert subscriber_kwargs.get("startup_only") is False
    startup_profile = dict(subscriber_kwargs.get("startup_profile", {}))
    assert startup_profile.get("viewer_only") is True
    assert startup_profile.get("startup_only") is False
    assert startup_profile.get("producer_wait_s") is None
    assert startup_profile.get("first_frame_status") == "viewer_only"


def test_napari_lab_main_writes_phase_profile_json(monkeypatch, tmp_path):
    def _fake_run_napari_subscriber(**kwargs):
        startup_profile = kwargs["startup_profile"]
        startup_profile["napari_qt_import_s"] = 0.1234567
        startup_profile["viewer_create_s"] = 0.4567891
        startup_profile["first_frame_s"] = 0.7891234
        startup_profile["first_frame_status"] = "rendered"
        return 0

    fake_subscriber_module = types.ModuleType("detm_app.ui.napari.subscriber")
    fake_subscriber_module.run_napari_subscriber = _fake_run_napari_subscriber
    monkeypatch.setitem(sys.modules, "detm_app.ui.napari.subscriber", fake_subscriber_module)

    out_path = tmp_path / "napari_phase_profile.json"
    rc = napari_lab.main(
        [
            "--viewer-only",
            "--startup-only",
            "--host",
            "127.0.0.1",
            "--port",
            "5591",
            "--phase-profile-json",
            str(out_path),
        ]
    )

    assert int(rc) == 0
    assert out_path.exists()
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload.get("host") == "127.0.0.1"
    assert int(payload.get("port", 0)) == 5591
    assert payload.get("viewer_only") is True
    assert payload.get("startup_only") is True
    assert float(payload.get("napari_qt_import_s", 0.0)) == 0.123457
    assert float(payload.get("viewer_create_s", 0.0)) == 0.456789
    assert float(payload.get("first_frame_s", 0.0)) == 0.789123
    assert payload.get("first_frame_status") == "rendered"


def test_napari_lab_main_interactive_routes_to_interactive_runner(monkeypatch):
    captured: dict[str, object] = {}

    class _FailPopen:
        def __init__(self, _cmd):
            raise AssertionError("Popen must not be called in --interactive mode")

    def _fake_run_napari_interactive(*, preset, override_path, autoscale, title):
        captured["preset"] = str(preset)
        captured["override_path"] = override_path
        captured["autoscale"] = bool(autoscale)
        captured["title"] = str(title)
        return 0

    fake_interactive_module = types.ModuleType("detm_app.ui.napari.interactive")
    fake_interactive_module.run_napari_interactive = _fake_run_napari_interactive
    monkeypatch.setitem(sys.modules, "detm_app.ui.napari.interactive", fake_interactive_module)
    monkeypatch.setattr(napari_lab.subprocess, "Popen", _FailPopen)

    rc = napari_lab.main(
        [
            "--interactive",
            "--preset",
            "default",
            "--config",
            "config.example.py",
            "--autoscale",
            "--title",
            "DETM interactive",
        ]
    )

    assert int(rc) == 0
    assert captured.get("preset") == "default"
    assert captured.get("override_path") == "config.example.py"
    assert captured.get("autoscale") is True
    assert captured.get("title") == "DETM interactive"


def test_napari_lab_main_interactive_rejects_viewer_only():
    try:
        napari_lab.main(["--interactive", "--viewer-only"])
    except SystemExit as exc:
        assert "--interactive cannot be combined with --viewer-only" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected SystemExit for incompatible --interactive/--viewer-only")


def test_napari_lab_main_interactive_rejects_startup_only():
    try:
        napari_lab.main(["--interactive", "--startup-only"])
    except SystemExit as exc:
        assert "--interactive cannot be combined with --startup-only" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected SystemExit for incompatible --interactive/--startup-only")
