"""Feature manifest for this phase."""

PHASE = 7
NAME = 'finance'
APPLICATION = 'finance'
FEATURES = ['ledger', 'close', 'tax', 'treasury', 'cashflow', 'receivable', 'payable', 'revenue', 'expense', 'asset', 'budget', 'forecast', 'reconciliation', 'consolidation', 'cost_center']

def describe() -> dict:
    return {"phase": PHASE, "name": NAME, "application": APPLICATION, "features": list(FEATURES)}
