"""Offline source validation for the 500K expansion."""
from __future__ import annotations

from pathlib import Path
import ast
import hashlib
import json

SOURCE_SUFFIXES = {".py", ".html", ".css", ".js", ".md"}
EXCLUDED = {".git", "__pycache__", ".venv", "venv"}


def iter_source(root: Path):
    for path in root.rglob("*"):
        if path.is_file() and path.suffix in SOURCE_SUFFIXES and not any(part in EXCLUDED for part in path.parts):
            yield path


def count_lines(root: Path) -> dict[str, int]:
    result: dict[str, int] = {}
    for path in iter_source(root):
        result[path.suffix] = result.get(path.suffix, 0) + path.read_text(errors="ignore").count("\n")
    result["total"] = sum(result.values())
    result["code_total"] = sum(result.get(ext, 0) for ext in (".py", ".html", ".css", ".js"))
    return result


def compile_python(root: Path) -> list[str]:
    errors: list[str] = []
    for path in root.rglob("*.py"):
        if any(part in EXCLUDED for part in path.parts):
            continue
        try:
            ast.parse(path.read_text(errors="strict"), filename=str(path))
        except Exception as exc:
            errors.append(f"{path}: {exc}")
    return errors


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(iter_source(root)):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def validate(root: Path, minimum: int = 500_000) -> dict[str, object]:
    counts = count_lines(root)
    errors = compile_python(root)
    return {
        "counts": counts,
        "python_errors": errors,
        "minimum_code_loc": minimum,
        "meets_target": counts["code_total"] >= minimum and not errors,
        "digest": tree_digest(root),
    }


if __name__ == "__main__":
    result = validate(Path(__file__).resolve().parents[1])
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["meets_target"] else 1)
