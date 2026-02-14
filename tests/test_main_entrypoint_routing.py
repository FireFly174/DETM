from __future__ import annotations

import runpy
import sys
import types
from pathlib import Path


def _load_main_callable():
    module_globals = runpy.run_path(str((Path(__file__).resolve().parent.parent / "main.py")), run_name="detm_main_test")
    return module_globals["main"]


def test_main_entrypoint_routes_napari_to_detm_app_napari_lab(monkeypatch):
    main_fn = _load_main_callable()
    calls: dict[str, object] = {}

    fake_napari_lab = types.ModuleType("detm_app.ui.napari.lab")

    def _fake_napari_main(argv=None):
        calls["argv"] = list(argv or [])
        return 17

    fake_napari_lab.main = _fake_napari_main  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "detm_app.ui.napari.lab", fake_napari_lab)
    monkeypatch.setattr(sys, "argv", ["main.py", "napari", "--host", "127.0.0.1", "--port", "5588"])

    rc = int(main_fn())
    assert rc == 17
    assert calls["argv"] == ["--host", "127.0.0.1", "--port", "5588"]


def test_main_entrypoint_routes_shell_to_detm_app_orchestrate(monkeypatch):
    main_fn = _load_main_callable()
    calls: dict[str, object] = {}

    fake_orchestrate = types.ModuleType("detm_app.runner.shell")

    def _fake_shell_main(argv=None):
        calls["argv"] = list(argv or [])
        return 19

    fake_orchestrate.main = _fake_shell_main  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "detm_app.runner.shell", fake_orchestrate)
    monkeypatch.setattr(sys, "argv", ["main.py", "shell", "--controller", "external"])

    rc = int(main_fn())
    assert rc == 19
    assert calls["argv"] == ["--controller", "external"]


def test_main_entrypoint_routes_headless_to_detm_app_cli(monkeypatch):
    main_fn = _load_main_callable()
    calls: dict[str, object] = {}

    fake_cli = types.ModuleType("detm_app.runner.headless")

    def _fake_cli_main(argv=None):
        calls["argv"] = list(argv or [])
        return 23

    fake_cli.main = _fake_cli_main  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "detm_app.runner.headless", fake_cli)
    monkeypatch.setattr(sys, "argv", ["main.py", "--seed", "3", "--steps", "5"])

    rc = int(main_fn())
    assert rc == 23
    assert calls["argv"] == ["--seed", "3", "--steps", "5"]


def test_main_entrypoint_routes_explicit_headless_subcommand_to_cli(monkeypatch):
    main_fn = _load_main_callable()
    calls: dict[str, object] = {}

    fake_cli = types.ModuleType("detm_app.runner.headless")

    def _fake_cli_main(argv=None):
        calls["argv"] = list(argv or [])
        return 27

    fake_cli.main = _fake_cli_main  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "detm_app.runner.headless", fake_cli)
    monkeypatch.setattr(sys, "argv", ["main.py", "headless", "--seed", "11"])

    rc = int(main_fn())
    assert rc == 27
    assert calls["argv"] == ["--seed", "11"]


def test_main_entrypoint_routes_ui_alias_to_detm_app_napari_lab(monkeypatch):
    main_fn = _load_main_callable()
    calls: dict[str, object] = {}

    fake_napari_lab = types.ModuleType("detm_app.ui.napari.lab")

    def _fake_napari_main(argv=None):
        calls["argv"] = list(argv or [])
        return 29

    fake_napari_lab.main = _fake_napari_main  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "detm_app.ui.napari.lab", fake_napari_lab)
    monkeypatch.setattr(sys, "argv", ["main.py", "ui", "--host", "127.0.0.1", "--port", "5588"])

    rc = int(main_fn())
    assert rc == 29
    assert calls["argv"] == ["--host", "127.0.0.1", "--port", "5588"]


def test_main_entrypoint_no_args_uses_local_config(monkeypatch):
    main_fn = _load_main_callable()
    calls: dict[str, object] = {}
    local_config = Path("config.example.py")

    def _fake_ensure_local_config(repo_root: Path) -> Path:
        calls["repo_root"] = repo_root
        return local_config

    def _fake_napari_main(argv):
        calls["napari_argv"] = list(argv)
        return 31

    monkeypatch.setitem(main_fn.__globals__, "_ensure_local_config", _fake_ensure_local_config)
    monkeypatch.setitem(main_fn.__globals__, "_napari_main", _fake_napari_main)
    monkeypatch.setattr(sys, "argv", ["main.py"])

    rc = int(main_fn())
    assert rc == 31
    assert isinstance(calls.get("repo_root"), Path)
    assert calls["napari_argv"] == ["--interactive", "--config", str(local_config)]


def test_main_entrypoint_help_shows_launcher_help_without_internal_cli_flags(monkeypatch, capsys):
    main_fn = _load_main_callable()
    monkeypatch.setattr(sys, "argv", ["main.py", "--help"])

    rc = int(main_fn())
    assert rc == 0
    out = capsys.readouterr().out
    assert "python main.py headless --help" in out
    assert "python main.py napari --help" in out
    assert "--fabric-handshake" not in out

