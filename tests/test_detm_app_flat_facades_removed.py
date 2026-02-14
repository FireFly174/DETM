from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
REMOVED_FACADES = [
    "detm_app/app_settings.py",
    "detm_app/bus.py",
    "detm_app/cli.py",
    "detm_app/client.py",
    "detm_app/coarsening.py",
    "detm_app/config_hints.py",
    "detm_app/daemon.py",
    "detm_app/napari_lab.py",
    "detm_app/napari_subscriber.py",
    "detm_app/orchestrate.py",
    "detm_app/protocol.py",
    "detm_app/scheduler.py",
    "detm_app/session.py",
    "detm_app/subscriber.py",
    "detm_app/subscribers.py",
    "detm_app/tk_panel.py",
    "detm_app/tk_runner.py",
    "detm_app/tooltips.py",
]


def test_detm_app_flat_facade_files_removed():
    existing = [path for path in REMOVED_FACADES if (REPO_ROOT / path).exists()]
    assert existing == [], "Flat detm_app compatibility facades must stay removed:\n" + "\n".join(existing)

