# Changelog

All notable changes to this project are documented in this file.

## [0.2.0] - 2026-02-14

- Runtime/app restructuring finalized across `detm` and `detm_app`.
- Monolithic runtime modules split into cohesive subpackages:
  - `detm/runtime/serialization/*`
  - `detm/runtime/refinement/{apply.py,pipeline/*}`
  - `detm/runtime/level_policy/*`
  - `detm_app/runtime/session/*`
  - `detm_app/runtime/ui_runtime/*`
  - `detm_app/runtime/subscribers/{trace,watch,commit,fabric}/*`
- Docs and architecture references synchronized, including UML suite.
- Canonical entrypoint remains `main.py`; legacy wrapper `detm.py` removed.
- Stabilized TCP fabric transport connect path with relay-ready handshake.
- Reduced race-window for first message delivery right after connect.
- Fix targets CI flake in:
  - `tests/test_fabric_tcp_transport.py::test_tcp_fabric_transport_auth_accepts_with_matching_key`
- Public-repo readiness package added:
  - `LICENSE`, `COMMERCIAL_LICENSE.md`, `LICENSE_FAQ.md`, `NOTICE`, `THIRD_PARTY_NOTICES.md`
  - `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `SUPPORT.md`
  - GitHub templates (`ISSUE_TEMPLATE`, PR template, `CODEOWNERS`, `dependabot`)
- License model documented as:
  - source-available non-commercial (`PolyForm-Noncommercial-1.0.0`)
  - separate commercial licensing.
