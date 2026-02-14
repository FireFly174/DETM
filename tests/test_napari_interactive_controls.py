from __future__ import annotations

from pathlib import Path

import numpy as np

from detm.runtime.config import DETMConfig
from detm_app.ui.napari import interactive as napari_interactive


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

    assert settings.config is cfg
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
