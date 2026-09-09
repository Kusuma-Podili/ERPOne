from django import forms
from .models import ServiceComponent, HealthCheck, MetricDefinition, AlertRule, SLODefinition, MaintenanceWindow

class ComponentForm(forms.ModelForm):
    class Meta:
        model=ServiceComponent
        fields=["name","code","component_type","owner_team","endpoint","environment","criticality","expected_interval_seconds","timeout_seconds","tags","metadata","is_active"]

class HealthCheckForm(forms.ModelForm):
    class Meta:
        model=HealthCheck
        fields=["component","name","check_type","target","expected_status","interval_seconds","timeout_seconds","failure_threshold","recovery_threshold","is_active"]

class MetricForm(forms.ModelForm):
    class Meta:
        model=MetricDefinition
        fields=["organization","name","key","unit","metric_type","description","source","aggregation","threshold_config","labels","is_active"]

class AlertRuleForm(forms.ModelForm):
    class Meta:
        model=AlertRule
        fields=["organization","name","metric","condition","severity","evaluation_window_minutes","trigger_count","recovery_count","cooldown_minutes","notification_channels","is_active"]

class SLOForm(forms.ModelForm):
    class Meta:
        model=SLODefinition
        fields=["organization","component","name","objective_type","target","warning_threshold","evaluation_window_days","error_budget_percent","is_active"]

class MaintenanceWindowForm(forms.ModelForm):
    class Meta:
        model=MaintenanceWindow
        fields=["organization","name","services","reason","starts_at","ends_at","created_by"]
