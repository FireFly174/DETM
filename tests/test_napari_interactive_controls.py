from __future__ import annotations

from pathlib import Path

import numpy as np

from detm.runtime import api
from detm.runtime.config import DETMConfig
from detm_app.ui.napari import interactive as napari_interactive
from detm_app.ui.napari.interactive.helpers import (
    build_projection_plane_options,
    format_projection_plane_label,
)
from detm_app.ui.napari.interactive.flow.render import NapariRenderFlow


def test_build_interactive_settings_applies_ui_overrides_and_forces_local_viz_off(monkeypatch):
    cfg = DETMConfig(width=10, height=6, backend="numpy")

    def _fake_load_merged_payload(*, preset, override_path):
        assert preset == "default"
        assert override_path == "config.example.py"
        return {
            "ui": {
                "seed": 7,
                "ticks_per_step": 11,
                "record_dir": "runs/out/ui_demo",
                "viz_enabled": True,
                "viz_transport": "tcp",
                "viz_port": 5588,
            }
        }

    monkeypatch.setattr(napari_interactive, "load_merged_payload", _fake_load_merged_payload)
    monkeypatch.setattr(napari_interactive, "build_runtime_config", lambda _payload: cfg)
    monkeypatch.setattr(napari_interactive, "build_ui_overrides", lambda ui_payload: dict(ui_payload))

    settings = napari_interactive._build_interactive_settings(
        preset="default",
        override_path="config.example.py",
    )

    assert isinstance(settings.config, DETMConfig)
    assert int(settings.config.width) == int(cfg.width)
    assert int(settings.config.height) == int(cfg.height)
    assert float(settings.config.level_policy.refinement_capacity_saturation_band) == 0.05
    assert int(settings.seed) == 7
    assert int(settings.ticks_per_step) == 11
    assert settings.record_dir == Path("runs/out/ui_demo")
    assert bool(settings.viz_enabled) is False
    assert str(settings.viz_transport) == "none"
    assert bool(settings.viz_connect) is False
    assert int(settings.viz_port) == 0


def test_build_quiver_vectors_returns_empty_for_constant_field():
    field = np.ones((6, 8), dtype=np.float32)
    vectors = napari_interactive._build_quiver_vectors(field, step=2, scale=0.8)
    assert isinstance(vectors, np.ndarray)
    assert vectors.shape == (0, 2, 2)


def test_build_quiver_vectors_emits_vectors_for_non_constant_field():
    y, x = np.mgrid[0:6, 0:8]
    field = (x + 2.0 * y).astype(np.float32)
    vectors = napari_interactive._build_quiver_vectors(field, step=2, scale=1.0)
    assert isinstance(vectors, np.ndarray)
    assert vectors.ndim == 3
    assert vectors.shape[1:] == (2, 2)
    assert vectors.shape[0] > 0


def test_parse_symbol_csv_returns_default_list_when_empty(monkeypatch):
    monkeypatch.setattr(napari_interactive, "list_symbols", lambda: ["pulse", "ring"])
    assert napari_interactive._parse_symbol_csv("") == ["pulse", "ring"]
    assert napari_interactive._parse_symbol_csv("   ") == ["pulse", "ring"]


def test_parse_symbol_csv_parses_and_validates_values(monkeypatch):
    monkeypatch.setattr(napari_interactive, "list_symbols", lambda: ["pulse", "ring", "drop"])
    parsed = napari_interactive._parse_symbol_csv("pulse, ring")
    assert parsed == ["pulse", "ring"]

    try:
        napari_interactive._parse_symbol_csv("pulse, unknown")
    except ValueError as exc:
        assert "Unknown symbol_id: unknown" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected ValueError for unknown symbol in batch csv")


