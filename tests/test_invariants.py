from core.fields import FieldState, Lattice, ScalarField
from core.invariants import collect_series, describe_field, radial_profile


def test_describe_field_reports_moments():
    lattice = Lattice(2, 2)
    field = ScalarField(lattice, [0.0, 1.0, 2.0, 3.0])

    stats = describe_field(field)

    assert stats.minimum == 0.0
    assert stats.maximum == 3.0
    assert stats.mean == 1.5
    assert stats.variance == 1.25


def test_collect_series_tracks_means_and_extrema():
    lattice = Lattice(2, 1)
    f0 = ScalarField(lattice, [0.0, 1.0])
    f1 = ScalarField(lattice, [1.0, 2.0])
    time = ScalarField.constant(lattice, value=0.0)

    series = collect_series(
        [
            FieldState(energy=f0, entropy=f0, internal_time=time),
            FieldState(energy=f1, entropy=f1, internal_time=time),
        ]
    )

    assert series["energy_mean"] == [0.5, 1.5]
    assert series["energy_min"] == [0.0, 1.0]
    assert series["energy_max"] == [1.0, 2.0]
    assert series["entropy_mean"] == [0.5, 1.5]
    assert series["internal_time_mean"] == [0.0, 0.0]


def test_radial_profile_matches_uniform_field():
    lattice = Lattice(3, 3)
    field = ScalarField(lattice, [1.0] * lattice.size)

    profile, radii = radial_profile(field, center=(0, 0))

    assert radii == [0.0, 1.0, 2.0]
    assert all(value == 1.0 for value in profile if value == value)  # filter NaNs if any
