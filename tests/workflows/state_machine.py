"""Small deterministic workflow engine for testing enterprise state transitions."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


Guard = Callable[[str, str], bool]


@dataclass(frozen=True)
class Transition:
    source: str
    target: str
    event: str
    guard: Guard | None = None


@dataclass
class Workflow:
    name: str
    initial: str
    transitions: list[Transition] = field(default_factory=list)

    def add(self, source: str, event: str, target: str, guard: Guard | None = None) -> "Workflow":
        self.transitions.append(Transition(source, target, event, guard))
        return self

    def allowed_events(self, state: str) -> list[str]:
        return [t.event for t in self.transitions if t.source == state]

    def transition(self, state: str, event: str, actor: str = "system") -> str:
        matches = [t for t in self.transitions if t.source == state and t.event == event]
        if not matches:
            raise ValueError(f"event {event!r} is not valid from {state!r}")
        transition = matches[0]
        if transition.guard and not transition.guard(actor, state):
            raise PermissionError(f"actor {actor!r} failed guard for {event!r}")
        return transition.target

    def validate(self) -> list[str]:
        errors = []
        states = {self.initial}
        for transition in self.transitions:
            states.add(transition.source)
            states.add(transition.target)
        for state in states:
            if state != "cancelled" and not self.allowed_events(state) and state != "completed":
                errors.append(f"terminal state without explicit completion: {state}")
        return errors


def order_workflow() -> Workflow:
    return (
        Workflow("sales_order", "draft")
        .add("draft", "submit", "pending_approval")
        .add("pending_approval", "approve", "approved")
        .add("pending_approval", "reject", "rejected")
        .add("approved", "confirm", "confirmed")
        .add("confirmed", "ship", "fulfilled")
        .add("fulfilled", "close", "completed")
        .add("draft", "cancel", "cancelled")
        .add("pending_approval", "cancel", "cancelled")
    )


def ticket_workflow() -> Workflow:
    return (
        Workflow("support_ticket", "open")
        .add("open", "assign", "assigned")
        .add("assigned", "start", "in_progress")
        .add("in_progress", "resolve", "resolved")
        .add("resolved", "reopen", "reopened")
        .add("reopened", "start", "in_progress")
        .add("resolved", "close", "closed")
        .add("open", "close", "closed")
    )


def approval_workflow() -> Workflow:
    return (
        Workflow("approval", "draft")
        .add("draft", "submit", "pending")
        .add("pending", "approve", "approved")
        .add("pending", "reject", "rejected")
        .add("pending", "request_changes", "changes_requested")
        .add("changes_requested", "resubmit", "pending")
    )
