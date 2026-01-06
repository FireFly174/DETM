"""Minimal pub/sub event bus inspired by the legacy bundle patterns."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, DefaultDict, Dict, List, Optional


EventHandler = Callable[..., None]


@dataclass
class Event:
    name: str
    payload: Dict[str, Any]


class EventBus:
    """Synchronous event bus.

    The bus is intentionally simple: handlers are called in subscription order.
    Handlers should be fast and non-blocking; heavy work is expected to be done
    in separate processes/threads at the orchestrator layer (ACGS), or by
    throttling/dropping updates.
    """

    def __init__(self) -> None:
        self._listeners: Dict[str, List[EventHandler]] = {}
        self._once: Dict[str, List[EventHandler]] = {}

    def add_event_listener(self, event: str, listener: EventHandler) -> None:
        self._listeners.setdefault(str(event), []).append(listener)
        return None

    def add_event_listener_unsub(self, event: str, listener: EventHandler) -> Callable[[], None]:
        """Add listener and return an unsubscribe callable."""

        name = str(event)
        listeners = self._listeners.setdefault(name, [])
        listeners.append(listener)

        def unsubscribe() -> None:
            current = self._listeners.get(name, [])
            try:
                current.remove(listener)
            except ValueError:
                return

        return unsubscribe

    def remove_event_listener(self, event: str) -> None:
        self._listeners.pop(str(event), None)
        self._once.pop(str(event), None)

    def remove_all_listeners(self) -> None:
        self._listeners.clear()
        self._once.clear()

    def publish(self, event: str, **payload: Any) -> None:
        name = str(event)
        listeners = list(self._listeners.get(name, ()))
        for listener in listeners:
            listener(**payload)

        once = self._once.pop(name, [])
        for listener in once:
            listener(**payload)

    def publish_once(self, event: str, listener: EventHandler) -> None:
        self._once.setdefault(str(event), []).append(listener)

    def emit(self, event: Event) -> None:
        self.publish(event.name, **event.payload)


__all__ = ["Event", "EventBus", "EventHandler"]
