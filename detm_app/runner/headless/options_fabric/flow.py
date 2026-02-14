"""Fabric option resolution orchestration for headless CLI."""

from __future__ import annotations

from typing import Any

from detm_app.runner.headless.options_fabric.coordination import resolve_coordination_fabric_options
from detm_app.runner.headless.options_fabric.delivery import resolve_delivery_fabric_options
from detm_app.runner.headless.options_fabric.handshake import resolve_handshake_fabric_options
from detm_app.runner.headless.options_fabric.transport import resolve_transport_fabric_options


def resolve_headless_fabric_options(*, args: Any, runner_defaults: dict[str, Any]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    values.update(resolve_handshake_fabric_options(args=args, runner_defaults=runner_defaults))
    values.update(resolve_transport_fabric_options(args=args, runner_defaults=runner_defaults))
    values.update(resolve_coordination_fabric_options(args=args, runner_defaults=runner_defaults))
    values.update(resolve_delivery_fabric_options(args=args, runner_defaults=runner_defaults))
    return values


__all__ = ["resolve_headless_fabric_options"]
