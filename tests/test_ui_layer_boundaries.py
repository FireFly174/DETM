from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _imported_modules(path: Path) -> list[str]:
    source = path.read_text(encoding="utf-8-sig")
    tree = ast.parse(source, filename=str(path))
    out: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                out.append(node.module)
    return out


def _python_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.py") if path.is_file())


def _read_text_first_existing(*paths: Path) -> str:
    for path in paths:
        if path.exists():
            return path.read_text(encoding="utf-8")
    raise FileNotFoundError(f"No expected file found: {[str(p) for p in paths]}")


def test_napari_and_config_do_not_import_tk_modules() -> None:
    roots = [
        ROOT / "detm_app" / "ui" / "napari",
        ROOT / "detm_app" / "config",
    ]
    offenders: list[str] = []
    for sub_root in roots:
        for path in _python_files(sub_root):
            modules = _imported_modules(path)
            if any(module.startswith("detm_app.ui.tk") for module in modules):
                offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


def test_config_layer_does_not_import_runner_modules() -> None:
    offenders: list[str] = []
    for path in _python_files(ROOT / "detm_app" / "config"):
        modules = _imported_modules(path)
        if any(module.startswith("detm_app.runner") for module in modules):
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


def test_ui_runtime_does_not_import_frontend_layers() -> None:
    offenders: list[str] = []
    path = ROOT / "detm_app" / "runtime" / "ui_runtime.py"
    modules = _imported_modules(path)
    if any(module.startswith("detm_app.ui.tk") for module in modules):
        offenders.append(str(path.relative_to(ROOT)))
    if any(module.startswith("detm_app.ui.napari") for module in modules):
        offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


def test_runner_shell_uses_viewer_registry_not_direct_ui_imports() -> None:
    path = ROOT / "detm_app" / "runner" / "shell.py"
    modules = _imported_modules(path)
    assert not any(module.startswith("detm_app.ui.") for module in modules)
    assert "detm_app.runner.viewer_registry" in modules


