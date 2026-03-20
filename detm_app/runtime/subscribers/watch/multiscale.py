from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from detm.runtime.config import DETMConfig
from detm.runtime.pattern_memory import get_pattern_runtime_for_state
from detm.runtime.state import DETMState

from detm_app.runtime.subscribers.common import _effective_storage_limit, _tail_limit, _to_numpy, _trace_ref_for_tick
from detm_app.runtime.subscribers.watch.flow import resolve_policy_decision


@dataclass
class MultiscaleCatalogWriter:
    candidates_path: Path
    sources_path: Path
    verifications_path: Path
    scale_tension_path: Path
    hits_path: Path
    retention_window: int = 0
    compaction_budget: int = 0
    _fh_candidates: Any | None = None
    _fh_sources: Any | None = None
    _fh_verifications: Any | None = None
    _fh_tension: Any | None = None
    _fh_hits: Any | None = None
    _unsub_step: Callable[[], None] | None = None
    _unsub_close: Callable[[], None] | None = None

    @classmethod
    def attach(
        cls,
        bus,
        out_dir: Path,
        *,
        retention_window: int = 0,
        compaction_budget: int = 0,
    ) -> "MultiscaleCatalogWriter":
        writer = cls(
            candidates_path=out_dir / "multiscale_candidates.jsonl",
            sources_path=out_dir / "bridge_record_sources.jsonl",
            verifications_path=out_dir / "bridge_verifications.jsonl",
            scale_tension_path=out_dir / "scale_tension.jsonl",
            hits_path=out_dir / "operator_catalog_hits.jsonl",
            retention_window=max(0, int(retention_window)),
            compaction_budget=max(0, int(compaction_budget)),
        )
        writer._unsub_step = bus.add_event_listener_unsub("step", writer.on_step)
        writer._unsub_close = bus.add_event_listener_unsub("close", writer.on_close)
        return writer

    def _ensure(self) -> None:
        if self._fh_candidates is None:
            self.candidates_path.parent.mkdir(parents=True, exist_ok=True)
            self._fh_candidates = self.candidates_path.open("a", encoding="utf-8")
        if self._fh_sources is None:
            self.sources_path.parent.mkdir(parents=True, exist_ok=True)
            self._fh_sources = self.sources_path.open("a", encoding="utf-8")
        if self._fh_verifications is None:
            self.verifications_path.parent.mkdir(parents=True, exist_ok=True)
            self._fh_verifications = self.verifications_path.open("a", encoding="utf-8")
        if self._fh_tension is None:
            self.scale_tension_path.parent.mkdir(parents=True, exist_ok=True)
            self._fh_tension = self.scale_tension_path.open("a", encoding="utf-8")
        if self._fh_hits is None:
            self.hits_path.parent.mkdir(parents=True, exist_ok=True)
            self._fh_hits = self.hits_path.open("a", encoding="utf-8")

    def on_step(
        self,
        *,
        config: DETMConfig,
        state: DETMState,
        n_ticks: int,
        requested_n_ticks: int = 0,
        level_policy=None,
        policy_decision=None,
        **_rest: Any,
    ) -> None:
        multiscale = config.multiscale_catalog
        if not bool(multiscale.enabled):
            return
        resolved_policy = resolve_policy_decision(
            state=state,
            n_ticks=int(n_ticks),
            requested_n_ticks=int(requested_n_ticks),
            level_policy=level_policy,
            policy_decision=policy_decision,
        )
        if bool(multiscale.commit_only_sampling) and not bool(resolved_policy.commit_boundary_crossed):
            return

        runtime = get_pattern_runtime_for_state(state=state, config=config)
        observed = runtime.observe_multiscale(
            energy=_to_numpy(state.field_state.energy),
            tick=int(state.step_count),
            boundary=str(state.lattice.boundary),
            level=str(resolved_policy.active_level),
            trace_ref=_trace_ref_for_tick(int(state.step_count)),
        )

        tick = int(state.step_count)
        trace_ref = _trace_ref_for_tick(tick)
        self._ensure()
        assert self._fh_candidates is not None
        assert self._fh_sources is not None
        assert self._fh_verifications is not None
        assert self._fh_tension is not None
        assert self._fh_hits is not None
        self._fh_candidates.write(
            json.dumps(
                {
                    "tick": tick,
                    "trace_ref": trace_ref,
                    "mode": str(observed["mode"]),
                    "catalog_backend": dict(observed["catalog_backend"]),
                    "candidates": list(observed["candidates"]),
                },
                ensure_ascii=False,
            )
            + "\n"
        )
        self._fh_candidates.flush()
        self._fh_sources.write(
            json.dumps(
                {
                    "tick": tick,
                    "trace_ref": trace_ref,
                    "mode": str(observed["mode"]),
                    "catalog_backend": dict(observed["catalog_backend"]),
                    "sources": list(observed["sources"]),
                },
                ensure_ascii=False,
            )
            + "\n"
        )
        self._fh_sources.flush()
        self._fh_verifications.write(
            json.dumps(
                {
                    "tick": tick,
                    "trace_ref": trace_ref,
                    "mode": str(observed["mode"]),
                    "catalog_backend": dict(observed["catalog_backend"]),
                    "verifications": list(observed["verifications"]),
                },
                ensure_ascii=False,
            )
            + "\n"
        )
        self._fh_verifications.flush()
        self._fh_tension.write(
            json.dumps(
                {
                    "tick": tick,
                    "trace_ref": trace_ref,
                    "mode": str(observed["mode"]),
                    "summary": dict(observed["summary"]),
                    "catalog_backend": dict(observed["catalog_backend"]),
                },
                ensure_ascii=False,
            )
            + "\n"
        )
        self._fh_tension.flush()
        self._fh_hits.write(
            json.dumps(
                {
                    "tick": tick,
                    "trace_ref": trace_ref,
                    "mode": str(observed["mode"]),
                    "catalog_backend": dict(observed["catalog_backend"]),
                    "hit_count": int(observed["hit_count"]),
                    "miss_count": int(observed["miss_count"]),
                    "record_count": int(observed["record_count"]),
                    "source_count": int(observed.get("source_count", 0)),
                },
                ensure_ascii=False,
            )
            + "\n"
        )
        self._fh_hits.flush()
        self._tail_limit_all()

    def on_close(self, **_rest: Any) -> None:
        for handle_name in ("_fh_candidates", "_fh_sources", "_fh_verifications", "_fh_tension", "_fh_hits"):
            handle = getattr(self, handle_name)
            if handle is not None:
                handle.close()
                setattr(self, handle_name, None)
        self._tail_limit_all()
        self.detach()

    def _tail_limit_all(self) -> None:
        limit = _effective_storage_limit(
            retention_window=int(self.retention_window),
            compaction_budget=int(self.compaction_budget),
        )
        if limit <= 0:
            return
        _tail_limit(self.candidates_path, max_entries=limit)
        _tail_limit(self.sources_path, max_entries=limit)
        _tail_limit(self.verifications_path, max_entries=limit)
        _tail_limit(self.scale_tension_path, max_entries=limit)
        _tail_limit(self.hits_path, max_entries=limit)

    def detach(self) -> None:
        if self._unsub_step is not None:
            self._unsub_step()
            self._unsub_step = None
        if self._unsub_close is not None:
            self._unsub_close()
            self._unsub_close = None


__all__ = ["MultiscaleCatalogWriter"]
