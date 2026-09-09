"""Feature manifest for this phase."""

PHASE = 15
NAME = 'comprehensive_testing'
APPLICATION = 'tests'
FEATURES = ['unit', 'integration', 'contract', 'property', 'fixture', 'factory', 'synthetic', 'performance', 'load', 'security', 'regression', 'workflow', 'mutation', 'coverage', 'quality']

def describe() -> dict:
    return {"phase": PHASE, "name": NAME, "application": APPLICATION, "features": list(FEATURES)}
