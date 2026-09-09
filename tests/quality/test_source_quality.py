"""Executable source-quality tests."""
from pathlib import Path
import ast

from .source_quality import PythonSourceScanner

ROOT = Path(__file__).resolve().parents[2]


def test_all_python_sources_parse():
    scanner = PythonSourceScanner(ROOT)
    issues = scanner.syntax_issues()
    assert not issues, "\n".join(f"{i.path}:{i.line}: {i.message}" for i in issues)


def test_project_contains_no_nested_git_repositories():
    nested = [p for p in ROOT.rglob(".git") if p.is_dir() and p != ROOT / ".git"]
    assert not nested


def test_python_files_have_valid_encoding():
    scanner = PythonSourceScanner(ROOT)
    for path in scanner.files():
        text = path.read_text(encoding="utf-8")
        assert "\ufffd" not in text, f"replacement character found in {path}"


def test_package_initializers_are_importable_syntax():
    scanner = PythonSourceScanner(ROOT)
    for path in scanner.files():
        if path.name == "__init__.py":
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def test_source_metrics_are_nontrivial():
    scanner = PythonSourceScanner(ROOT)
    metrics = scanner.complexity_metrics()
    assert metrics["files"] >= 250
    assert metrics["functions"] >= 500
    assert metrics["classes"] >= 100
    assert metrics["branches"] >= 500


def test_required_enterprise_apps_exist():
    required = {"accounts", "organizations", "crm", "sales", "inventory", "procurement", "finance", "hr", "payroll", "projects", "support", "analytics", "ai_engine", "documents", "notifications", "security"}
    apps = {p.parent.name for p in (ROOT / "apps").glob("*/apps.py")}
    assert required <= apps
