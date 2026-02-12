from __future__ import annotations

import warnings


def test_detm_ui_config_hints_facade_warns_and_delegates(monkeypatch):
    import detm.ui.config_hints as legacy_hints

    monkeypatch.setattr(legacy_hints, "_app_load_tooltips", lambda: {"runner.seed": "seed"})

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        payload = legacy_hints.load_tooltips_from_config_default()

    assert payload == {"runner.seed": "seed"}
    assert any("deprecated" in str(item.message).lower() for item in caught)


def test_detm_ui_tooltips_facade_warns_and_delegates(monkeypatch):
    import detm.ui.tooltips as legacy_tooltips
    from detm_app.tooltips import Tooltip as app_tooltip

    called = {"ok": False}

    def _fake_attach(_widget: object, _text: str) -> None:
        called["ok"] = True

    monkeypatch.setattr(legacy_tooltips, "_app_attach_tooltip", _fake_attach)

    assert legacy_tooltips.Tooltip is app_tooltip

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        legacy_tooltips.attach_tooltip(object(), "hint")

    assert called["ok"] is True
    assert any("deprecated" in str(item.message).lower() for item in caught)
