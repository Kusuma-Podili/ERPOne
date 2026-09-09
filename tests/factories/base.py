"""Reusable deterministic builders for EnterpriseOne test scenarios."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from itertools import count
from typing import Any


class Sequence:
    """Small deterministic sequence generator used by factories."""

    def __init__(self, prefix: str = "TEST") -> None:
        self.prefix = prefix
        self._counter = count(1)

    def next(self, label: str = "item") -> str:
        return f"{self.prefix}-{label}-{next(self._counter):05d}"


@dataclass
class ScenarioContext:
    """In-memory scenario context shared by service and contract tests."""

    name: str = "default"
    seed: int = 42
    data: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    sequence: Sequence = field(default_factory=Sequence)

    def put(self, key: str, value: Any) -> Any:
        self.data[key] = value
        return value

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def emit(self, event_type: str, **payload: Any) -> dict[str, Any]:
        event = {"type": event_type, "payload": payload}
        self.events.append(event)
        return event

    def clear_events(self) -> None:
        self.events.clear()


class RecordFactory:
    """Generic factory for service-level tests that do not need a database."""

    def __init__(self, context: ScenarioContext | None = None) -> None:
        self.context = context or ScenarioContext()

    def user(self, role: str = "employee", **overrides: Any) -> dict[str, Any]:
        record = {
            "id": self.context.sequence.next("user"),
            "email": f"{self.context.sequence.next('mail').lower()}@test.enterpriseone",
            "role": role,
            "active": True,
        }
        record.update(overrides)
        return record

    def organization(self, name: str = "Test Organization", **overrides: Any) -> dict[str, Any]:
        record = {
            "id": self.context.sequence.next("org"),
            "name": name,
            "currency": "INR",
            "timezone": "Asia/Kolkata",
            "active": True,
        }
        record.update(overrides)
        return record

    def money(self, amount: int | str | Decimal, currency: str = "INR") -> dict[str, Any]:
        return {"amount": Decimal(str(amount)), "currency": currency}

    def customer(self, **overrides: Any) -> dict[str, Any]:
        record = {
            "id": self.context.sequence.next("customer"),
            "name": "Test Customer",
            "status": "active",
            "credit_limit": Decimal("100000.00"),
        }
        record.update(overrides)
        return record

    def product(self, sku: str | None = None, **overrides: Any) -> dict[str, Any]:
        record = {
            "id": self.context.sequence.next("product"),
            "sku": sku or self.context.sequence.next("SKU"),
            "name": "Test Product",
            "unit_price": Decimal("1250.00"),
            "quantity": 100,
        }
        record.update(overrides)
        return record

    def invoice(self, customer_id: str, lines: list[dict[str, Any]] | None = None, **overrides: Any) -> dict[str, Any]:
        lines = lines or [{"description": "Service", "quantity": 1, "unit_price": Decimal("1000.00")}]
        subtotal = sum(Decimal(str(x["quantity"])) * Decimal(str(x["unit_price"])) for x in lines)
        record = {
            "id": self.context.sequence.next("invoice"),
            "customer_id": customer_id,
            "status": "draft",
            "currency": "INR",
            "lines": lines,
            "subtotal": subtotal,
            "tax": Decimal("0.00"),
            "total": subtotal,
        }
        record.update(overrides)
        return record

    def notification(self, user_id: str, event: str = "test.event", **overrides: Any) -> dict[str, Any]:
        record = {
            "id": self.context.sequence.next("notification"),
            "user_id": user_id,
            "event": event,
            "channel": "in_app",
            "status": "queued",
            "read": False,
        }
        record.update(overrides)
        return record

    def document(self, owner_id: str, **overrides: Any) -> dict[str, Any]:
        record = {
            "id": self.context.sequence.next("document"),
            "owner_id": owner_id,
            "name": "Test Document.pdf",
            "version": 1,
            "status": "draft",
            "visibility": "private",
            "size": 1024,
            "checksum": "a" * 64,
        }
        record.update(overrides)
        return record
