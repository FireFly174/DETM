from __future__ import annotations

import json
import subprocess
import sys
import warnings

from detm.run._compat import (
    DETM_RUN_MIGRATION_DOC,
    DETM_RUN_REMOVAL_TARGET_DATE,
    DETM_RUN_REMOVAL_TARGET_VERSION,
)


def test_detm_run_facade_reexports_symbols_and_warns():
    import detm.run as run_facade
    from detm_app.bus import EventBus as AppEventBus

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        exported = run_facade.EventBus

    assert exported is AppEventBus
    assert any("deprecated" in str(item.message).lower() for item in caught)
    assert any(DETM_RUN_REMOVAL_TARGET_VERSION in str(item.message) for item in caught)
    assert any(DETM_RUN_REMOVAL_TARGET_DATE in str(item.message) for item in caught)
    assert any(DETM_RUN_MIGRATION_DOC in str(item.message) for item in caught)


def test_detm_run_facade_import_is_lazy_until_symbol_access():
    script = """
import json
import sys
import warnings

import detm.run as run_facade
after_import = sorted(name for name in sys.modules if name == 'detm_app' or name.startswith('detm_app.'))

with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter('always', DeprecationWarning)
    _ = run_facade.DetmSession

after_access = sorted(name for name in sys.modules if name == 'detm_app' or name.startswith('detm_app.'))

print(json.dumps({
    'after_import': after_import,
    'after_access': after_access,
    'warnings': [str(item.message) for item in caught],
}))
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(str(completed.stdout).strip())

    assert payload["after_import"] == []
    assert len(payload["after_access"]) > 0
    assert any("deprecated" in str(message).lower() for message in payload["warnings"])
    assert any(DETM_RUN_REMOVAL_TARGET_VERSION in str(message) for message in payload["warnings"])
