from __future__ import annotations

from detm_app.runner.headless.executor import execute_headless_steps


class _DummySession:
    def __init__(self) -> None:
        self.calls: list[tuple[object | None, int]] = []

    def step(self, influence, steps: int) -> None:
        self.calls.append((influence, int(steps)))


def test_execute_headless_steps_per_symbol_mode(monkeypatch):
    monkeypatch.setattr("detm_app.runner.headless.executor.make_symbol", lambda sid: f"sym:{sid}")
    session = _DummySession()

    execute_headless_steps(
        session=session,
        symbol_ids=["pulse", "ring"],
        steps=3,
        steps_mode="per_symbol",
    )

    assert session.calls == [("sym:pulse", 3), ("sym:ring", 3)]


def test_execute_headless_steps_total_mode_with_empty_symbols():
    session = _DummySession()

    execute_headless_steps(
        session=session,
        symbol_ids=[],
        steps=5,
        steps_mode="total",
    )

    assert session.calls == [(None, 5)]


def test_execute_headless_steps_total_mode_cycles_symbols(monkeypatch):
    monkeypatch.setattr("detm_app.runner.headless.executor.make_symbol", lambda sid: f"sym:{sid}")
    session = _DummySession()

    execute_headless_steps(
        session=session,
        symbol_ids=["pulse", "ring"],
        steps=5,
        steps_mode="total",
    )

    assert session.calls == [
        ("sym:pulse", 1),
        ("sym:ring", 1),
        ("sym:pulse", 1),
        ("sym:ring", 1),
        ("sym:pulse", 1),
    ]
