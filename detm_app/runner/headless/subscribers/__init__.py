"""Subscriber wiring API for headless runtime runs."""

from detm_app.runner.headless.subscribers.flow import attach_headless_subscribers

__all__ = ["attach_headless_subscribers"]