def test_headless_runner_uses_split_parser_and_option_modules() -> None:
    main_path = ROOT / "detm_app" / "runner" / "headless" / "main.py"
    main_source = main_path.read_text(encoding="utf-8")
    assert "from detm_app.runner.headless.options import HeadlessMainOptions, resolve_headless_main_options" in main_source
    assert "from detm_app.runner.headless.parser import build_headless_parser" in main_source

    parser_path = ROOT / "detm_app" / "runner" / "headless" / "parser.py"
    parser_source = parser_path.read_text(encoding="utf-8")
    assert "from detm_app.runner.headless.parser_fabric import add_fabric_arguments" in parser_source
    assert "add_fabric_arguments(ap)" in parser_source
    parser_fabric_init_path = ROOT / "detm_app" / "runner" / "headless" / "parser_fabric" / "__init__.py"
    parser_fabric_init_source = parser_fabric_init_path.read_text(encoding="utf-8")
    assert "from detm_app.runner.headless.parser_fabric.flow import add_fabric_arguments" in parser_fabric_init_source
    parser_fabric_flow_path = ROOT / "detm_app" / "runner" / "headless" / "parser_fabric" / "flow.py"
    parser_fabric_flow_source = parser_fabric_flow_path.read_text(encoding="utf-8")
    assert "from detm_app.runner.headless.parser_fabric.handshake import add_handshake_arguments" in parser_fabric_flow_source
    assert "from detm_app.runner.headless.parser_fabric.transport import add_transport_arguments" in parser_fabric_flow_source
    assert "from detm_app.runner.headless.parser_fabric.coordination import add_coordination_arguments" in parser_fabric_flow_source
    assert "from detm_app.runner.headless.parser_fabric.delivery import add_delivery_arguments" in parser_fabric_flow_source

    options_path = ROOT / "detm_app" / "runner" / "headless" / "options.py"
    options_source = options_path.read_text(encoding="utf-8")
    assert "from detm_app.runner.headless.options_fabric import resolve_headless_fabric_options" in options_source
    assert "from detm_app.runner.headless.options_model import HeadlessMainOptions" in options_source
    options_fabric_init_path = ROOT / "detm_app" / "runner" / "headless" / "options_fabric" / "__init__.py"
    options_fabric_init_source = options_fabric_init_path.read_text(encoding="utf-8")
    assert "from detm_app.runner.headless.options_fabric.flow import resolve_headless_fabric_options" in options_fabric_init_source
    options_fabric_flow_path = ROOT / "detm_app" / "runner" / "headless" / "options_fabric" / "flow.py"
    options_fabric_flow_source = options_fabric_flow_path.read_text(encoding="utf-8")
    assert "from detm_app.runner.headless.options_fabric.handshake import resolve_handshake_fabric_options" in options_fabric_flow_source
    assert "from detm_app.runner.headless.options_fabric.transport import resolve_transport_fabric_options" in options_fabric_flow_source
    assert "from detm_app.runner.headless.options_fabric.coordination import resolve_coordination_fabric_options" in options_fabric_flow_source
    assert "from detm_app.runner.headless.options_fabric.delivery import resolve_delivery_fabric_options" in options_fabric_flow_source

    subscribers_init_path = ROOT / "detm_app" / "runner" / "headless" / "subscribers" / "__init__.py"
    subscribers_init_source = subscribers_init_path.read_text(encoding="utf-8")
    assert "from detm_app.runner.headless.subscribers.flow import attach_headless_subscribers" in subscribers_init_source
    subscribers_flow_path = ROOT / "detm_app" / "runner" / "headless" / "subscribers" / "flow.py"
    subscribers_flow_source = subscribers_flow_path.read_text(encoding="utf-8")
    assert "from detm_app.runner.headless.subscribers.core import attach_core_subscribers" in subscribers_flow_source
    assert "from detm_app.runner.headless.subscribers.fabric import attach_fabric_handshake_subscriber" in subscribers_flow_source
    assert "from detm_app.runner.headless.subscribers.streaming import attach_streaming_subscribers" in subscribers_flow_source

    options_model_path = ROOT / "detm_app" / "runner" / "headless" / "options_model.py"
    options_model_source = options_model_path.read_text(encoding="utf-8")
    assert "class HeadlessMainOptions:" in options_model_source


def test_tk_runner_wrapper_points_to_launcher() -> None:
    runner_path = ROOT / "detm_app" / "ui" / "tk" / "runner" / "__init__.py"
    source = runner_path.read_text(encoding="utf-8")
    assert "from detm_app.ui.tk.runner.launcher import DetmTkRunner, UiRunSettings, launch_tk_ui" in source


