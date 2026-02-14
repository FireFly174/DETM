"""Fabric parser argument orchestration for headless CLI."""

from __future__ import annotations

import argparse

from detm_app.runner.headless.parser_fabric.coordination import add_coordination_arguments
from detm_app.runner.headless.parser_fabric.delivery import add_delivery_arguments
from detm_app.runner.headless.parser_fabric.handshake import add_handshake_arguments
from detm_app.runner.headless.parser_fabric.transport import add_transport_arguments


def add_fabric_arguments(ap: argparse.ArgumentParser) -> None:
    add_handshake_arguments(ap)
    add_transport_arguments(ap)
    add_coordination_arguments(ap)
    add_delivery_arguments(ap)


__all__ = ["add_fabric_arguments"]
