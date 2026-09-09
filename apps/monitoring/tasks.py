"""Framework-friendly scheduled monitoring jobs."""
from datetime import timedelta
from django.utils import timezone
from .models import HealthCheck, MetricDefinition, AlertRule, ServiceComponent, SLODefinition, ResourceBudget
from .services import HealthService, MetricService, AlertService, PerformanceService, SLOService, ResourceOptimizationService


def mark_stale_components(stale_after_minutes=10):
    cutoff=timezone.now()-timedelta(minutes=stale_after_minutes); changed=0
    for component in ServiceComponent.objects.filter(is_active=True):
        latest=component.health_checks.filter(is_active=True).order_by("-last_run_at").first()
        if latest and latest.last_run_at and latest.last_run_at < cutoff and component.status != "DEGRADED":
            component.status="DEGRADED"; component.save(update_fields=["status","updated_at"]); changed+=1
    return changed

def evaluate_metric_rules(lookback_minutes=5):
    end=timezone.now(); start=end-timedelta(minutes=lookback_minutes); created=0
    for rule in AlertRule.objects.filter(is_active=True, metric__isnull=False):
        values=list(rule.metric.samples.filter(sampled_at__gte=start,sampled_at__lte=end).values_list("value",flat=True))
        if values:
            alert=AlertService.evaluate_rule(rule,values[-1]); created += bool(alert)
    return created

def build_recent_performance(hours=1):
    end=timezone.now(); start=end-timedelta(hours=hours); count=0
    for component in ServiceComponent.objects.filter(is_active=True): PerformanceService.build_snapshot(component,start,end); count+=1
    return count

def evaluate_slos(days=30):
    end=timezone.now(); start=end-timedelta(days=days); return [SLOService.evaluate(s,start,end) for s in SLODefinition.objects.filter(is_active=True)]

def generate_capacity_recommendations():
    return [ResourceOptimizationService.generate_recommendation(b) for b in ResourceBudget.objects.filter(is_active=True)]
