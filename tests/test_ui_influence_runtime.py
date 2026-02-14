from __future__ import annotations

from detm.runtime.config import DETMConfig
from detm_app.config.ui_models import UiRunSettings
from detm_app.runtime.ui_runtime.influence import resolve_influence_for_settings


def _settings(**kwargs) -> UiRunSettings:
    cfg = DETMConfig(width=8, height=6, backend="numpy")
    base = UiRunSettings(config=cfg)
    for key, value in kwargs.items():
        setattr(base, key, value)
    return base


def test_resolve_influence_none_mode_keeps_window_state() -> None:
    settings = _settings(influence_mode="none")
    influence, key, remaining = resolve_influence_for_settings(
        settings,
        last_key=("symbol", "a", 0.1),
        remaining_steps=3,
    )
    assert influence is None
    assert key == ("symbol", "a", 0.1)
    assert remaining == 3


def test_resolve_influence_symbol_duration_window_counts_down() -> None:
    settings = _settings(
        influence_mode="symbol",
        symbol_id="a",
        amplitude=0.2,
        influence_duration_steps=2,
    )

    influence1, key1, remaining1 = resolve_influence_for_settings(
        settings,
        last_key=None,
        remaining_steps=0,
    )
    assert influence1 is not None
    assert key1 == ("symbol", "a", 0.2)
    assert remaining1 == 1

    influence2, key2, remaining2 = resolve_influence_for_settings(
        settings,
        last_key=key1,
        remaining_steps=remaining1,
    )
    assert influence2 is not None
    assert key2 == key1
    assert remaining2 == 0

    influence3, key3, remaining3 = resolve_influence_for_settings(
        settings,
        last_key=key2,
        remaining_steps=remaining2,
    )
    assert influence3 is None
    assert key3 == key2
    assert remaining3 == 0


def test_resolve_influence_unknown_mode_returns_none() -> None:
    settings = _settings(influence_mode="unknown-mode")
    influence, key, remaining = resolve_influence_for_settings(
        settings,
        last_key=("x",),
        remaining_steps=5,
    )
    assert influence is None
    assert key == ("x",)
    assert remaining == 5


def test_resolve_influence_joystick_patch_applies_modulo_coordinates() -> None:
    settings = _settings(
        influence_mode="joystick_patch",
        amplitude=0.3,
        patch_cx=17,
        patch_cy=13,
        patch_radius=4,
        influence_duration_steps=0,
    )
    influence, key, remaining = resolve_influence_for_settings(
        settings,
        last_key=None,
        remaining_steps=0,
    )
    assert influence is not None
    assert influence.symbol_id == "joystick_patch"
    assert influence.region == (1, 1, 4)
    assert key == ("joystick_patch", 0.3, 1, 1, 4)
    assert remaining == 0
