"""Operational monitoring and optimization domain for EnterpriseOne."""
import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


class ServiceComponent(models.Model):
    STATUS = (("HEALTHY", "Healthy"), ("DEGRADED", "Degraded"), ("DOWN", "Down"), ("MAINTENANCE", "Maintenance"))
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name="monitored_components")
    name = models.CharField(max_length=160)
    code = models.SlugField(max_length=100)
    component_type = models.CharField(max_length=80, default="SERVICE")
    owner_team = models.CharField(max_length=160, blank=True)
    endpoint = models.URLField(blank=True)
    environment = models.CharField(max_length=40, default="production")
    status = models.CharField(max_length=20, choices=STATUS, default="HEALTHY")
    criticality = models.PositiveSmallIntegerField(default=3)
    expected_interval_seconds = models.PositiveIntegerField(default=60)
    timeout_seconds = models.PositiveIntegerField(default=10)
    tags = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        unique_together = (("organization", "code"),)
        ordering = ("name",)


class HealthCheck(models.Model):
    CHECK_TYPES = (("HTTP", "HTTP"), ("TCP", "TCP"), ("DATABASE", "Database"), ("QUEUE", "Queue"), ("CUSTOM", "Custom"))
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    component = models.ForeignKey(ServiceComponent, on_delete=models.CASCADE, related_name="health_checks")
    name = models.CharField(max_length=160)
    check_type = models.CharField(max_length=30, choices=CHECK_TYPES, default="HTTP")
    target = models.CharField(max_length=300, blank=True)
    expected_status = models.PositiveSmallIntegerField(default=200)
    interval_seconds = models.PositiveIntegerField(default=60)
    timeout_seconds = models.PositiveIntegerField(default=10)
    failure_threshold = models.PositiveSmallIntegerField(default=3)
    recovery_threshold = models.PositiveSmallIntegerField(default=2)
    is_active = models.BooleanField(default=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    consecutive_failures = models.PositiveIntegerField(default=0)
    consecutive_successes = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)


class HealthCheckResult(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    health_check = models.ForeignKey(HealthCheck, on_delete=models.CASCADE, related_name="results", db_column="check_id")
    success = models.BooleanField(default=False)
    status_code = models.PositiveSmallIntegerField(null=True, blank=True)
    latency_ms = models.FloatField(default=0)
    response_size = models.PositiveIntegerField(default=0)
    error_code = models.CharField(max_length=100, blank=True)
    error_message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    checked_at = models.DateTimeField(default=timezone.now, db_index=True)
    class Meta:
        ordering = ("-checked_at",)
        indexes = [models.Index(fields=("health_check", "checked_at")), models.Index(fields=("success", "checked_at"))]


class MetricDefinition(models.Model):
    TYPES = (("GAUGE", "Gauge"), ("COUNTER", "Counter"), ("HISTOGRAM", "Histogram"), ("RATE", "Rate"))
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name="monitoring_metrics")
    name = models.CharField(max_length=160)
    key = models.SlugField(max_length=120)
    unit = models.CharField(max_length=40, default="count")
    metric_type = models.CharField(max_length=20, choices=TYPES, default="GAUGE")
    description = models.TextField(blank=True)
    source = models.CharField(max_length=120, default="application")
    aggregation = models.CharField(max_length=30, default="avg")
    threshold_config = models.JSONField(default=dict, blank=True)
    labels = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = (("organization", "key"),)


class MetricSample(models.Model):
    id = models.BigAutoField(primary_key=True)
    metric = models.ForeignKey(MetricDefinition, on_delete=models.CASCADE, related_name="samples")
    component = models.ForeignKey(ServiceComponent, on_delete=models.SET_NULL, null=True, blank=True, related_name="metric_samples")
    value = models.FloatField()
    labels = models.JSONField(default=dict, blank=True)
    trace_id = models.CharField(max_length=120, blank=True, db_index=True)
    sampled_at = models.DateTimeField(default=timezone.now, db_index=True)
    class Meta:
        indexes = [models.Index(fields=("metric", "sampled_at")), models.Index(fields=("component", "sampled_at"))]


