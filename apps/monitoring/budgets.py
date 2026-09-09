"""Resource budget and cost-control calculations."""
from dataclasses import dataclass
@dataclass
class BudgetStatus:
    usage: float
    limit: float
    utilization: float
    state: str
    remaining: float

def evaluate_budget(usage, limit, warning=80, critical=95):
    usage=float(usage); limit=float(limit)
    utilization=usage/limit*100 if limit else 0
    state="NORMAL" if utilization<warning else "WARNING" if utilization<critical else "CRITICAL"
    return BudgetStatus(usage,limit,utilization,state,max(0,limit-usage))

def projected_usage(current, elapsed_ratio, total_ratio):
    if elapsed_ratio<=0:return float(current)
    return float(current)/elapsed_ratio*total_ratio

def savings_percent(before, after):
    before=float(before); after=float(after)
    return 0 if before==0 else (before-after)/before*100
