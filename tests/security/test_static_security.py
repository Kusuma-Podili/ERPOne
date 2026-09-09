"""Static security regression checks."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]


def python_sources():
    return [p for p in ROOT.rglob("*.py") if ".git" not in p.parts and "__pycache__" not in p.parts]


def test_no_printed_secrets_in_application_source():
    suspicious = re.compile(r"print\s*\([^\n]*(password|secret|token|private_key)[^\n]*\)", re.I)
    hits = []
    for path in python_sources():
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if suspicious.search(line):
                hits.append(f"{path}:{number}")
    assert not hits, "Possible secret logging:\n" + "\n".join(hits)


def test_csrf_and_session_controls_are_present():
    settings = (ROOT / "enterpriseone/settings/base.py").read_text(encoding="utf-8")
    assert "CsrfViewMiddleware" in settings
    assert "SessionMiddleware" in settings
    assert "SESSION_COOKIE_HTTPONLY = True" in settings
    assert "SESSION_COOKIE_SAMESITE = \"Lax\"" in settings


def test_security_phase_contains_audit_and_risk_components():
    required = ["audit", "risk", "policies", "reporting", "management"]
    security = ROOT / "apps/security"
    for name in required:
        assert (security / f"{name}.py").exists(), name
