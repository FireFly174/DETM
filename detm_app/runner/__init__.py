"""Runner layer for application orchestration."""

from detm_app.runner.headless import main as cli_main, run_headless
from detm_app.runner.shell import build_shell_contract, main as orchestrate_main

__all__ = ["build_shell_contract", "cli_main", "orchestrate_main", "run_headless"]
