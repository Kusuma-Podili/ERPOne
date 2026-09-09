"""Monitoring services: health evaluation, metrics, SLOs, alerting and incidents."""
import hashlib
import math
import statistics
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from .models import (
    ServiceComponent, HealthCheck, HealthCheckResult, MetricDefinition, MetricSample,
    PerformanceSnapshot, SLODefinition, SLOEvaluation, AlertRule, MonitoringAlert,
    Incident, IncidentEvent, DeploymentRecord, ResourceBudget, OptimizationRecommendation,
    MaintenanceWindow, MonitorAuditEvent,
)


def percentile(values, percent):
    data = sorted(float(v) for v in values if v is not None)
    if not data:
        return 0.0
    if len(data) == 1:
        return data[0]
    rank = (len(data) - 1) * (percent / 100.0)
    low, high = math.floor(rank), math.ceil(rank)
    if low == high:
        return data[low]
    return data[low] + (data[high] - data[low]) * (rank - low)


class HealthService:
    @staticmethod
    @transaction.atomic
    def record_result(check, success, latency_ms=0, status_code=None, error_code="", error_message="", metadata=None):
        result = HealthCheckResult.objects.create(health_check=check, success=success, latency_ms=latency_ms,
            status_code=status_code, error_code=error_code, error_message=error_message, metadata=metadata or {})
        check.last_run_at = result.checked_at
        if success:
            check.consecutive_successes += 1
            check.consecutive_failures = 0
            check.last_success_at = result.checked_at
        else:
            check.consecutive_failures += 1
            check.consecutive_successes = 0
        check.save(update_fields=["last_run_at", "last_success_at", "consecutive_successes", "consecutive_failures"])
        component = check.component
        if not success and check.consecutive_failures >= check.failure_threshold:
            component.status = "DOWN"
        elif success and check.consecutive_successes >= check.recovery_threshold:
            component.status = "HEALTHY"
        component.save(update_fields=["status", "updated_at"])
        return result

    @staticmethod
    def component_health(component):
        checks = list(component.health_checks.filter(is_active=True))
        if not checks:
            return {"status": component.status, "checks": 0, "healthy": 0, "availability": 100.0}
        healthy = sum(1 for c in checks if c.consecutive_failures < c.failure_threshold)
        return {"status": component.status, "checks": len(checks), "healthy": healthy,
                "availability": round(healthy / len(checks) * 100, 2)}


class MetricService:
    @staticmethod
    def record(metric, value, component=None, labels=None, trace_id="", sampled_at=None):
        return MetricSample.objects.create(metric=metric, value=float(value), component=component,
            labels=labels or {}, trace_id=trace_id, sampled_at=sampled_at or timezone.now())

    @staticmethod
    def summarize(metric, start, end):
        values = list(metric.samples.filter(sampled_at__gte=start, sampled_at__lt=end).values_list("value", flat=True))
        if not values:
            return {"count": 0, "min": 0, "max": 0, "avg": 0, "sum": 0, "p95": 0, "stddev": 0}
        return {"count": len(values), "min": min(values), "max": max(values), "avg": statistics.fmean(values),
                "sum": sum(values), "p95": percentile(values, 95), "stddev": statistics.pstdev(values) if len(values) > 1 else 0}

    @staticmethod
    def rate(metric, start, end):
        summary = MetricService.summarize(metric, start, end)
        seconds = max((end - start).total_seconds(), 1)
        return summary["sum"] / seconds


class PerformanceService:
    @staticmethod
    def build_snapshot(component, start, end, period="HOUR"):
        results = list(HealthCheckResult.objects.filter(health_check__component=component, checked_at__gte=start, checked_at__lt=end))
        latencies = [r.latency_ms for r in results]
        count = len(results)
        errors = sum(1 for r in results if not r.success)
        seconds = max((end - start).total_seconds(), 1)
        snapshot = PerformanceSnapshot.objects.create(
            organization=component.organization, component=component, period=period, window_start=start, window_end=end,
            request_count=count, error_count=errors, p50_latency_ms=percentile(latencies, 50),
            p95_latency_ms=percentile(latencies, 95), p99_latency_ms=percentile(latencies, 99),
            throughput_per_second=count / seconds, availability_percent=((count-errors) / count * 100) if count else 100,
        )
        return snapshot

    @staticmethod
    def compare(current, previous):
        fields = ("p95_latency_ms", "p99_latency_ms", "throughput_per_second", "availability_percent")
        output = {}
        for field in fields:
            old = float(getattr(previous, field) or 0)
            new = float(getattr(current, field) or 0)
            output[field] = {"current": new, "previous": old, "delta": new-old,
                             "percent_change": ((new-old)/old*100) if old else None}
        return output