class PerformanceSnapshot(models.Model):
    PERIODS = (("MINUTE", "Minute"), ("HOUR", "Hour"), ("DAY", "Day"), ("WEEK", "Week"))
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name="performance_snapshots")
    component = models.ForeignKey(ServiceComponent, on_delete=models.CASCADE, related_name="performance_snapshots")
    period = models.CharField(max_length=20, choices=PERIODS, default="HOUR")
    window_start = models.DateTimeField()
    window_end = models.DateTimeField()
    request_count = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)
    p50_latency_ms = models.FloatField(default=0)
    p95_latency_ms = models.FloatField(default=0)
    p99_latency_ms = models.FloatField(default=0)
    throughput_per_second = models.FloatField(default=0)
    availability_percent = models.FloatField(default=100)
    cpu_percent = models.FloatField(default=0)
    memory_percent = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ("-window_end",)
        indexes = [models.Index(fields=("component", "window_end"))]


class SLODefinition(models.Model):
    TYPES = (("AVAILABILITY", "Availability"), ("LATENCY", "Latency"), ("ERROR_RATE", "Error rate"), ("THROUGHPUT", "Throughput"))
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name="slos")
    component = models.ForeignKey(ServiceComponent, on_delete=models.CASCADE, related_name="slos")
    name = models.CharField(max_length=180)
    objective_type = models.CharField(max_length=30, choices=TYPES)
    target = models.FloatField()
    warning_threshold = models.FloatField(null=True, blank=True)
    evaluation_window_days = models.PositiveIntegerField(default=30)
    error_budget_percent = models.FloatField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


class SLOEvaluation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slo = models.ForeignKey(SLODefinition, on_delete=models.CASCADE, related_name="evaluations")
    window_start = models.DateTimeField()
    window_end = models.DateTimeField()
    measured_value = models.FloatField(default=0)
    target_value = models.FloatField(default=0)
    compliance_percent = models.FloatField(default=0)
    error_budget_remaining = models.FloatField(default=100)
    breached = models.BooleanField(default=False)
    evaluated_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ("-evaluated_at",)


class AlertRule(models.Model):
    SEVERITIES = (("INFO", "Info"), ("WARNING", "Warning"), ("CRITICAL", "Critical"))
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name="monitoring_alert_rules")
    name = models.CharField(max_length=180)
    metric = models.ForeignKey(MetricDefinition, on_delete=models.CASCADE, related_name="alert_rules", null=True, blank=True)
    condition = models.JSONField(default=dict)
    severity = models.CharField(max_length=20, choices=SEVERITIES, default="WARNING")
    evaluation_window_minutes = models.PositiveIntegerField(default=5)
    trigger_count = models.PositiveIntegerField(default=1)
    recovery_count = models.PositiveIntegerField(default=1)
    cooldown_minutes = models.PositiveIntegerField(default=15)
    notification_channels = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


class MonitoringAlert(models.Model):
    STATUS = (("OPEN", "Open"), ("ACK", "Acknowledged"), ("RESOLVED", "Resolved"), ("SUPPRESSED", "Suppressed"))
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name="monitoring_alerts")
    rule = models.ForeignKey(AlertRule, on_delete=models.SET_NULL, null=True, related_name="alerts")
    component = models.ForeignKey(ServiceComponent, on_delete=models.SET_NULL, null=True, related_name="alerts")
    title = models.CharField(max_length=220)
    severity = models.CharField(max_length=20, default="WARNING")
    status = models.CharField(max_length=20, choices=STATUS, default="OPEN")
    fingerprint = models.CharField(max_length=128, db_index=True)
    message = models.TextField(blank=True)
    current_value = models.FloatField(null=True, blank=True)
    threshold_value = models.FloatField(null=True, blank=True)
    occurrence_count = models.PositiveIntegerField(default=1)
    first_seen_at = models.DateTimeField(default=timezone.now)
    last_seen_at = models.DateTimeField(default=timezone.now)
    acknowledged_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="acknowledged_monitoring_alerts")
    resolved_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    class Meta:
        indexes = [models.Index(fields=("organization", "status", "last_seen_at")), models.Index(fields=("fingerprint", "status"))]


