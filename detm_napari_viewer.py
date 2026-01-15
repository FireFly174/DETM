"""
Minimal napari viewer for DETMState.

What it does:
- Accepts a DETMState instance (or loads one from msgpack if you wire it in).
- Tries to extract 2D numpy arrays from state.field_state.lattice (energy/entropy/time/etc.)
- Displays them as separate napari image layers.
- Adds a tiny Qt dock widget with a Refresh button (so you can redraw after you step the sim).

Install (example):
  pip install napari[all] pyside6 numpy

Run:
  python detm_napari_viewer.py
"""

from __future__ import annotations

from dataclasses import is_dataclass
from typing import Any, Dict, Optional, Tuple

import numpy as np
import napari
from qtpy import QtWidgets


# ----------------------------
# Helpers: robust array pulling
# ----------------------------

def _as_2d_float(arr: Any) -> Optional[np.ndarray]:
    """Convert candidate to a 2D float32 numpy array if possible."""
    if arr is None:
        return None
    if isinstance(arr, np.ndarray):
        if arr.ndim == 2:
            return arr.astype(np.float32, copy=False)
        # common: (H,W,1) or (1,H,W)
        if arr.ndim == 3:
            if arr.shape[-1] == 1:
                return arr[..., 0].astype(np.float32, copy=False)
            if arr.shape[0] == 1:
                return arr[0].astype(np.float32, copy=False)
    # torch tensor support (optional)
    try:
        import torch  # type: ignore
        if isinstance(arr, torch.Tensor):
            arr = arr.detach().cpu().numpy()
            return _as_2d_float(arr)
    except Exception:
        pass
    return None


def _get_attr(obj: Any, *names: str) -> Any:
    """Try multiple attribute names; return first found or None."""
    for n in names:
        if hasattr(obj, n):
            return getattr(obj, n)
    return None


def _guess_fields_from_lattice(lattice: Any) -> Dict[str, np.ndarray]:
    """
    Best-effort extraction of 2D fields from your Lattice object.

    Update the CANDIDATES mapping once you know the exact field names,
    e.g. lattice.E, lattice.S, lattice.tau, etc.
    """
    # Likely field name candidates (edit these to match your actual Lattice API)
    CANDIDATES: Dict[str, Tuple[str, ...]] = {
        "E": ("E", "energy", "energy_field", "field_E", "e"),
        "S": ("S", "entropy", "entropy_field", "field_S", "s"),
        "tau": ("tau", "time", "internal_time", "t", "field_tau"),
        "Jx": ("Jx", "jx", "flow_x", "flux_x"),
        "Jy": ("Jy", "jy", "flow_y", "flux_y"),
        "mask": ("mask", "active_mask", "boundary_mask"),
    }

    out: Dict[str, np.ndarray] = {}

    # 1) Try known attributes by name
    for label, attrs in CANDIDATES.items():
        cand = _get_attr(lattice, *attrs)
        arr2d = _as_2d_float(cand)
        if arr2d is not None:
            out[label] = arr2d

    # 2) If lattice itself is dict-like
    if not out and isinstance(lattice, dict):
        for k, v in lattice.items():
            arr2d = _as_2d_float(v)
            if arr2d is not None:
                out[str(k)] = arr2d

    # 3) If lattice is dataclass-like, scan fields
    if not out and is_dataclass(lattice):
        for field_name in getattr(lattice, "__dataclass_fields__", {}).keys():
            v = getattr(lattice, field_name, None)
            arr2d = _as_2d_float(v)
            if arr2d is not None:
                out[field_name] = arr2d

    return out


def detm_state_to_layers(state: Any) -> Dict[str, np.ndarray]:
    """
    Convert DETMState to a dict of {layer_name: 2D ndarray}.
    Assumes state.field_state.lattice exists (per your class).
    """
    lattice = getattr(getattr(state, "field_state", None), "lattice", None)
    if lattice is None:
        raise ValueError("state.field_state.lattice is None or missing")
    layers = _guess_fields_from_lattice(lattice)
    if not layers:
        # Fallback: if lattice itself is 2D array
        arr2d = _as_2d_float(lattice)
        if arr2d is not None:
            layers = {"lattice": arr2d}
    if not layers:
        raise ValueError(
            "Could not extract any 2D fields from lattice. "
            "Edit CANDIDATES in _guess_fields_from_lattice() to match your Lattice attributes."
        )
    return layers


