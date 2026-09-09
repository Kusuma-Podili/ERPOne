"""Configuration-level regression checks that do not require a running server."""
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[2]


def _read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_all_apps_are_registered():
    text = _read("enterpriseone/settings/base.py")
    for app in ("accounts", "organizations", "crm", "sales", "inventory", "procurement", "finance", "hr", "payroll", "projects", "support", "analytics", "ai_engine", "documents", "notifications", "security"):
        assert f'"apps.{app}.apps.' in text


def test_security_middleware_is_registered():
    text = _read("enterpriseone/settings/base.py")
    assert "EnterpriseSecurityMiddleware" in text
    assert "SessionSecurityMiddleware" in text
    assert "AuditContextMiddleware" in text


def test_custom_user_model_is_configured():
    text = _read("enterpriseone/settings/base.py")
    assert 'AUTH_USER_MODEL = "accounts.User"' in text


def test_no_hardcoded_real_credentials_in_settings():
    for path in (ROOT / "enterpriseone").rglob("*.py"):
        text = path.read_text(encoding="utf-8").lower()
        forbidden = ("aws_secret_access_key", "private_key=", "password='production", "password=\"production")
        assert not any(token in text for token in forbidden), path


def test_requirements_contains_test_stack():
    text = _read("requirements.txt")
    for package in ("pytest", "pytest-django", "coverage"):
        assert package in text


def test_urls_are_python_parseable():
    for path in (ROOT / "enterpriseone").rglob("*.py"):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
