from .state_machine import approval_workflow, order_workflow, ticket_workflow


def test_order_happy_path():
    workflow = order_workflow()
    state = workflow.initial
    for event in ("submit", "approve", "confirm", "ship", "close"):
        state = workflow.transition(state, event)
    assert state == "completed"


def test_order_rejection_is_terminal():
    workflow = order_workflow()
    assert workflow.transition("pending_approval", "reject") == "rejected"


def test_ticket_reopen_cycle():
    workflow = ticket_workflow()
    state = workflow.transition("open", "assign")
    state = workflow.transition(state, "start")
    state = workflow.transition(state, "resolve")
    state = workflow.transition(state, "reopen")
    assert workflow.transition(state, "start") == "in_progress"


def test_invalid_event_is_rejected():
    workflow = approval_workflow()
    try:
        workflow.transition("approved", "approve")
    except ValueError as exc:
        assert "not valid" in str(exc)
    else:
        raise AssertionError("invalid transition was accepted")


def test_approval_change_request_loop():
    workflow = approval_workflow()
    state = workflow.transition("draft", "submit")
    state = workflow.transition(state, "request_changes")
    state = workflow.transition(state, "resubmit")
    assert state == "pending"