class SLOService:
    @staticmethod
    def evaluate(slo, start, end):
        snapshots = PerformanceSnapshot.objects.filter(component=slo.component, window_start__gte=start, window_end__lte=end)
        if slo.objective_type == "AVAILABILITY":
            measured = statistics.fmean([s.availability_percent for s in snapshots]) if snapshots else 100.0
            compliant = measured >= slo.target
        elif slo.objective_type == "LATENCY":
            measured = statistics.fmean([s.p95_latency_ms for s in snapshots]) if snapshots else 0.0
            compliant = measured <= slo.target
        elif slo.objective_type == "ERROR_RATE":
            measured = statistics.fmean([(s.error_count/s.request_count*100) if s.request_count else 0 for s in snapshots]) if snapshots else 0.0
            compliant = measured <= slo.target
        else:
            measured = statistics.fmean([s.throughput_per_second for s in snapshots]) if snapshots else 0.0
            compliant = measured >= slo.target
        if slo.objective_type in ("AVAILABILITY", "THROUGHPUT"):
            compliance = min(measured / slo.target * 100, 100) if slo.target else 100
        else:
            compliance = min(slo.target / measured * 100, 100) if measured else 100
        budget = max(0.0, 100.0 - max(0.0, 100.0-compliance))
        return SLOEvaluation.objects.create(slo=slo, window_start=start, window_end=end, measured_value=measured,
            target_value=slo.target, compliance_percent=round(compliance, 2), error_budget_remaining=round(budget, 2), breached=not compliant)


class AlertService:
    @staticmethod
    def fingerprint(rule, component=None, extra=""):
        raw = f"{rule.organization_id}:{rule.id}:{component.id if component else ''}:{extra}"
        return hashlib.sha256(raw.encode()).hexdigest()

    @staticmethod
    def evaluate_rule(rule, value, component=None, now=None):
        now = now or timezone.now()
        condition = rule.condition or {}
        operator = condition.get("operator", "gt")
        threshold = float(condition.get("threshold", 0))
        comparisons = {"gt": value > threshold, "gte": value >= threshold, "lt": value < threshold,
                       "lte": value <= threshold, "eq": value == threshold, "neq": value != threshold}
        triggered = comparisons.get(operator, False)
        fp = AlertService.fingerprint(rule, component, f"{operator}:{threshold}")
        existing = MonitoringAlert.objects.filter(fingerprint=fp, status__in=["OPEN", "ACK"]).first()
        if triggered:
            if existing:
                existing.occurrence_count += 1; existing.last_seen_at = now; existing.current_value = value
                existing.save(update_fields=["occurrence_count", "last_seen_at", "current_value"])
                return existing
            return MonitoringAlert.objects.create(organization=rule.organization, rule=rule, component=component,
                title=rule.name, severity=rule.severity, fingerprint=fp, message=f"Condition {operator} {threshold} triggered",
                current_value=value, threshold_value=threshold)
        if existing and existing.status != "RESOLVED":
            existing.status = "RESOLVED"; existing.resolved_at = now; existing.save(update_fields=["status", "resolved_at"])
        return None


