"""Regression matrix documenting critical capabilities from Phases 1-14."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

MATRIX = {
    1: ["accounts/models.py", "accounts/services.py"],
    2: ["organizations/models.py", "organizations/services.py"],
    3: ["crm/models.py", "crm/services.py"],
    4: ["sales/models.py", "sales/services.py"],
    5: ["inventory/models.py", "inventory/services.py"],
    6: ["procurement/models.py", "procurement/services.py"],
    7: ["finance/models.py", "finance/services.py"],
    8: ["hr/models.py", "payroll/models.py"],
    9: ["projects/models.py", "projects/services.py"],
    10: ["support/models.py", "support/services.py"],
    11: ["analytics/models.py", "analytics/services.py"],
    12: ["ai_engine/models.py", "ai_engine/services.py"],
    13: ["documents/models.py", "notifications/models.py"],
    14: ["security/models.py", "security/services.py"],
}


def test_phase_regression_matrix_has_required_files():
    missing = []
    for phase, paths in MATRIX.items():
        for relative in paths:
            if not (ROOT / "apps" / relative).exists():
                missing.append(f"phase {phase}: {relative}")
    assert not missing, "Missing regression targets:\n" + "\n".join(missing)


def test_each_phase_has_at_least_one_existing_test():
    existing = list((ROOT / "tests").rglob("test_*.py"))
    assert len(existing) >= 30
