"""Read-side query helpers for monitoring screens and reports."""
from django.db.models import Count, Avg
from django.utils import timezone
from datetime import timedelta
from .models import ServiceComponent, MonitoringAlert, Incident, PerformanceSnapshot, DeploymentRecord

def active_components(org):
    return ServiceComponent.objects.filter(organization=org,is_active=True).order_by("name")

def open_alerts(org, severity=None):
    qs=MonitoringAlert.objects.filter(organization=org,status__in=["OPEN","ACK"]).select_related("component","rule")
    return qs.filter(severity=severity) if severity else qs

def active_incidents(org):
    return Incident.objects.filter(organization=org,status__in=["OPEN","INVESTIGATING","MITIGATED"]).select_related("owner")

def performance_rollup(org, days=1):
    start=timezone.now()-timedelta(days=days)
    return PerformanceSnapshot.objects.filter(organization=org,window_end__gte=start).values("component","component__name").annotate(
        avg_latency=Avg("p95_latency_ms"), avg_availability=Avg("availability_percent"), requests=Count("id"))

def deployment_history(org, limit=25):
    return DeploymentRecord.objects.filter(organization=org).order_by("-started_at")[:limit]