def test_resolve_influence_policy_enforces_off_sustain_pulse():
    mode, dur = napari_interactive._resolve_influence_policy(
        policy="off",
        selected_mode="source_sink",
        duration_steps=25,
    )
    assert mode == "none"
    assert int(dur) == 0

    mode, dur = napari_interactive._resolve_influence_policy(
        policy="sustain",
        selected_mode="joystick_patch",
        duration_steps=10,
    )
    assert mode == "joystick_patch"
    assert int(dur) == 0

    mode, dur = napari_interactive._resolve_influence_policy(
        policy="pulse",
        selected_mode="symbol",
        duration_steps=0,
    )
    assert mode == "symbol"
    assert int(dur) == 1


def test_build_projection_plane_options_for_2d_and_nd_shapes():
    options_2d = build_projection_plane_options((8, 6))
    assert options_2d == [("native", None)]

    options_nd = build_projection_plane_options((2, 3, 8, 6))
    assert options_nd[0] == ("mean projection", None)
    assert ("plane[0,0]", (0, 0)) in options_nd
    assert ("plane[1,2]", (1, 2)) in options_nd
    assert len(options_nd) == 1 + (2 * 3)


def test_build_projection_plane_options_caps_large_nd_shapes() -> None:
    options_nd = build_projection_plane_options((9, 9, 8, 6))

    assert options_nd == [("mean projection", None)]


def test_format_projection_plane_label_formats_mean_and_explicit_plane():
    assert format_projection_plane_label(None) == "mean"
    assert format_projection_plane_label((1,)) == "plane[1]"
    assert format_projection_plane_label((1, 2)) == "plane[1,2]"


def test_napari_render_flow_status_shows_selected_plane_view():
    class _FakeLayer:
        def __init__(self, data):
            self.data = np.asarray(data, dtype=np.float32)
            self.interpolation2d = None
            self.colormap = None
            self.contrast_limits = None
            self.size = None
            self.face_color = None
            self.opacity = None
            self.symbol = None
            self.edge_color = None

    class _FakeLayers(dict):
        def remove(self, name):
            del self[name]

    class _FakeViewer:
        def __init__(self):
            self.layers = _FakeLayers()

        def add_image(self, image, name):
            layer = _FakeLayer(image)
            self.layers[name] = layer
            return layer

        def add_vectors(self, vectors, name, edge_color, edge_width):
            layer = _FakeLayer(vectors)
            layer.edge_color = edge_color
            self.layers[name] = layer
            return layer

        def add_points(self, points, name, size, face_color, opacity, symbol, edge_color=None, border_color=None):
            layer = _FakeLayer(points)
            layer.size = size
            layer.face_color = face_color
            layer.opacity = opacity
            layer.symbol = symbol
            layer.edge_color = edge_color if edge_color is not None else border_color
            self.layers[name] = layer
            return layer

    class _FakeStatus:
        def __init__(self):
            self.text = ""

        def setText(self, text):
            self.text = str(text)

    cfg = DETMConfig(shape=(2, 6, 5), backend="numpy", device="cpu")
    state = api.reset(cfg, seed=19)
    energy = np.zeros((2, 6, 5), dtype=np.float32)
    energy[0, :, :] = 1.0
    energy[1, :, :] = 4.0
    state.field_state.energy = energy
    state.field_state.entropy = energy + 1.0
    state.field_state.internal_time = energy + 2.0

    settings = type("_Settings", (), {"config": cfg})()
    runner = type(
        "_Runner",
        (),
        {
            "state": state,
            "last_observables": [0.1, 0.2, 0.3, 0.4],
            "runtime_backend_label": lambda self: "numpy/cpu",
            "learning_status_compact": lambda self, max_len=96: "",
        },
    )()
    viewer = _FakeViewer()
    status = _FakeStatus()

    meta = NapariRenderFlow(viewer=viewer).render(
        runner=runner,
        settings=settings,
        status_widget=status,
        field_name="energy",
        plane_index=(1,),
        cmap_name="heat",
        quiver_enabled=False,
        quiver_step=2,
        quiver_scale=0.8,
        autoscale=False,
        anchors_enabled=False,
        anchors_top_k=8,
        anchors_threshold=0.8,
        anchors_capture_ticks=4,
    )

    assert np.allclose(meta["energy_field"], np.full((6, 5), 4.0, dtype=np.float32))
    assert "view=plane[1]" in status.text
