"""Pure health-state calculations suitable for probes, workers and command-line checks."""
from dataclasses import dataclass
from enum import Enum

class HealthState(str, Enum):
    HEALTHY="HEALTHY"; DEGRADED="DEGRADED"; DOWN="DOWN"; UNKNOWN="UNKNOWN"

@dataclass(frozen=True)
class ProbeObservation:
    success: bool
    latency_ms: float=0
    status_code: int|None=None
    error: str=""

def classify(observations, failure_threshold=3, recovery_threshold=2):
    if not observations:return HealthState.UNKNOWN
    failures=successes=0
    for observation in observations:
        if observation.success: successes+=1; failures=0
        else: failures+=1; successes=0
    if failures>=failure_threshold:return HealthState.DOWN
    if successes>=recovery_threshold:return HealthState.HEALTHY
    return HealthState.DEGRADED

def availability(observations):
    if not observations:return 100.0
    return sum(o.success for o in observations)/len(observations)*100

def latency_summary(observations):
    values=sorted(o.latency_ms for o in observations)
    if not values:return {"min":0,"avg":0,"max":0}
    return {"min":values[0],"avg":sum(values)/len(values),"max":values[-1]}
