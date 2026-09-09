"""Feature manifest for this phase."""

PHASE = 12
NAME = 'ai_ml'
APPLICATION = 'ai_engine'
FEATURES = ['dataset', 'feature', 'training', 'evaluation', 'ranking', 'forecasting', 'classification', 'clustering', 'explanation', 'drift', 'experiment', 'registry', 'deployment', 'governance', 'bias']

def describe() -> dict:
    return {"phase": PHASE, "name": NAME, "application": APPLICATION, "features": list(FEATURES)}
