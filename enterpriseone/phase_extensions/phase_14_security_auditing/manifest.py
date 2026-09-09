"""Feature manifest for this phase."""

PHASE = 14
NAME = 'security_auditing'
APPLICATION = 'security'
FEATURES = ['identity_access', 'secret', 'device_trust', 'threat', 'detection', 'incident', 'evidence', 'compliance', 'risk', 'policy', 'session', 'mfa', 'audit', 'retention', 'privacy']

def describe() -> dict:
    return {"phase": PHASE, "name": NAME, "application": APPLICATION, "features": list(FEATURES)}
