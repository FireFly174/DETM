"""Contracts for delivery tracking runtime."""

from __future__ import annotations

from typing import Callable

from detm.runtime.fabric import FabricEnvelope

RepublishFn = Callable[[FabricEnvelope], bool]

__all__ = ["RepublishFn"]


