"""Model contract discovery and invariant checks for the enterprise domain."""
from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class ModelContract:
    app: str
    model: str
    required_fields: tuple[str, ...] = ()
    forbidden_fields: tuple[str, ...] = ()


class ModelContractScanner:
    def __init__(self, root: str | Path):
        self.root = Path(root)

    def model_classes(self, app: str) -> dict[str, ast.ClassDef]:
        path = self.root / "apps" / app / "models.py"
        if not path.exists():
            return {}
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        return {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}

    def field_names(self, node: ast.ClassDef) -> set[str]:
        names = set()
        for statement in node.body:
            if isinstance(statement, ast.Assign):
                targets = statement.targets
            elif isinstance(statement, ast.AnnAssign):
                targets = [statement.target]
            else:
                continue
            for target in targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        return names

    def validate(self, contracts: Iterable[ModelContract]) -> list[str]:
        errors = []
        for contract in contracts:
            models = self.model_classes(contract.app)
            node = models.get(contract.model)
            if node is None:
                errors.append(f"missing model {contract.app}.{contract.model}")
                continue
            fields = self.field_names(node)
            for field in contract.required_fields:
                if field not in fields:
                    errors.append(f"{contract.app}.{contract.model} missing field {field}")
            for field in contract.forbidden_fields:
                if field in fields:
                    errors.append(f"{contract.app}.{contract.model} contains forbidden field {field}")
        return errors


CORE_CONTRACTS = [
    ModelContract("accounts", "User", ("email",)),
    ModelContract("organizations", "Organization", ("name",)),
    ModelContract("crm", "Account", ()),
    ModelContract("sales", "SalesOrder", ()),
    ModelContract("inventory", "StockItem", ()),
    ModelContract("finance", "GLAccount", ()),
    ModelContract("hr", "Employee", ()),
    ModelContract("payroll", "Payslip", ()),
    ModelContract("projects", "Project", ()),
    ModelContract("support", "SupportTicket", ()),
    ModelContract("analytics", "Dashboard", ()),
    ModelContract("ai_engine", "MLModel", ()),
    ModelContract("documents", "Document", ()),
    ModelContract("notifications", "Notification", ()),
    ModelContract("security", "SecurityEvent", ()),
]
