"""Smoke tests for all 17 phase expansion manifests."""
from enterpriseone.phase_extensions.catalog import load_manifests
from enterpriseone.phase_extensions.cross_phase_workflows import CrossPhaseOrchestrator, WorkflowStep, readiness_score


def test_all_phase_manifests_are_loadable():
    manifests = load_manifests()
    assert len(manifests) == 17
    assert [item["phase"] for item in manifests] == list(range(1, 18))
    assert all(len(item["features"]) >= 15 for item in manifests)


def test_cross_phase_orchestrator_runs_required_steps():
    steps = [
        WorkflowStep("identity", 1, lambda ctx: {"identity": "ready"}),
        WorkflowStep("finance", 7, lambda ctx: {"finance": "ready", "identity_seen": ctx["identity"]}),
        WorkflowStep("release", 17, lambda ctx: {"release": "ready", "finance_seen": ctx["finance"]}),
    ]
    run = CrossPhaseOrchestrator(steps).run({"seed": "smoke"})
    assert not run.failures
    assert len(run.outputs) == 3
    assert readiness_score(run) == 1.0
