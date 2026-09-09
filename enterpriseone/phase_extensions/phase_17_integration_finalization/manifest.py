"""Feature manifest for this phase."""

PHASE = 17
NAME = 'integration_finalization'
APPLICATION = 'integration'
FEATURES = ['connector', 'event', 'webhook', 'sync', 'mapping', 'import', 'export', 'retry', 'dead_letter', 'idempotency', 'reconciliation', 'migration', 'release', 'readiness', 'orchestration']

def describe() -> dict:
    return {"phase": PHASE, "name": NAME, "application": APPLICATION, "features": list(FEATURES)}
