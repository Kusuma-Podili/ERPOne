"""Feature manifest for this phase."""

PHASE = 10
NAME = 'customer_support'
APPLICATION = 'support'
FEATURES = ['ticket', 'omnichannel', 'routing', 'sla', 'escalation', 'conversation', 'knowledge', 'macro', 'quality', 'satisfaction', 'refund', 'entitlement', 'workload', 'root_cause', 'self_service']

def describe() -> dict:
    return {"phase": PHASE, "name": NAME, "application": APPLICATION, "features": list(FEATURES)}
