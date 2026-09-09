"""Feature manifest for this phase."""

PHASE = 9
NAME = 'projects'
APPLICATION = 'projects'
FEATURES = ['portfolio', 'project', 'resource', 'capacity', 'schedule', 'milestone', 'task', 'dependency', 'risk', 'budget', 'billing', 'time', 'cost', 'quality', 'delivery']

def describe() -> dict:
    return {"phase": PHASE, "name": NAME, "application": APPLICATION, "features": list(FEATURES)}
