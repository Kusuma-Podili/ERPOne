"""Feature manifest for this phase."""

PHASE = 11
NAME = 'analytics_reporting'
APPLICATION = 'analytics'
FEATURES = ['metric', 'semantic', 'dashboard', 'cohort', 'funnel', 'attribution', 'forecast', 'anomaly', 'segment', 'drilldown', 'scorecard', 'benchmark', 'snapshot', 'lineage', 'report']

def describe() -> dict:
    return {"phase": PHASE, "name": NAME, "application": APPLICATION, "features": list(FEATURES)}
