"""Cross-domain model contract tests."""
from pathlib import Path
from .model_contracts import CORE_CONTRACTS, ModelContractScanner

ROOT = Path(__file__).resolve().parents[2]


def test_core_domain_models_are_present():
    errors = ModelContractScanner(ROOT).validate(CORE_CONTRACTS)
    assert not errors, "\n".join(errors)


def test_each_enterprise_app_has_a_model_module():
    apps = [p.parent for p in (ROOT / "apps").glob("*/apps.py")]
    missing = [app.name for app in apps if not (app / "models.py").exists()]
    assert not missing, f"apps without models.py: {missing}"
