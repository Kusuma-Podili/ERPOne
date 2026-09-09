"""Cross-module scenario builders used by Phase 15 workflow tests."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from .base import RecordFactory, ScenarioContext


@dataclass
class OrderScenario:
    organization: dict
    user: dict
    customer: dict
    product: dict
    order: dict
    invoice: dict


@dataclass
class EmployeeScenario:
    organization: dict
    manager: dict
    employee: dict
    leave_request: dict
    payroll_input: dict


@dataclass
class SupportScenario:
    organization: dict
    customer: dict
    agent: dict
    ticket: dict
    sla: dict


@dataclass
class DocumentScenario:
    organization: dict
    owner: dict
    reviewer: dict
    document: dict
    approval: dict


class DomainScenarioFactory(RecordFactory):
    """Creates coherent business scenarios with predictable relationships."""

    def order_lifecycle(self) -> OrderScenario:
        org = self.organization()
        user = self.user(role="sales_manager")
        customer = self.customer(organization_id=org["id"])
        product = self.product()
        order = {
            "id": self.context.sequence.next("order"),
            "organization_id": org["id"],
            "customer_id": customer["id"],
            "owner_id": user["id"],
            "status": "draft",
            "lines": [{"product_id": product["id"], "quantity": 2, "unit_price": product["unit_price"]}],
        }
        invoice = self.invoice(customer["id"], order["lines"], organization_id=org["id"])
        return OrderScenario(org, user, customer, product, order, invoice)

    def employee_lifecycle(self) -> EmployeeScenario:
        org = self.organization("People Test Organization")
        manager = self.user(role="hr_manager", organization_id=org["id"])
        employee = self.user(role="employee", organization_id=org["id"])
        leave = {
            "id": self.context.sequence.next("leave"),
            "employee_id": employee["id"],
            "manager_id": manager["id"],
            "days": Decimal("2.0"),
            "status": "submitted",
        }
        payroll = {
            "employee_id": employee["id"],
            "gross": Decimal("45000.00"),
            "deductions": Decimal("5000.00"),
            "net": Decimal("40000.00"),
        }
        return EmployeeScenario(org, manager, employee, leave, payroll)

    def support_lifecycle(self) -> SupportScenario:
        org = self.organization("Support Test Organization")
        customer = self.customer(organization_id=org["id"])
        agent = self.user(role="support_agent", organization_id=org["id"])
        sla = {"id": self.context.sequence.next("sla"), "response_minutes": 30, "resolution_minutes": 240}
        ticket = {
            "id": self.context.sequence.next("ticket"),
            "organization_id": org["id"],
            "customer_id": customer["id"],
            "assignee_id": agent["id"],
            "priority": "high",
            "status": "open",
            "sla_id": sla["id"],
        }
        return SupportScenario(org, customer, agent, ticket, sla)

    def document_approval(self) -> DocumentScenario:
        org = self.organization("Document Test Organization")
        owner = self.user(role="employee", organization_id=org["id"])
        reviewer = self.user(role="manager", organization_id=org["id"])
        document = self.document(owner["id"], organization_id=org["id"], status="pending_review")
        approval = {
            "id": self.context.sequence.next("approval"),
            "document_id": document["id"],
            "reviewer_id": reviewer["id"],
            "status": "pending",
        }
        return DocumentScenario(org, owner, reviewer, document, approval)
