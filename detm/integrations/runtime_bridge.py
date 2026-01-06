"""Minimal in-process runtime bridge for DETM sessions.

This module intentionally contains **no module-level singleton state** so that
external runtimes can host multiple independent bridges in-process (or one
bridge per worker/process) without cross-talk.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Dict, Tuple

from detm.runtime import api
from detm.runtime.config import DETMConfig
from detm.runtime.influence import DETMInfluence
from detm.runtime.serialization import serialize_state
from detm.runtime.signature import DETMSignature
from detm.runtime.state import DETMState


@dataclass(frozen=True)
class SessionStepResult:
    signature: DETMSignature
    observables: api.Observables
    state_digest: list[float]


class DETMRuntimeBridge:
    def __init__(self) -> None:
        self._sessions: Dict[int, DETMState] = {}
        self._session_counter = itertools.count(1)

    def create_session(self, config: DETMConfig, seed: int) -> int:
        session_id = next(self._session_counter)
        self._sessions[session_id] = api.reset(config, seed)
        return session_id

    def session_step(self, session_id: int, influence: DETMInfluence | None, n_ticks: int) -> SessionStepResult:
        state = self._sessions[session_id]
        next_state, obs = api.step(state, influence, n_ticks, None)
        self._sessions[session_id] = next_state
        signature = api.digest(next_state)
        return SessionStepResult(signature=signature, observables=obs, state_digest=list(signature.vector))

    def session_get_state_blob(self, session_id: int) -> bytes:
        state = self._sessions[session_id]
        return serialize_state(state)

    def close_session(self, session_id: int) -> None:
        self._sessions.pop(session_id, None)

    def clear_sessions(self) -> None:
        self._sessions.clear()


__all__ = ["DETMRuntimeBridge", "SessionStepResult"]
