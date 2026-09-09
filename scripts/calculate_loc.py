#!/usr/bin/env python
"""
Accurately measures genuine source Lines of Code (LOC) for EnterpriseOne.
Strictly excludes:
- .git metadata
- __pycache__ and bytecode
- Virtual environments (.venv, env, venv)
- Migrations
- Static build output / media
- Third-party packages
- Reports and documentation
"""
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

EXCLUDED_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "media",
    "staticfiles",
    "htmlcov",
    ".pytest_cache",
    "reports",
    "migrations",
}

VALID_EXTENSIONS = {
    ".py": "Python",
    ".html": "HTML Template",
    ".css": "CSS",
    ".js": "JavaScript",
    ".sql": "SQL",
}


def count_file_loc(filepath: Path) -> int:
    """Counts non-blank lines in a source file."""
    count = 0
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.strip():
                    count += 1
    except Exception:
        pass
    return count


def calculate_loc():
    stats_by_ext = {ext: {"files": 0, "loc": 0, "name": name} for ext, name in VALID_EXTENSIONS.items()}
    total_files = 0
    total_loc = 0

    for root, dirs, files in os.walk(ROOT_DIR):
        # Prune excluded directories in-place
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith(".")]

        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in stats_by_ext:
                fpath = Path(root) / file
                loc = count_file_loc(fpath)
                stats_by_ext[ext]["files"] += 1
                stats_by_ext[ext]["loc"] += loc
                total_files += 1
                total_loc += loc

    print("=" * 65)
    print("           ENTERPRISEONE GENUINE SOURCE LOC REPORT           ")
    print("=" * 65)
    print(f"{'Language / File Type':<25} | {'Files':<10} | {'LOC':<15}")
    print("-" * 65)
    for ext, data in sorted(stats_by_ext.items(), key=lambda x: x[1]["loc"], reverse=True):
        if data["files"] > 0:
            print(f"{data['name']:<25} | {data['files']:<10} | {data['loc']:<15,}")
    print("-" * 65)
    print(f"{'TOTAL SOURCE CODE':<25} | {total_files:<10} | {total_loc:<15,}")
    print("=" * 65)
    return total_loc


if __name__ == "__main__":
    calculate_loc()
