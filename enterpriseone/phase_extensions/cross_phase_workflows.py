"""Cross-phase orchestration primitives."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Callable, Mapping

@dataclass(frozen=True)
class WorkflowStep:
    name: str
    phase: int
    action: Callable[[Mapping[str, Any]], Mapping[str, Any]]
    required: bool = True

@dataclass
class WorkflowRun:
    name: str
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    outputs: list[Mapping[str, Any]] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)

    def fingerprint(self) -> str:
        return sha256(repr([dict(item) for item in self.outputs]).encode("utf-8")).hexdigest()

class CrossPhaseOrchestrator:
    def __init__(self, steps: list[WorkflowStep]):
        self.steps=sorted(steps, key=lambda step:(step.phase, step.name))

    def run(self, payload: Mapping[str, Any]) -> WorkflowRun:
        run=WorkflowRun(name="enterpriseone-cross-phase")
        context=dict(payload)
        for step in self.steps:
            try:
                result=dict(step.action(context))
                result.update({"phase": step.phase, "step": step.name})
                run.outputs.append(result)
                context.update(result)
            except Exception as exc:
                run.failures.append(f"{step.name}:{type(exc).__name__}:{exc}")
                if step.required:
                    break
        return run

def readiness_score(run: WorkflowRun) -> float:
    total=len(run.outputs)+len(run.failures)
    return 1.0 if total == 0 else len(run.outputs)/total
