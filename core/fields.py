"""Core lattice and scalar field primitives for DETM.

The module defines a minimal, deterministic toolkit for representing
regular lattices and scalar fields that live on top of them.  The classes are
purposefully lightweight so they can be reused in simulation code as well as
experiment and visualisation pipelines.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterator, List, Optional, Tuple

Coordinate = Tuple[int, int]
BoundaryCondition = str


@dataclass(frozen=True)
class Lattice:
    """Two-dimensional regular lattice descriptor.

    Parameters
    ----------
    width, height:
        Dimensions of the lattice in cells.
    boundary:
        Either ``"periodic"`` (default) for toroidal wrapping or ``"open"`` to
        drop neighbours that would fall outside the lattice.
    """

    width: int
    height: int
    boundary: BoundaryCondition = "periodic"

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Lattice dimensions must be positive")
        if self.boundary not in {"periodic", "open"}:
            raise ValueError(f"Unsupported boundary condition: {self.boundary}")

    @property
    def size(self) -> int:
        return self.width * self.height

    def in_bounds(self, coord: Coordinate) -> bool:
        x, y = coord
        return 0 <= x < self.width and 0 <= y < self.height

    def normalize(self, coord: Coordinate) -> Optional[Coordinate]:
        """Return a valid coordinate or ``None`` if outside for open borders."""

        x, y = coord
        if self.boundary == "periodic":
            return x % self.width, y % self.height
        if self.in_bounds(coord):
            return coord
        return None

    def neighbors(self, coord: Coordinate) -> List[Coordinate]:
        """Return neighbour coordinates in a deterministic order.

        The order is left, right, up, down so that the evolution logic remains
        stable across runs.
        """

        x, y = coord
        raw_neighbours = [(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)]

        resolved: List[Coordinate] = []
        for nx, ny in raw_neighbours:
            normalized = self.normalize((nx, ny))
            if normalized is not None:
                resolved.append(normalized)
        return resolved

    def positions(self) -> Iterator[Coordinate]:
        """Iterate over all coordinates in row-major order."""

        for y in range(self.height):
            for x in range(self.width):
                yield x, y


@dataclass
class ScalarField:
    """Scalar values attached to the cells of a :class:`Lattice`."""

    lattice: Lattice
    values: List[float]

    def __post_init__(self) -> None:
        if len(self.values) != self.lattice.size:
            raise ValueError(
                "Field value count "
                f"{len(self.values)} does not match lattice size {self.lattice.size}"
            )

    # ------------------------------------------------------------------
    # Constructors and utilities
    # ------------------------------------------------------------------
    @classmethod
    def constant(cls, lattice: Lattice, value: float = 0.0) -> "ScalarField":
        return cls(lattice=lattice, values=[float(value)] * lattice.size)

    def copy(self) -> "ScalarField":
        return ScalarField(self.lattice, self.values.copy())

    def index(self, coord: Coordinate) -> int:
        x, y = coord
        if not self.lattice.in_bounds((x, y)):
            raise IndexError(f"Coordinate {(x, y)} outside lattice bounds")
        return y * self.lattice.width + x

    def get(self, coord: Coordinate) -> float:
        return self.values[self.index(coord)]

    def set(self, coord: Coordinate, value: float) -> None:
        self.values[self.index(coord)] = float(value)

    def items(self) -> Iterator[Tuple[Coordinate, float]]:
        for coord in self.lattice.positions():
            yield coord, self.get(coord)

    def map_values(self, fn: Callable[[float], float]) -> "ScalarField":
        return ScalarField(self.lattice, [float(fn(v)) for v in self.values])

    def combine(self, other: "ScalarField", fn: Callable[[float, float], float]) -> "ScalarField":
        self._ensure_same_lattice(other)
        combined = [float(fn(a, b)) for a, b in zip(self.values, other.values)]
        return ScalarField(self.lattice, combined)

    def apply_in_place(self, fn: Callable[[float], float]) -> None:
        for i, value in enumerate(self.values):
            self.values[i] = float(fn(value))

    def clamp(self, min_value: float, max_value: float) -> "ScalarField":
        return ScalarField(
            self.lattice,
            [min(max(value, min_value), max_value) for value in self.values],
        )

    def to_matrix(self) -> List[List[float]]:
        rows: List[List[float]] = []
        for y in range(self.lattice.height):
            start = y * self.lattice.width
            end = start + self.lattice.width
            rows.append(self.values[start:end])
        return rows

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _ensure_same_lattice(self, other: "ScalarField") -> None:
        if self.lattice != other.lattice:
            raise ValueError("Fields must share the same lattice")


@dataclass
class FieldState:
    """Bundle of core fields that evolve together during simulation."""

    energy: ScalarField
    entropy: ScalarField
    internal_time: ScalarField

    def copy(self) -> "FieldState":
        return FieldState(
            energy=self.energy.copy(),
            entropy=self.entropy.copy(),
            internal_time=self.internal_time.copy(),
        )

    def ensure_alignment(self) -> None:
        self.energy._ensure_same_lattice(self.entropy)
        self.energy._ensure_same_lattice(self.internal_time)

    @property
    def lattice(self) -> Lattice:
        return self.energy.lattice


__all__ = ["BoundaryCondition", "Coordinate", "FieldState", "Lattice", "ScalarField"]
