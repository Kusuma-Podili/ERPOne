"""Feature manifest for this phase."""

PHASE = 1
NAME = 'foundation_authentication'
APPLICATION = 'accounts'
FEATURES = ['identity', 'authentication', 'session', 'credential', 'authorization', 'risk', 'recovery', 'consent', 'device', 'profile', 'token', 'access', 'lockout', 'password', 'audit']

def describe() -> dict:
    return {"phase": PHASE, "name": NAME, "application": APPLICATION, "features": list(FEATURES)}