def test_tk_launcher_reuses_runtime_and_batch_services() -> None:
    launcher_path = ROOT / "detm_app" / "ui" / "tk" / "runner" / "launcher.py"
    source = launcher_path.read_text(encoding="utf-8")
    assert "from detm_app.runtime.ui_runtime import DetmUiRunner" in source
    assert "from detm_app.config.ui_models import UiRunSettings" in source
    assert "from detm_app.ui.tk.runner.flow import (" in source
    assert "TkSettingsFlow" in source
    assert "build_launcher_layout" in source
    assert "install_fullscreen_bindings" in source
    assert "configure_root_grid" in source
    assert "DetmTkRunner = DetmUiRunner" in source

    tk_viz_init_source = _read_text_first_existing(
        ROOT / "detm_app" / "ui" / "tk" / "runner" / "flow" / "viz" / "__init__.py",
        ROOT / "detm_app" / "ui" / "tk" / "runner" / "flow" / "__init__.py",
    )
    assert ("from detm_app.ui.tk.runner.flow.viz.clipboard import install_clipboard_shortcuts" in tk_viz_init_source) or (
        "from detm_app.ui.tk.runner.flow.viz import TkVizFlow, install_clipboard_shortcuts" in tk_viz_init_source
    )
    assert ("from detm_app.ui.tk.runner.flow.viz.flow import TkVizFlow" in tk_viz_init_source) or (
        "TkVizFlow" in tk_viz_init_source
    )

    tk_viz_flow_source = _read_text_first_existing(
        ROOT / "detm_app" / "ui" / "tk" / "runner" / "flow" / "viz" / "flow.py",
        ROOT / "detm_app" / "ui" / "tk" / "runner" / "flow" / "viz.py",
    )
    assert "from detm_app.transport.subscriber import TcpVizSubscriber" in tk_viz_flow_source
    assert "class TkVizFlow:" in tk_viz_flow_source

    tk_viz_clipboard_source = _read_text_first_existing(
        ROOT / "detm_app" / "ui" / "tk" / "runner" / "flow" / "viz" / "clipboard.py",
        ROOT / "detm_app" / "ui" / "tk" / "runner" / "flow" / "viz.py",
    )
    assert "install_clipboard_shortcuts" in tk_viz_clipboard_source

    tk_batch_flow_path = ROOT / "detm_app" / "ui" / "tk" / "runner" / "flow" / "batch.py"
    tk_batch_flow_source = tk_batch_flow_path.read_text(encoding="utf-8")
    assert "from detm_app.runner.batch_service import (" in tk_batch_flow_source
    assert "class TkBatchFlow:" in tk_batch_flow_source

    tk_actions_flow_path = ROOT / "detm_app" / "ui" / "tk" / "runner" / "flow" / "actions.py"
    tk_actions_flow_source = tk_actions_flow_path.read_text(encoding="utf-8")
    assert "class TkRuntimeActionFlow:" in tk_actions_flow_source

    tk_settings_init_source = _read_text_first_existing(
        ROOT / "detm_app" / "ui" / "tk" / "runner" / "flow" / "settings" / "__init__.py",
        ROOT / "detm_app" / "ui" / "tk" / "runner" / "flow" / "__init__.py",
    )
    assert ("from detm_app.ui.tk.runner.flow.settings.flow import TkSettingsFlow" in tk_settings_init_source) or (
        "TkSettingsFlow" in tk_settings_init_source
    )

    tk_settings_flow_source = _read_text_first_existing(
        ROOT / "detm_app" / "ui" / "tk" / "runner" / "flow" / "settings" / "flow.py",
        ROOT / "detm_app" / "ui" / "tk" / "runner" / "flow" / "settings.py",
    )
    assert "class TkSettingsFlow:" in tk_settings_flow_source

    tk_settings_config_source = _read_text_first_existing(
        ROOT / "detm_app" / "ui" / "tk" / "runner" / "flow" / "settings" / "runtime_config.py",
        ROOT / "detm_app" / "ui" / "tk" / "runner" / "flow" / "settings" / "config.py",
        ROOT / "detm_app" / "ui" / "tk" / "runner" / "flow" / "settings.py",
    )
    assert "from detm.runtime.config import DETMConfig" in tk_settings_config_source

    tk_settings_apply_source = _read_text_first_existing(
        ROOT / "detm_app" / "ui" / "tk" / "runner" / "flow" / "settings" / "apply.py",
        ROOT / "detm_app" / "ui" / "tk" / "runner" / "flow" / "settings.py",
    )
    assert ("def apply_runtime_settings(" in tk_settings_apply_source) or ("def apply(" in tk_settings_apply_source)

    tk_layout_flow_path = ROOT / "detm_app" / "ui" / "tk" / "runner" / "flow" / "layout.py"
    tk_layout_flow_source = tk_layout_flow_path.read_text(encoding="utf-8")
    assert "class TkLauncherLayout:" in tk_layout_flow_source
    assert "def build_launcher_layout(*, root: Any, tk: Any, ttk: Any) -> TkLauncherLayout:" in tk_layout_flow_source

    tk_window_flow_path = ROOT / "detm_app" / "ui" / "tk" / "runner" / "flow" / "window.py"
    tk_window_flow_source = tk_window_flow_path.read_text(encoding="utf-8")
    assert "def install_fullscreen_bindings(root: Any) -> None:" in tk_window_flow_source
    assert "def configure_root_grid(root: Any) -> None:" in tk_window_flow_source

    tk_controls_init_source = _read_text_first_existing(
        ROOT / "detm_app" / "ui" / "tk" / "runner" / "flow" / "controls" / "__init__.py",
        ROOT / "detm_app" / "ui" / "tk" / "runner" / "flow" / "__init__.py",
    )
    assert ("build_launcher_controls" in tk_controls_init_source) or ("TkControlVars" in tk_controls_init_source)

    tk_controls_model_source = _read_text_first_existing(
        ROOT / "detm_app" / "ui" / "tk" / "runner" / "flow" / "controls" / "model.py",
        ROOT / "detm_app" / "ui" / "tk" / "runner" / "flow" / "controls.py",
    )
    assert "class TkControlVars:" in tk_controls_model_source

    tk_controls_builder_source = _read_text_first_existing(
        ROOT / "detm_app" / "ui" / "tk" / "runner" / "flow" / "controls" / "builder.py",
        ROOT / "detm_app" / "ui" / "tk" / "runner" / "flow" / "controls.py",
    )
    assert "def build_launcher_controls(" in tk_controls_builder_source