class Incident(models.Model):
    STATUS = (("OPEN", "Open"), ("INVESTIGATING", "Investigating"), ("MITIGATED", "Mitigated"), ("RESOLVED", "Resolved"), ("CLOSED", "Closed"))
    PRIORITY = (("P1", "P1"), ("P2", "P2"), ("P3", "P3"), ("P4", "P4"))
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name="monitoring_incidents")
    title = models.CharField(max_length=220)
    status = models.CharField(max_length=20, choices=STATUS, default="OPEN")
    priority = models.CharField(max_length=5, choices=PRIORITY, default="P3")
    summary = models.TextField(blank=True)
    root_cause = models.TextField(blank=True)
    impact = models.TextField(blank=True)
    started_at = models.DateTimeField(default=timezone.now)
    detected_at = models.DateTimeField(default=timezone.now)
    mitigated_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="monitoring_incidents")
    class Meta:
        ordering = ("-started_at",)


class IncidentEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name="events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="monitoring_incident_events")
    event_type = models.CharField(max_length=80)
    message = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class DeploymentRecord(models.Model):
    STATUS = (("STARTED", "Started"), ("SUCCESS", "Success"), ("FAILED", "Failed"), ("ROLLED_BACK", "Rolled back"))
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name="deployments")
    service = models.CharField(max_length=160)
    version = models.CharField(max_length=100)
    environment = models.CharField(max_length=40, default="production")
    commit_hash = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default="STARTED")
    deployed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="monitoring_deployments")
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    rollback_reason = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    class Meta:
        ordering = ("-started_at",)


class ResourceBudget(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name="resource_budgets")
    component = models.ForeignKey(ServiceComponent, on_delete=models.CASCADE, related_name="resource_budgets")
    resource_type = models.CharField(max_length=40, default="CPU")
    monthly_limit = models.FloatField(default=0)
    current_usage = models.FloatField(default=0)
    unit = models.CharField(max_length=30, default="hours")
    warning_percent = models.FloatField(default=80)
    critical_percent = models.FloatField(default=95)
    period_start = models.DateField()
    period_end = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


class OptimizationRecommendation(models.Model):
    STATUS = (("NEW", "New"), ("REVIEW", "Under review"), ("ACCEPTED", "Accepted"), ("REJECTED", "Rejected"), ("IMPLEMENTED", "Implemented"))
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name="optimization_recommendations")
    component = models.ForeignKey(ServiceComponent, on_delete=models.SET_NULL, null=True, blank=True, related_name="optimization_recommendations")
    category = models.CharField(max_length=80)
    title = models.CharField(max_length=220)
    rationale = models.TextField()
    expected_impact = models.TextField(blank=True)
    estimated_savings = models.FloatField(default=0)
    confidence = models.FloatField(default=0)
    evidence = models.JSONField(default=dict, blank=True)
    priority = models.PositiveSmallIntegerField(default=3)
    status = models.CharField(max_length=20, choices=STATUS, default="NEW")
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="optimization_recommendations")
    created_at = models.DateTimeField(auto_now_add=True)
    implemented_at = models.DateTimeField(null=True, blank=True)


class MaintenanceWindow(models.Model):
    STATUS = (("PLANNED", "Planned"), ("ACTIVE", "Active"), ("COMPLETED", "Completed"), ("CANCELLED", "Cancelled"))
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name="maintenance_windows")
    name = models.CharField(max_length=180)
    services = models.JSONField(default=list, blank=True)
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default="PLANNED")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class MonitorAuditEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey("organizations.Organization", on_delete=models.SET_NULL, null=True, blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=80)
    resource_type = models.CharField(max_length=100)
    resource_id = models.CharField(max_length=100, blank=True)
    details = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)
