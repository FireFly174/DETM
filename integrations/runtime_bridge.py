"""Minimal in-process runtime bridge for DETM sessions."""

from __future__ import annotations

import itertools
from typing import Dict

from runtime import api
from runtime.config import DETMConfig
from runtime.influence import DETMInfluence
from runtime.serialization import serialize_state
from runtime.state import DETMState

_sessions: Dict[int, DETMState] = {}
_session_counter = itertools.count(1)


def create_session(config: DETMConfig, seed: int) -> int:
    session_id = next(_session_counter)
    _sessions[session_id] = api.reset(config, seed)
    return session_id


def session_step(session_id: int, influence: DETMInfluence, n_ticks: int):
    state = _sessions[session_id]
    next_state, obs = api.step(state, influence, n_ticks, None)
    _sessions[session_id] = next_state
    signature = api.digest(next_state)
    return signature, obs, signature.vector


def session_get_state_blob(session_id: int) -> bytes:
    state = _sessions[session_id]
    return serialize_state(state)


def clear_sessions() -> None:
    _sessions.clear()


__all__ = ["clear_sessions", "create_session", "session_get_state_blob", "session_step"]