class IncidentService:
    @staticmethod
    @transaction.atomic
    def create_from_alert(alert, owner=None):
        incident = Incident.objects.create(organization=alert.organization, title=alert.title,
            priority={"CRITICAL":"P1", "WARNING":"P2", "INFO":"P4"}.get(alert.severity, "P3"),
            summary=alert.message, owner=owner)
        IncidentEvent.objects.create(incident=incident, actor=owner, event_type="ALERT_LINKED", message=alert.title,
                                     metadata={"alert_id": str(alert.id)})
        return incident

    @staticmethod
    def transition(incident, status, actor=None, message=""):
        allowed = {"OPEN": {"INVESTIGATING", "CLOSED"}, "INVESTIGATING": {"MITIGATED", "RESOLVED", "OPEN"},
                   "MITIGATED": {"RESOLVED", "INVESTIGATING"}, "RESOLVED": {"CLOSED", "OPEN"}, "CLOSED": set()}
        if status != incident.status and status not in allowed.get(incident.status, set()):
            raise ValueError(f"Invalid incident transition {incident.status} -> {status}")
        incident.status = status
        if status == "MITIGATED": incident.mitigated_at = timezone.now()
        if status == "RESOLVED": incident.resolved_at = timezone.now()
        incident.save(update_fields=["status", "mitigated_at", "resolved_at"])
        return IncidentEvent.objects.create(incident=incident, actor=actor, event_type="STATUS_CHANGED", message=message or status)


class DeploymentService:
    @staticmethod
    def start(org, service, version, environment="production", commit_hash="", user=None):
        return DeploymentRecord.objects.create(organization=org, service=service, version=version,
            environment=environment, commit_hash=commit_hash, deployed_by=user)

    @staticmethod
    def finish(deployment, status="SUCCESS", rollback_reason=""):
        deployment.status = status; deployment.completed_at = timezone.now(); deployment.rollback_reason = rollback_reason
        deployment.save(update_fields=["status", "completed_at", "rollback_reason"])
        return deployment


class ResourceOptimizationService:
    @staticmethod
    def utilization(budget):
        limit = float(budget.monthly_limit or 0)
        usage = float(budget.current_usage or 0)
        percent = usage / limit * 100 if limit else 0
        state = "NORMAL" if percent < budget.warning_percent else "WARNING" if percent < budget.critical_percent else "CRITICAL"
        return {"usage": usage, "limit": limit, "percent": round(percent, 2), "state": state}

    @staticmethod
    def generate_recommendation(budget, category="RESOURCE"):
        data = ResourceOptimizationService.utilization(budget)
        if data["state"] == "NORMAL":
            title = f"Review capacity for {budget.component.name}"
            rationale = "Current usage is below warning threshold; review trend before scaling."
            priority = 4
        else:
            title = f"Optimize {budget.resource_type} usage for {budget.component.name}"
            rationale = f"Resource usage is {data['percent']}% of the configured budget."
            priority = 1 if data["state"] == "CRITICAL" else 2
        return OptimizationRecommendation.objects.create(organization=budget.organization, component=budget.component,
            category=category, title=title, rationale=rationale, expected_impact="Reduce resource pressure and avoid capacity incidents.",
            confidence=85 if data["state"] != "NORMAL" else 60, evidence=data, priority=priority)


class MaintenanceService:
    @staticmethod
    def active_for(component_code, at=None):
        at = at or timezone.now()
        return MaintenanceWindow.objects.filter(starts_at__lte=at, ends_at__gte=at, status="ACTIVE").filter(services__contains=[component_code]).exists()

    @staticmethod
    def activate(window):
        window.status = "ACTIVE"; window.save(update_fields=["status"]); return window

    @staticmethod
    def complete(window):
        window.status = "COMPLETED"; window.save(update_fields=["status"]); return window


class MonitoringAuditService:
    @staticmethod
    def record(org, action, resource_type, resource_id="", actor=None, details=None):
        return MonitorAuditEvent.objects.create(organization=org, actor=actor, action=action,
            resource_type=resource_type, resource_id=str(resource_id), details=details or {})


class MonitoringDashboardService:
    @staticmethod
    def summary(org):
        components = list(ServiceComponent.objects.filter(organization=org, is_active=True))
        alerts = MonitoringAlert.objects.filter(organization=org, status__in=["OPEN", "ACK"])
        incidents = Incident.objects.filter(organization=org, status__in=["OPEN", "INVESTIGATING", "MITIGATED"])
        return {"components": len(components), "healthy": sum(c.status == "HEALTHY" for c in components),
                "degraded": sum(c.status == "DEGRADED" for c in components), "down": sum(c.status == "DOWN" for c in components),
                "open_alerts": alerts.count(), "active_incidents": incidents.count(),
                "critical_alerts": alerts.filter(severity="CRITICAL").count()}
