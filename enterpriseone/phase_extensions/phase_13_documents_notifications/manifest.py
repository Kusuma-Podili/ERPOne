"""Feature manifest for this phase."""

PHASE = 13
NAME = 'documents_notifications'
APPLICATION = 'documents'
FEATURES = ['document', 'version', 'approval', 'retention', 'classification', 'search', 'template', 'signature', 'share', 'watermark', 'notification', 'digest', 'preference', 'delivery', 'reminder']

def describe() -> dict:
    return {"phase": PHASE, "name": NAME, "application": APPLICATION, "features": list(FEATURES)}
