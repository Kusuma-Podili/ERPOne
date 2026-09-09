"""Feature manifest for this phase."""

PHASE = 2
NAME = 'organization_users'
APPLICATION = 'organizations'
FEATURES = ['tenant', 'hierarchy', 'membership', 'policy', 'role', 'team', 'department', 'location', 'calendar', 'directory', 'delegation', 'onboarding', 'offboarding', 'capacity', 'workspace']

def describe() -> dict:
    return {"phase": PHASE, "name": NAME, "application": APPLICATION, "features": list(FEATURES)}
