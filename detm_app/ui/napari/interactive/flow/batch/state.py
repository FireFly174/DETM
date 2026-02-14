#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Batch runtime state holder for napari interactive controller."""

from __future__ import annotations

from typing import Any, Callable

from detm_app.runner.batch_service import BatchRunRequest, build_batch_start_message, start_batch_run


class BatchRunState:
    def __init__(
        self,
        *,
        poll_timer: Any,
        log: Callable[[str], None],
        clear_log: Callable[[], None],
        set_button_text: Callable[[str], None],
    ) -> None:
        self._poll_timer = poll_timer
        self._log = log
        self._clear_log = clear_log
        self._set_button_text = set_button_text
        self._handle: Any | None = None

    def is_running(self) -> bool:
        return self._handle is not None

    def start(self, request: BatchRunRequest) -> None:
        self._set_button_text("Stop batch")
        self._clear_log()
        self._log(build_batch_start_message(request))
        self._handle = start_batch_run(request)
        self._poll_timer.start()

    def cancel(self) -> None:
        if self._handle is None:
            return
        self._handle.cancel()
        self._log("[cancel] requested")

    def drain(self) -> None:
        if self._handle is None:
            return
        items, done = self._handle.drain_messages()
        for item in items:
            self._log(str(item))
        if done:
            self._finish()

    def close(self) -> None:
        self._poll_timer.stop()
        if self._handle is not None:
            self._handle.cancel()
        self._finish()

    def _finish(self) -> None:
        self._poll_timer.stop()
        self._handle = None
        self._set_button_text("Run batch")


__all__ = ["BatchRunState"]
