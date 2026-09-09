"""Feature manifest for this phase."""

PHASE = 4
NAME = 'sales'
APPLICATION = 'sales'
FEATURES = ['quote', 'pricing', 'order', 'commission', 'discount', 'contract', 'fulfillment', 'invoice_link', 'shipment', 'return', 'subscription', 'renewal', 'approval', 'revenue', 'channel']

def describe() -> dict:
    return {"phase": PHASE, "name": NAME, "application": APPLICATION, "features": list(FEATURES)}
