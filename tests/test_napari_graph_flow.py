from __future__ import annotations

from detm_app.ui.napari.interactive.flow.graph import (
    _build_histogram_bins,
    available_graph_series_ids,
    extract_graph_series_values,
    parse_graph_series_csv,
)


def test_parse_graph_series_csv_filters_unknown_and_deduplicates() -> None:
    out = parse_graph_series_csv("event_count,operator_reuse,unknown,operator_reuse")
    assert out == ["event_count", "operator_reuse"]


def test_parse_graph_series_csv_falls_back_to_defaults() -> None:
    out = parse_graph_series_csv("unknown_a,unknown_b")
    assert len(out) >= 1
    assert "event_count" in out


def test_extract_graph_series_values_reads_snapshot_paths() -> None:
    snapshot = {
        "event_count": 9,
        "signature_summary": {
            "energy_mean": 0.52,
            "energy_var": 0.01,
            "entropy_mean": 0.12,
            "internal_time_mean": 0.77,
            "center_of_mass_x": 11.5,
            "center_of_mass_y": 8.25,
        },
        "field_summaries": {
            "energy": {
                "minimum": 0.1,
                "maximum": 0.9,
                "mean": 0.52,
                "variance": 0.01,
                "std": 0.1,
                "range": 0.8,
            }
        },
        "influence": {
            "last_amplitude": 0.3,
            "last_affected_fraction": 0.12,
        },
        "legacy_metrics": {
            "A_t": 0.44,
            "P_t": 0.21,
            "T_t": 18.0,
            "n_peaks": 3.0,
            "freeze_mean": 0.02,
            "freeze_min": 0.01,
            "locked_frac": 0.75,
            "a3_plv_mean": 0.8,
            "a3_var_mean": 0.2,
        },
        "watchpoints": {
            "refinement_count": 3,
            "influence_count": 2,
            "attractor_count": 1,
            "operator_decision_count": 4,
            "operator_reuse_rate": 0.5,
            "runtime_adaptive_window_active": True,
            "anti_goodhart_flag": False,
            "cpu_time_ms": 12.5,
            "step_ops_estimate": 144.0,
            "oscillation_score": 0.75,
        },
        "portability_panel": {
            "operator_reuse": 0.5,
            "transferability": 0.25,
            "hold_rate": 0.8,
            "torsion_health": 0.9,
        },
    }
    values = extract_graph_series_values(
        snapshot=snapshot,
        series_ids=[
            "event_count",
            "refinement_count",
            "decision_count",
            "operator_reuse",
            "transferability",
            "hold_rate",
            "torsion_health",
            "runtime_active",
            "anti_goodhart_flag",
            "cpu_time_ms",
            "oscillation_score",
            "influence_count",
            "attractor_count",
            "operator_reuse_rate",
            "step_ops_estimate",
            "energy_mean",
            "energy_var",
            "energy_min",
            "energy_max",
            "energy_std",
            "energy_range",
            "entropy_mean",
            "tau_mean",
            "center_x",
            "center_y",
            "influence_last_amplitude",
            "influence_last_affected_fraction",
            "A_t",
            "P_t",
            "T_t",
            "n_peaks",
            "freeze_mean",
            "freeze_min",
            "locked_frac",
            "a3_plv_mean",
            "a3_var_mean",
        ],
    )
    assert float(values["event_count"]) == 9.0
    assert float(values["refinement_count"]) == 3.0
    assert float(values["decision_count"]) == 4.0
    assert float(values["operator_reuse"]) == 0.5
    assert float(values["transferability"]) == 0.25
    assert float(values["hold_rate"]) == 0.8
    assert float(values["torsion_health"]) == 0.9
    assert float(values["runtime_active"]) == 1.0
    assert float(values["anti_goodhart_flag"]) == 0.0
    assert float(values["cpu_time_ms"]) == 12.5
    assert float(values["oscillation_score"]) == 0.75
    assert float(values["influence_count"]) == 2.0
    assert float(values["attractor_count"]) == 1.0
    assert float(values["operator_reuse_rate"]) == 0.5
    assert float(values["step_ops_estimate"]) == 144.0
    assert float(values["energy_mean"]) == 0.52
    assert float(values["energy_var"]) == 0.01
    assert float(values["energy_min"]) == 0.1
    assert float(values["energy_max"]) == 0.9
    assert float(values["energy_std"]) == 0.1
    assert float(values["energy_range"]) == 0.8
    assert float(values["entropy_mean"]) == 0.12
    assert float(values["tau_mean"]) == 0.77
    assert float(values["center_x"]) == 11.5
    assert float(values["center_y"]) == 8.25
    assert float(values["influence_last_amplitude"]) == 0.3
    assert float(values["influence_last_affected_fraction"]) == 0.12
    assert float(values["A_t"]) == 0.44
    assert float(values["P_t"]) == 0.21
    assert float(values["T_t"]) == 18.0
    assert float(values["n_peaks"]) == 3.0
    assert float(values["freeze_mean"]) == 0.02
    assert float(values["freeze_min"]) == 0.01
    assert float(values["locked_frac"]) == 0.75
    assert float(values["a3_plv_mean"]) == 0.8
    assert float(values["a3_var_mean"]) == 0.2


def test_available_graph_series_ids_contains_core_defaults() -> None:
    ids = set(available_graph_series_ids())
    assert "event_count" in ids
    assert "operator_reuse" in ids
    assert "transferability" in ids


def test_build_histogram_bins_for_tiny_span_returns_edges() -> None:
    import numpy as np

    values = np.asarray([1.0, 1.0 + 1e-16], dtype=np.float64)
    bins = _build_histogram_bins(values, requested_bins=48)
    assert isinstance(bins, np.ndarray)
    assert bins.shape[0] == 49
    assert bool(np.all(np.diff(bins) > 0.0))
