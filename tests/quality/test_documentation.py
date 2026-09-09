from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_phase_documentation_exists():
    for path in (
        "PHASE_14_SECURITY_AUDITING.md",
        "documentation/PHASE_13_DOCUMENTS_NOTIFICATIONS.md",
        "PHASE_STATUS.md",
        "README.md",
    ):
        assert (ROOT / path).exists(), path


def test_phase_status_mentions_testing():
    text = (ROOT / "PHASE_STATUS.md").read_text(encoding="utf-8")
    assert "Phase 15" in text
