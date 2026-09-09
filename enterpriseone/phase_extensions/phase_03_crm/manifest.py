"""Feature manifest for this phase."""

PHASE = 3
NAME = 'crm'
APPLICATION = 'crm'
FEATURES = ['lead', 'account_plan', 'contact', 'opportunity', 'activity', 'campaign', 'segment', 'territory', 'pipeline', 'forecast', 'relationship', 'enrichment', 'scoring', 'engagement', 'retention']

def describe() -> dict:
    return {"phase": PHASE, "name": NAME, "application": APPLICATION, "features": list(FEATURES)}
