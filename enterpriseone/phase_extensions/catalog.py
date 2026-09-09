"""Runtime catalog for the phase expansion packages."""
from __future__ import annotations
from dataclasses import dataclass
from importlib import import_module
from typing import Any

@dataclass(frozen=True)
class PhaseModule:
    number: int
    name: str
    module: str

PHASES = (
    PhaseModule(1, 'foundation_authentication', "enterpriseone.phase_extensions.phase_01_foundation_authentication.manifest"),
    PhaseModule(2, 'organization_users', "enterpriseone.phase_extensions.phase_02_organization_users.manifest"),
    PhaseModule(3, 'crm', "enterpriseone.phase_extensions.phase_03_crm.manifest"),
    PhaseModule(4, 'sales', "enterpriseone.phase_extensions.phase_04_sales.manifest"),
    PhaseModule(5, 'inventory', "enterpriseone.phase_extensions.phase_05_inventory.manifest"),
    PhaseModule(6, 'procurement', "enterpriseone.phase_extensions.phase_06_procurement.manifest"),
    PhaseModule(7, 'finance', "enterpriseone.phase_extensions.phase_07_finance.manifest"),
    PhaseModule(8, 'hr_payroll', "enterpriseone.phase_extensions.phase_08_hr_payroll.manifest"),
    PhaseModule(9, 'projects', "enterpriseone.phase_extensions.phase_09_projects.manifest"),
    PhaseModule(10, 'customer_support', "enterpriseone.phase_extensions.phase_10_customer_support.manifest"),
    PhaseModule(11, 'analytics_reporting', "enterpriseone.phase_extensions.phase_11_analytics_reporting.manifest"),
    PhaseModule(12, 'ai_ml', "enterpriseone.phase_extensions.phase_12_ai_ml.manifest"),
    PhaseModule(13, 'documents_notifications', "enterpriseone.phase_extensions.phase_13_documents_notifications.manifest"),
    PhaseModule(14, 'security_auditing', "enterpriseone.phase_extensions.phase_14_security_auditing.manifest"),
    PhaseModule(15, 'comprehensive_testing', "enterpriseone.phase_extensions.phase_15_comprehensive_testing.manifest"),
    PhaseModule(16, 'monitoring_optimization', "enterpriseone.phase_extensions.phase_16_monitoring_optimization.manifest"),
    PhaseModule(17, 'integration_finalization', "enterpriseone.phase_extensions.phase_17_integration_finalization.manifest"),
)

def load_manifests() -> list[dict[str, Any]]:
    result=[]
    for phase in PHASES:
        result.append(import_module(phase.module).describe())
    return result

def find_feature(term: str) -> list[dict[str, Any]]:
    needle=term.strip().lower()
    return [item for item in load_manifests() if any(needle in feature.lower() for feature in item["features"])]
