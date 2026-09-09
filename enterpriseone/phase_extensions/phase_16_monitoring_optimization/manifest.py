"""Feature manifest for this phase."""

PHASE = 16
NAME = 'monitoring_optimization'
APPLICATION = 'monitoring'
FEATURES = ['health', 'metric', 'trace', 'latency', 'error_budget', 'slo', 'capacity', 'anomaly', 'alert', 'incident', 'deployment', 'resource', 'optimization', 'maintenance', 'readiness']

def describe() -> dict:
    return {"phase": PHASE, "name": NAME, "application": APPLICATION, "features": list(FEATURES)}