# ----------------------------
# Napari UI
# ----------------------------

class DetmControlDock(QtWidgets.QWidget):
    def __init__(self, viewer: napari.Viewer, state_ref: Dict[str, Any]):
        super().__init__()
        self.viewer = viewer
        self.state_ref = state_ref  # expects {"state": DETMState}

        layout = QtWidgets.QVBoxLayout(self)

        self.lbl = QtWidgets.QLabel("DETM Viewer Controls")
        self.lbl.setStyleSheet("font-weight: 600;")
        layout.addWidget(self.lbl)

        self.info = QtWidgets.QLabel("")
        self.info.setWordWrap(True)
        layout.addWidget(self.info)

        self.btn_refresh = QtWidgets.QPushButton("Refresh layers from state")
        self.btn_refresh.clicked.connect(self.refresh)
        layout.addWidget(self.btn_refresh)

        self.btn_autoscale = QtWidgets.QPushButton("Autoscale contrast")
        self.btn_autoscale.clicked.connect(self.autoscale)
        layout.addWidget(self.btn_autoscale)

        layout.addStretch(1)

        self.refresh()

    def refresh(self):
        state = self.state_ref["state"]
        layers = detm_state_to_layers(state)

        # Update/add layers
        for name, img in layers.items():
            if name in self.viewer.layers:
                layer = self.viewer.layers[name]
                layer.data = img
            else:
                self.viewer.add_image(img, name=name)

        # Remove stale layers that are not present anymore (optional)
        keep = set(layers.keys())
        for layer in list(self.viewer.layers):
            if layer.name not in keep:
                # comment out if you prefer to keep old layers
                pass

        step = getattr(state, "step_count", None)
        dyn = getattr(state, "dynamics", None)
        self.info.setText(f"step_count: {step}\nfields: {', '.join(sorted(layers.keys()))}\ndynamics: {dyn}")

    def autoscale(self):
        for layer in self.viewer.layers:
            if hasattr(layer, "contrast_limits") and isinstance(layer.data, np.ndarray):
                vmin = float(np.nanmin(layer.data))
                vmax = float(np.nanmax(layer.data))
                if np.isfinite(vmin) and np.isfinite(vmax) and vmin != vmax:
                    layer.contrast_limits = (vmin, vmax)


def show_detm_in_napari(state: Any) -> napari.Viewer:
    viewer = napari.Viewer(title="DETM napari viewer")

    # initial layers
    layers = detm_state_to_layers(state)
    for name, img in layers.items():
        viewer.add_image(img, name=name)

    # dock
    state_ref = {"state": state}  # mutable reference so you can swap state_ref["state"] externally
    dock = DetmControlDock(viewer, state_ref)
    viewer.window.add_dock_widget(dock, name="DETM", area="right")

    return viewer


# ----------------------------
# Demo / entrypoint
# ----------------------------

def _make_dummy_state_like() -> Any:
    """
    Demo-only fallback when you just want to test napari wiring.
    Replace this with your real DETMState instance creation/loading.
    """
    class DummyLattice:
        def __init__(self):
            x = np.linspace(-3, 3, 128)
            X, Y = np.meshgrid(x, x)
            self.E = np.exp(-(X**2 + Y**2))
            self.S = np.abs(np.sin(X) * np.cos(Y)) * 0.1
            self.tau = (np.sin(X * 2) + 1) * 0.5

    class DummyFieldState:
        def __init__(self):
            self.lattice = DummyLattice()

    class DummyState:
        def __init__(self):
            self.field_state = DummyFieldState()
            self.step_count = 0
            self.dynamics = {"demo": True}

    return DummyState()


if __name__ == "__main__":
    # Replace with: state = DETMState.load(...) or whatever you use.
    state = _make_dummy_state_like()

    show_detm_in_napari(state)
    napari.run()
