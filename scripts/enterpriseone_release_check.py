"""Offline release-readiness scanner for EnterpriseOne."""
from pathlib import Path
import ast, json, sys
ROOT=Path(__file__).resolve().parents[1]
errors=[]; files=list(ROOT.rglob("*.py"))
for path in files:
    if any(part in {".git","__pycache__"} for part in path.parts): continue
    try: ast.parse(path.read_text(encoding="utf-8"))
    except Exception as exc: errors.append(f"{path}: {exc}")
required=["manage.py","requirements.txt","README.md","PHASE_STATUS.md","pytest.ini"]
missing=[x for x in required if not (ROOT/x).exists()]
report={"python_files":len(files),"syntax_errors":errors,"missing_required_files":missing,"status":"PASS" if not errors and not missing else "FAIL"}
print(json.dumps(report,indent=2))
sys.exit(0 if report["status"]=="PASS" else 1)
