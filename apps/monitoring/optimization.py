"""Optimization decision engine based on observed utilization and performance."""
from dataclasses import dataclass
from .analytics import linear_trend

@dataclass
class OptimizationSignal:
    category: str
    priority: int
    title: str
    rationale: str
    estimated_impact: float
    evidence: dict
    def __getitem__(self, item): return getattr(self, item)

class OptimizationEngine:
    def latency_signal(self, values, threshold):
        avg=sum(values)/len(values) if values else 0
        trend=linear_trend(values)
        if avg <= threshold and trend["direction"] != "UP": return None
        return OptimizationSignal("LATENCY", 1 if avg>threshold*1.5 else 2,
            "Investigate rising latency", f"Average latency is {avg:.2f}ms against {threshold:.2f}ms target.",
            max(0, avg-threshold), {"average":avg,"target":threshold,"trend":trend})

    def error_signal(self, errors, requests, threshold_percent=1):
        rate=(errors/requests*100) if requests else 0
        if rate<=threshold_percent:return None
        return OptimizationSignal("RELIABILITY",1 if rate>threshold_percent*2 else 2,
            "Reduce elevated error rate", f"Error rate is {rate:.2f}%.", rate-threshold_percent,
            {"errors":errors,"requests":requests,"rate":rate})

    def capacity_signal(self, utilization_percent, warning=80, critical=95):
        if utilization_percent<warning:return None
        priority=1 if utilization_percent>=critical else 2
        return OptimizationSignal("CAPACITY",priority,"Review resource capacity",
            f"Utilization has reached {utilization_percent:.2f}%.",utilization_percent-warning,
            {"utilization":utilization_percent,"warning":warning,"critical":critical})

    def summarize(self, signals):
        active=[s for s in signals if s]
        return {"count":len(active),"critical":sum(s.priority==1 for s in active),
                "categories":sorted({s.category for s in active}),"signals":[s.__dict__ for s in active]}
