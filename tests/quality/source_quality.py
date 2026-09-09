"""Static source-quality primitives for EnterpriseOne CI.

These checks intentionally use only the Python standard library so they can run
before Django dependencies are installed in a clean build agent.
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SourceIssue:
    path: str
    line: int
    rule: str
    message: str


class PythonSourceScanner:
    """Scans Python source for syntax, hygiene and maintainability defects."""

    def __init__(self, root: str | Path, excluded: set[str] | None = None) -> None:
        self.root = Path(root).resolve()
        self.excluded = excluded or {".git", "__pycache__", ".venv", "venv"}

    def files(self) -> list[Path]:
        result = []
        for path in self.root.rglob("*.py"):
            if any(part in self.excluded for part in path.parts):
                continue
            result.append(path)
        return sorted(result)

    def parse(self, path: Path) -> ast.AST:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    def syntax_issues(self) -> list[SourceIssue]:
        issues = []
        for path in self.files():
            try:
                self.parse(path)
            except SyntaxError as exc:
                issues.append(SourceIssue(str(path), exc.lineno or 0, "PY-SYNTAX", str(exc)))
        return issues

    def todo_issues(self) -> list[SourceIssue]:
        issues = []
        pattern = re.compile(r"\b(TODO|FIXME|XXX)\b")
        for path in self.files():
            for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if pattern.search(line) and "test" not in str(path).lower():
                    issues.append(SourceIssue(str(path), line_no, "PY-TODO", "unresolved marker"))
        return issues

    def complexity_metrics(self) -> dict[str, int]:
        metrics = {"files": 0, "classes": 0, "functions": 0, "branches": 0, "imports": 0}
        for path in self.files():
            tree = self.parse(path)
            metrics["files"] += 1
            for node in ast.walk(tree):
                if isinstance(node, (ast.ClassDef,)):
                    metrics["classes"] += 1
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    metrics["functions"] += 1
                elif isinstance(node, (ast.If, ast.For, ast.While, ast.Try, ast.Match, ast.comprehension)):
                    metrics["branches"] += 1
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    metrics["imports"] += 1
        return metrics

    def line_metrics(self) -> dict[str, float]:
        files = self.files()
        lines = sum(len(path.read_text(encoding="utf-8").splitlines()) for path in files)
        nonblank = sum(sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip()) for path in files)
        return {"files": len(files), "lines": lines, "nonblank_lines": nonblank, "avg_lines_per_file": lines / len(files) if files else 0.0}
