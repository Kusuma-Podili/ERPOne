"""Feature manifest for this phase."""

PHASE = 5
NAME = 'inventory'
APPLICATION = 'inventory'
FEATURES = ['stock', 'warehouse', 'bin', 'reservation', 'replenishment', 'transfer', 'lot', 'serial', 'costing', 'valuation', 'cycle_count', 'demand', 'allocation', 'expiry', 'catalog']

def describe() -> dict:
    return {"phase": PHASE, "name": NAME, "application": APPLICATION, "features": list(FEATURES)}
