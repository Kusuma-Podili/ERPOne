from django.contrib import admin
from .models import *

@admin.register(ServiceComponent)
class ServiceComponentAdmin(admin.ModelAdmin):
    list_display=("name","code","environment","status","criticality","is_active")
    list_filter=("status","environment","is_active")
    search_fields=("name","code","owner_team")

@admin.register(HealthCheck)
class HealthCheckAdmin(admin.ModelAdmin):
    list_display=("name","component","check_type","is_active","last_run_at","consecutive_failures")
    list_filter=("check_type","is_active")

@admin.register(HealthCheckResult)
class HealthCheckResultAdmin(admin.ModelAdmin):
    list_display=("health_check","success","latency_ms","checked_at")
    list_filter=("success",)

@admin.register(MetricDefinition)
class MetricDefinitionAdmin(admin.ModelAdmin):
    list_display=("name","key","metric_type","unit","is_active")
    search_fields=("name","key")

@admin.register(MetricSample)
class MetricSampleAdmin(admin.ModelAdmin):
    list_display=("metric","value","component","sampled_at")
    list_filter=("metric",)

@admin.register(PerformanceSnapshot)
class PerformanceSnapshotAdmin(admin.ModelAdmin):
    list_display=("component","period","p95_latency_ms","availability_percent","window_end")
    list_filter=("period",)

@admin.register(SLODefinition)
class SLODefinitionAdmin(admin.ModelAdmin):
    list_display=("name","component","objective_type","target","is_active")
    list_filter=("objective_type","is_active")

@admin.register(SLOEvaluation)
class SLOEvaluationAdmin(admin.ModelAdmin):
    list_display=("slo","measured_value","target_value","compliance_percent","breached","evaluated_at")
    list_filter=("breached",)

@admin.register(AlertRule)
class AlertRuleAdmin(admin.ModelAdmin):
    list_display=("name","severity","metric","is_active")
    list_filter=("severity","is_active")

@admin.register(MonitoringAlert)
class MonitoringAlertAdmin(admin.ModelAdmin):
    list_display=("title","severity","status","occurrence_count","last_seen_at")
    list_filter=("severity","status")
    search_fields=("title","fingerprint")

@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display=("title","priority","status","started_at","resolved_at")
    list_filter=("priority","status")
    search_fields=("title","root_cause")

@admin.register(IncidentEvent)
class IncidentEventAdmin(admin.ModelAdmin):
    list_display=("incident","event_type","actor","created_at")

@admin.register(DeploymentRecord)
class DeploymentRecordAdmin(admin.ModelAdmin):
    list_display=("service","version","environment","status","started_at","completed_at")
    list_filter=("status","environment")

@admin.register(ResourceBudget)
class ResourceBudgetAdmin(admin.ModelAdmin):
    list_display=("component","resource_type","monthly_limit","current_usage","unit")

@admin.register(OptimizationRecommendation)
class OptimizationRecommendationAdmin(admin.ModelAdmin):
    list_display=("title","category","priority","confidence","status","created_at")
    list_filter=("category","priority","status")

@admin.register(MaintenanceWindow)
class MaintenanceWindowAdmin(admin.ModelAdmin):
    list_display=("name","status","starts_at","ends_at")
    list_filter=("status",)

@admin.register(MonitorAuditEvent)
class MonitorAuditEventAdmin(admin.ModelAdmin):
    list_display=("action","resource_type","actor","occurred_at")
    list_filter=("action","resource_type")
