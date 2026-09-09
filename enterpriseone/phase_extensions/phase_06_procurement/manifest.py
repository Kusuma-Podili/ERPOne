"""Feature manifest for this phase."""

PHASE = 6
NAME = 'procurement'
APPLICATION = 'procurement'
FEATURES = ['supplier', 'sourcing', 'rfq', 'bid', 'purchase', 'contract', 'approval', 'vendor_score', 'three_way_match', 'receipt', 'spend', 'category', 'compliance', 'risk', 'negotiation']

def describe() -> dict:
    return {"phase": PHASE, "name": NAME, "application": APPLICATION, "features": list(FEATURES)}
