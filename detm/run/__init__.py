"""Run/session helpers (headless + interactive).

This layer is intentionally thin:
- it orchestrates calls to `detm.runtime.api`
- it emits events to a simple pub/sub bus so that logging, viz streaming,
  statistics, and artifact writers can be attached without coupling.
"""

from __future__ import annotations

from detm.run.bus import EventBus
from detm.run.coarsening import InvariantCoarsener, InvariantStreamSpec
from detm.run.scheduler import TickRunner, TickScheduler
from detm.run.session import DetmSession

__all__ = [
    "DetmSession",
    "EventBus",
    "InvariantCoarsener",
    "InvariantStreamSpec",
    "TickRunner",
    "TickScheduler",
]
