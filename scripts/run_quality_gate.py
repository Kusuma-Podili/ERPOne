"""Run the dependency-light Phase 15 quality gate."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {".git", "__pycache__", ".venv", "venv"}


def source_files():
    return [p for p in ROOT.rglob("*.py") if not any(part in EXCLUDED for part in p.parts)]


def main() -> int:
    failures = []
    for path in source_files():
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            failures.append(f"{path}: {exc}")
    if failures:
        print("QUALITY GATE FAILED")
        print("\n".join(failures))
        return 1
    print(f"QUALITY GATE PASSED: {len(source_files())} Python files parsed successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
