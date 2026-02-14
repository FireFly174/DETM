from __future__ import annotations

import pytest

from detm.runtime.config import DETMConfig
from detm_app.runner.headless.request import (
    DEFAULT_FABRIC_RUN_OPTIONS,
    build_run_headless_request,
)


def test_build_run_headless_request_applies_fabric_defaults(tmp_path):
    req = build_run_headless_request(
        config=DETMConfig(width=8, height=8, backend="numpy", device="cpu"),
        seed=7,
        symbol_ids=["pulse"],
        steps=3,
        out_dir=tmp_path / "out",
        viz_transport=None,
    )
    assert req.fabric_kwargs == DEFAULT_FABRIC_RUN_OPTIONS
    assert req.symbol_ids == ("pulse",)


def test_build_run_headless_request_overrides_fabric_option(tmp_path):
    req = build_run_headless_request(
        config=DETMConfig(width=8, height=8, backend="numpy", device="cpu"),
        seed=7,
        symbol_ids=["pulse"],
        steps=3,
        out_dir=tmp_path / "out",
        viz_transport=None,
        fabric_kwargs={"fabric_handshake": True, "fabric_retry_attempts": 5},
    )
    assert bool(req.fabric_kwargs["fabric_handshake"]) is True
    assert int(req.fabric_kwargs["fabric_retry_attempts"]) == 5


def test_build_run_headless_request_rejects_unknown_fabric_option(tmp_path):
    with pytest.raises(TypeError):
        build_run_headless_request(
            config=DETMConfig(width=8, height=8, backend="numpy", device="cpu"),
            seed=7,
            symbol_ids=["pulse"],
            steps=3,
            out_dir=tmp_path / "out",
            viz_transport=None,
            fabric_kwargs={"fabric_unknown_option": True},
        )
