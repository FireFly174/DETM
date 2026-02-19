from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from detm.runtime import api
from detm.runtime.level_policy import LevelPolicy, PolicyDecision
from detm.runtime.state import DETMState

from detm_app.runtime.subscribers.common import _effective_storage_limit, _tail_limit
from detm_app.runtime.subscribers.watch.flow import (
    build_operator_decisions_entry,
    resolve_policy_decision,
)
from detm_app.runtime.subscribers.watch.portability import (
    AntiGoodhartThresholds,
    PortabilityThresholds,
    evaluate_anti_goodhart,
    evaluate_portability_acceptance,
)


@dataclass
class OperatorDecisionWriter:
    """Writes operator decision artifacts (`operator_decisions.jsonl`)."""

    path: Path
    retention_window: int = 0
    compaction_budget: int = 0
    _total_decisions: int = 0
    _compatible_decisions: int = 0
    _reuse_decisions: int = 0
    _transferable_reuse_decisions: int = 0
    _torsion_flag_decisions: int = 0
    _operator_scopes: dict[str, set[tuple[str, str]]] | None = None
    _last_portability_panel: dict[str, Any] | None = None
    _fh: Any | None = None
    _unsub_step: Callable[[], None] | None = None
    _unsub_close: Callable[[], None] | None = None
    _portability_thresholds: PortabilityThresholds = PortabilityThresholds()
    _anti_goodhart_enabled: bool = True
    _anti_goodhart_thresholds: AntiGoodhartThresholds = AntiGoodhartThresholds()
    _anti_goodhart_policy_reaction_enabled: bool = True
    _anti_goodhart_prefer_runtime_profile: str = "stability"

    @classmethod
    def attach(
        cls,
        bus,
        path: Path,
        *,
        retention_window: int = 0,
        compaction_budget: int = 0,
    ) -> "OperatorDecisionWriter":
        writer = cls(
            path=path,
            retention_window=max(0, int(retention_window)),
            compaction_budget=max(0, int(compaction_budget)),
        )
        writer._unsub_step = bus.add_event_listener_unsub("step", writer.on_step)
        writer._unsub_close = bus.add_event_listener_unsub("close", writer.on_close)
        return writer

    def _ensure(self) -> None:
        if self._fh is not None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("a", encoding="utf-8")
        if self._operator_scopes is None:
            self._operator_scopes = {}

    def _normalize_runtime_profile(self, profile: str) -> str:
        value = str(profile).strip().lower()
        if value in {"stability", "throughput", "manual"}:
            return value
        return "stability"

    def _sync_anti_goodhart_policy(self, level_policy: LevelPolicy | None) -> None:
        if not isinstance(level_policy, LevelPolicy):
            return
        target_signal = str(level_policy.anti_goodhart_target_signal).strip()
        if not target_signal:
            target_signal = "operator_reuse"
        self._anti_goodhart_enabled = bool(level_policy.anti_goodhart_enabled)
        self._anti_goodhart_policy_reaction_enabled = bool(
            level_policy.anti_goodhart_policy_reaction_enabled
        )
        self._anti_goodhart_prefer_runtime_profile = self._normalize_runtime_profile(
            str(level_policy.anti_goodhart_prefer_runtime_profile)
        )
        self._anti_goodhart_thresholds = AntiGoodhartThresholds(
            target_signal=target_signal,
            min_target_delta=float(max(0.0, level_policy.anti_goodhart_min_target_delta)),
            min_degraded_signals=int(max(1, level_policy.anti_goodhart_min_degraded_signals)),
            degradation_epsilon=float(max(0.0, level_policy.anti_goodhart_degradation_epsilon)),
        )

    def _reaction_actions(self) -> list[str]:
        profile = str(self._anti_goodhart_prefer_runtime_profile)
        if profile == "throughput":
            profile_action = "prefer_throughput_runtime_profile"
        elif profile == "manual":
            profile_action = "prefer_manual_runtime_profile"
        else:
            profile_action = "prefer_stability_runtime_profile"
        return [
            "downweight_target_signal",
            "enable_extended_outerfields_audit",
            profile_action,
        ]

    def _update_portability_panel(self, *, decisions: list[dict[str, Any]]) -> dict[str, Any]:
        if self._operator_scopes is None:
            self._operator_scopes = {}
        for decision in decisions:
            self._total_decisions += 1
            contract = dict(decision.get("contract", {}))
            if bool(contract.get("compatible", False)):
                self._compatible_decisions += 1
            if bool(contract.get("torsion_flag", False)):
                self._torsion_flag_decisions += 1

            source = str(decision.get("source", "")).strip().lower()
            operator_id = str(decision.get("id", ""))
            scope = dict(decision.get("scope", {}))
            scope_tuple = (
                str(scope.get("level", "")),
                str(scope.get("mode", "")),
            )
            known_scopes = self._operator_scopes.get(operator_id, set())
            if source == "reuse":
                self._reuse_decisions += 1
                if len(known_scopes) > 0 and scope_tuple not in known_scopes:
                    self._transferable_reuse_decisions += 1
            known_scopes.add(scope_tuple)
            self._operator_scopes[operator_id] = known_scopes

        total = max(0, int(self._total_decisions))
        reuse = max(0, int(self._reuse_decisions))
        panel = {
            "hold_rate": (float(self._compatible_decisions) / float(total)) if total > 0 else 0.0,
            "operator_reuse": (float(reuse) / float(total)) if total > 0 else 0.0,
            "transferability": (
                float(self._transferable_reuse_decisions) / float(reuse)
                if reuse > 0
                else 0.0
            ),
            "torsion_flag_rate": (
                float(self._torsion_flag_decisions) / float(total)
                if total > 0
                else 0.0
            ),
            "torsion_health": (
                1.0 - (float(self._torsion_flag_decisions) / float(total))
                if total > 0
                else 1.0
            ),
            "counts": {
                "total_decisions": int(total),
                "compatible_decisions": int(self._compatible_decisions),
                "reuse_decisions": int(reuse),
                "transferable_reuse_decisions": int(self._transferable_reuse_decisions),
                "torsion_flag_decisions": int(self._torsion_flag_decisions),
            },
        }
        thresholds = self._portability_thresholds.to_dict()
        panel["thresholds"] = thresholds
        panel["acceptance"] = evaluate_portability_acceptance(
            panel=panel,
            thresholds=self._portability_thresholds,
        )
        portability_snapshot = dict(panel)
        if bool(self._anti_goodhart_enabled):
            anti_goodhart = evaluate_anti_goodhart(
                panel=panel,
                previous_panel=self._last_portability_panel,
                thresholds=self._anti_goodhart_thresholds,
            )
        else:
            anti_goodhart = {
                "goodhart_flag": False,
                "target_signal": str(self._anti_goodhart_thresholds.target_signal),
                "target_delta": 0.0,
                "degraded_signals": [],
                "degraded_signal_count": 0,
                "thresholds": self._anti_goodhart_thresholds.to_dict(),
                "rule": "goodhart_flag=(d_target>min_target_delta) and (degraded_signals>=min_degraded_signals)",
                "policy_reaction": {"apply": False, "actions": []},
                "applicability": "disabled",
            }

        reaction_enabled = bool(self._anti_goodhart_policy_reaction_enabled)
        goodhart_flag = bool(anti_goodhart.get("goodhart_flag", False))
        if not reaction_enabled:
            anti_goodhart["policy_reaction"] = {"apply": False, "actions": []}
        elif goodhart_flag:
            anti_goodhart["policy_reaction"] = {
                "apply": True,
                "actions": self._reaction_actions(),
            }
        anti_goodhart["policy_reaction_enabled"] = bool(reaction_enabled)
        anti_goodhart["preferred_runtime_profile"] = str(self._anti_goodhart_prefer_runtime_profile)
        panel["anti_goodhart"] = anti_goodhart
        self._last_portability_panel = portability_snapshot
        return panel

    def on_step(
        self,
        *,
        state: DETMState,
        n_ticks: int,
        requested_n_ticks: int = 0,
        observables: api.Observables,
        level_policy: LevelPolicy | None = None,
        policy_decision: PolicyDecision | None = None,
        **_rest: Any,
    ) -> None:
        self._sync_anti_goodhart_policy(level_policy)
        policy_decision = resolve_policy_decision(
            state=state,
            n_ticks=int(n_ticks),
            requested_n_ticks=int(requested_n_ticks),
            level_policy=level_policy,
            policy_decision=policy_decision,
        )
        if not bool(policy_decision.commit_boundary_crossed):
            return

        entry = build_operator_decisions_entry(
            state=state,
            observables=observables,
            policy_decision=policy_decision,
        )
        panel = self._update_portability_panel(decisions=list(entry.get("decisions", [])))
        summary = dict(entry.get("summary", {}))
        summary["portability_panel"] = panel
        entry["summary"] = summary
        self._ensure()
        assert self._fh is not None
        self._fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._fh.flush()

        limit = _effective_storage_limit(
            retention_window=int(self.retention_window),
            compaction_budget=int(self.compaction_budget),
        )
        if limit > 0:
            _tail_limit(self.path, max_entries=limit)

    def on_close(self, **_rest: Any) -> None:
        if self._fh is not None:
            self._fh.close()
            self._fh = None
        limit = _effective_storage_limit(
            retention_window=int(self.retention_window),
            compaction_budget=int(self.compaction_budget),
        )
        if limit > 0:
            _tail_limit(self.path, max_entries=limit)
        self.detach()

    def detach(self) -> None:
        if self._unsub_step is not None:
            self._unsub_step()
            self._unsub_step = None
        if self._unsub_close is not None:
            self._unsub_close()
            self._unsub_close = None


__all__ = ["OperatorDecisionWriter"]
