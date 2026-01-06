"""DETM core primitives (lattice, fields, entropy dynamics)."""

from detm.core.entropy import DynamicsParameters, compute_entropy, evolve, step
from detm.core.fields import FieldState, Lattice, ScalarField
from detm.core.invariants import collect_series, describe_field, describe_state, radial_profile

__all__ = [
    "DynamicsParameters",
    "FieldState",
    "Lattice",
    "ScalarField",
    "collect_series",
    "compute_entropy",
    "describe_field",
    "describe_state",
    "evolve",
    "radial_profile",
    "step",
]

