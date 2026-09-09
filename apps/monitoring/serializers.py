"""Small serialization layer used by monitoring consumers."""
from .models import ServiceComponent, MonitoringAlert, Incident, PerformanceSnapshot

def component_dict(obj):
    return {"id":str(obj.id),"name":obj.name,"code":obj.code,"status":obj.status,"criticality":obj.criticality,
            "environment":obj.environment,"tags":obj.tags,"active":obj.is_active}

def alert_dict(obj):
    return {"id":str(obj.id),"title":obj.title,"severity":obj.severity,"status":obj.status,"component":str(obj.component_id) if obj.component_id else None,
            "value":obj.current_value,"threshold":obj.threshold_value,"occurrences":obj.occurrence_count,"first_seen":obj.first_seen_at.isoformat()}

def incident_dict(obj):
    return {"id":str(obj.id),"title":obj.title,"status":obj.status,"priority":obj.priority,"summary":obj.summary,
            "started_at":obj.started_at.isoformat(),"detected_at":obj.detected_at.isoformat()}

def snapshot_dict(obj):
    return {"id":str(obj.id),"component":str(obj.component_id),"window_start":obj.window_start.isoformat(),"window_end":obj.window_end.isoformat(),
            "requests":obj.request_count,"errors":obj.error_count,"p50":obj.p50_latency_ms,"p95":obj.p95_latency_ms,"p99":obj.p99_latency_ms,
            "throughput":obj.throughput_per_second,"availability":obj.availability_percent}
