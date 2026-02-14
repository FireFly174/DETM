from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from detm_app.ui.tk import panel_flow


class _Var:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value


class _Canvas:
    def __init__(self):
        self._next_id = 1
        self.rectangles: list[int] = []
        self.lines: list[int] = []
        self.deleted: list[object] = []
        self.itemconfig_calls: list[tuple[int, dict[str, object]]] = []
        self.coords_calls: list[tuple[int, float, float, float, float]] = []

    def create_rectangle(self, *_args, **_kwargs) -> int:
        rid = self._next_id
        self._next_id += 1
        self.rectangles.append(rid)
        return rid

    def create_line(self, *_args, **_kwargs) -> int:
        lid = self._next_id
        self._next_id += 1
        self.lines.append(lid)
        return lid

    def delete(self, item) -> None:
        self.deleted.append(item)

    def itemconfig(self, rid: int, **kwargs) -> None:
        self.itemconfig_calls.append((int(rid), dict(kwargs)))

    def coords(self, rid: int, x0: float, y0: float, x1: float, y1: float) -> None:
        self.coords_calls.append((int(rid), float(x0), float(y0), float(x1), float(y1)))

    def winfo_width(self) -> int:
        return 120

    def winfo_height(self) -> int:
        return 120

    def __getitem__(self, key: str) -> str:
        if key in {"width", "height"}:
            return "120"
        raise KeyError(key)


def _fake_panel() -> SimpleNamespace:
    return SimpleNamespace(
        canvas=_Canvas(),
        _rects=[],
        _arrows=[90, 91],
        _cell_w=20.0,
        _cell_h=20.0,
        _w=0,
        _h=0,
        _canvas_w=120,
        _canvas_h=120,
        _last_field=None,
        _off_x=0.0,
        _off_y=0.0,
        _tk=SimpleNamespace(LAST="last"),
        quiver_var=_Var(True),
        q_step_var=_Var(2),
        q_scale_var=_Var(0.8),
    )


def test_to_image_gray_constant_maps_to_midpoint() -> None:
    out = panel_flow.to_image_gray(np.ones((2, 2), dtype=float))
    assert out.dtype == np.uint8
    assert np.all(out == 128)


def test_field_from_state_selects_expected_tensor() -> None:
    state = SimpleNamespace(
        lattice=SimpleNamespace(height=2, width=3),
        field_state=SimpleNamespace(
            energy=np.arange(6, dtype=float),
            entropy=np.arange(10, 16, dtype=float),
            internal_time=np.arange(20, 26, dtype=float),
        ),
    )
    energy = panel_flow.field_from_state(state=state, mode="energy")
    entropy = panel_flow.field_from_state(state=state, mode="entropy")
    internal_time = panel_flow.field_from_state(state=state, mode="internal_time")

    assert energy.shape == (2, 3)
    assert np.allclose(energy, np.array([[0, 1, 2], [3, 4, 5]], dtype=float))
    assert np.allclose(entropy, np.array([[10, 11, 12], [13, 14, 15]], dtype=float))
    assert np.allclose(internal_time, np.array([[20, 21, 22], [23, 24, 25]], dtype=float))


def test_ensure_grid_creates_cells_and_layout_coords() -> None:
    panel = _fake_panel()
    panel_flow.ensure_grid(panel, h=2, w=3)

    assert panel._h == 2
    assert panel._w == 3
    assert len(panel._rects) == 2
    assert len(panel._rects[0]) == 3
    assert len(panel.canvas.coords_calls) == 6


def test_draw_quiver_clears_old_and_adds_new_arrows() -> None:
    panel = _fake_panel()
    panel._h = 4
    panel._w = 4
    panel._rects = [[1, 2, 3, 4]] * 4
    arr = np.array(
        [
            [0.0, 1.0, 2.0, 3.0],
            [1.0, 2.0, 3.0, 4.0],
            [2.0, 3.0, 4.0, 5.0],
            [3.0, 4.0, 5.0, 6.0],
        ],
        dtype=float,
    )
    panel_flow.draw_quiver(panel, arr)

    assert 90 in panel.canvas.deleted and 91 in panel.canvas.deleted
    assert len(panel._arrows) > 0


def test_paint_field_updates_each_cell_fill() -> None:
    panel = _fake_panel()
    panel._h = 2
    panel._w = 2
    panel._rects = [[11, 12], [21, 22]]
    field = np.array([[0.0, 1.0], [2.0, 3.0]], dtype=float)

    panel_flow.paint_field(panel, field=field, cmap="gray")
    assert len(panel.canvas.itemconfig_calls) == 4
    first = panel.canvas.itemconfig_calls[0][1].get("fill")
    assert isinstance(first, str) and first.startswith("#")