def test_napari_interactive_controller_uses_shared_batch_service() -> None:
    init_path = ROOT / "detm_app" / "ui" / "napari" / "interactive" / "__init__.py"
    init_source = init_path.read_text(encoding="utf-8")
    assert "from detm_app.ui.napari.interactive.controller import _InteractiveDockController" in init_source

    controller_path = ROOT / "detm_app" / "ui" / "napari" / "interactive" / "controller.py"
    controller_source = controller_path.read_text(encoding="utf-8")
    assert "from detm_app.ui.napari.interactive.flow.actions import (" in controller_source
    assert "from detm_app.ui.napari.interactive.flow.batch import BatchRunState, on_batch_toggle as _on_batch_toggle_flow" in controller_source
    assert "from detm_app.ui.napari.interactive.flow.render import NapariRenderFlow" in controller_source
    assert "from detm_app.ui.napari.interactive.flow.controls import build_interactive_controls" in controller_source
    assert "from detm_app.ui.napari.interactive.flow.influence import (" in controller_source
    assert "from detm_app.ui.napari.interactive.flow.settings import (" in controller_source
    assert "from detm_app.ui.napari.interactive.flow.ui_wiring import (" in controller_source
    assert "from detm_app.ui.napari.interactive.flow.widget_io import (" in controller_source

    batch_init_path = ROOT / "detm_app" / "ui" / "napari" / "interactive" / "flow" / "batch" / "__init__.py"
    batch_init_source = batch_init_path.read_text(encoding="utf-8")
    assert "from detm_app.ui.napari.interactive.flow.batch.state import BatchRunState" in batch_init_source
    assert "from detm_app.ui.napari.interactive.flow.batch.toggle import on_batch_toggle" in batch_init_source

    batch_state_path = ROOT / "detm_app" / "ui" / "napari" / "interactive" / "flow" / "batch" / "state.py"
    batch_state_source = batch_state_path.read_text(encoding="utf-8")
    assert "from detm_app.runner.batch_service import BatchRunRequest, build_batch_start_message, start_batch_run" in batch_state_source

    batch_toggle_path = ROOT / "detm_app" / "ui" / "napari" / "interactive" / "flow" / "batch" / "toggle.py"
    batch_toggle_source = batch_toggle_path.read_text(encoding="utf-8")
    assert "def on_batch_toggle(controller: Any) -> None:" in batch_toggle_source

    render_flow_path = ROOT / "detm_app" / "ui" / "napari" / "interactive" / "flow" / "render.py"
    render_flow_source = render_flow_path.read_text(encoding="utf-8")
    assert "from detm_app.ui.napari.subscriber import state_to_layers" in render_flow_source

    controls_builder_path = ROOT / "detm_app" / "ui" / "napari" / "interactive" / "flow" / "controls.py"
    controls_builder_source = controls_builder_path.read_text(encoding="utf-8")
    assert "from detm_app.ui.napari.interactive.flow.controls_parts.influence import add_influence_page" in controls_builder_source

    controls_view_runtime_init_path = ROOT / "detm_app" / "ui" / "napari" / "interactive" / "flow" / "controls_parts" / "view_runtime" / "__init__.py"
    controls_view_runtime_init_source = controls_view_runtime_init_path.read_text(encoding="utf-8")
    assert "from detm_app.ui.napari.interactive.flow.controls_parts.view_runtime.runtime import add_runtime_page" in controls_view_runtime_init_source
    assert "from detm_app.ui.napari.interactive.flow.controls_parts.view_runtime.view import add_view_page" in controls_view_runtime_init_source

    controls_recording_batch_init_path = ROOT / "detm_app" / "ui" / "napari" / "interactive" / "flow" / "controls_parts" / "recording_batch" / "__init__.py"
    controls_recording_batch_init_source = controls_recording_batch_init_path.read_text(encoding="utf-8")
    assert "from detm_app.ui.napari.interactive.flow.controls_parts.recording_batch.batch import add_batch_page" in controls_recording_batch_init_source
    assert "from detm_app.ui.napari.interactive.flow.controls_parts.recording_batch.recording import add_recording_page" in controls_recording_batch_init_source

    controls_influence_init_path = ROOT / "detm_app" / "ui" / "napari" / "interactive" / "flow" / "controls_parts" / "influence" / "__init__.py"
    controls_influence_init_source = controls_influence_init_path.read_text(encoding="utf-8")
    assert "from detm_app.ui.napari.interactive.flow.controls_parts.influence.page import add_influence_page" in controls_influence_init_source

    controls_influence_page_path = ROOT / "detm_app" / "ui" / "napari" / "interactive" / "flow" / "controls_parts" / "influence" / "page.py"
    controls_influence_page_source = controls_influence_page_path.read_text(encoding="utf-8")
    assert "from detm.runtime.symbols import list_symbols" in controls_influence_page_source

    settings_flow_path = ROOT / "detm_app" / "ui" / "napari" / "interactive" / "flow" / "settings.py"
    settings_flow_source = settings_flow_path.read_text(encoding="utf-8")
    assert "from detm.runtime.config import DETMConfig" in settings_flow_source

    actions_init_path = ROOT / "detm_app" / "ui" / "napari" / "interactive" / "flow" / "actions" / "__init__.py"
    actions_init_source = actions_init_path.read_text(encoding="utf-8")
    assert "from detm_app.ui.napari.interactive.flow.actions.mode import mode_is_batch, on_mode_change" in actions_init_source
    assert "from detm_app.ui.napari.interactive.flow.actions.interaction import on_apply, on_reset, on_run_toggle, on_step" in actions_init_source

    actions_mode_path = ROOT / "detm_app" / "ui" / "napari" / "interactive" / "flow" / "actions" / "mode.py"
    actions_mode_source = actions_mode_path.read_text(encoding="utf-8")
    assert "def mode_is_batch(controller: Any) -> bool:" in actions_mode_source

    actions_interaction_path = ROOT / "detm_app" / "ui" / "napari" / "interactive" / "flow" / "actions" / "interaction.py"
    actions_interaction_source = actions_interaction_path.read_text(encoding="utf-8")
    assert "def on_run_toggle(controller: Any) -> None:" in actions_interaction_source

    influence_flow_path = ROOT / "detm_app" / "ui" / "napari" / "interactive" / "flow" / "influence.py"
    influence_flow_source = influence_flow_path.read_text(encoding="utf-8")
    assert "def sync_geometry_bounds(controller: Any) -> None:" in influence_flow_source

    ui_wiring_flow_path = ROOT / "detm_app" / "ui" / "napari" / "interactive" / "flow" / "ui_wiring.py"
    ui_wiring_flow_source = ui_wiring_flow_path.read_text(encoding="utf-8")
    assert "def build_buttons(controller: Any) -> None:" in ui_wiring_flow_source

    widget_io_flow_path = ROOT / "detm_app" / "ui" / "napari" / "interactive" / "flow" / "widget_io.py"
    widget_io_flow_source = widget_io_flow_path.read_text(encoding="utf-8")
    assert "def read_int(controller: Any, widget: Any, default: int) -> int:" in widget_io_flow_source
