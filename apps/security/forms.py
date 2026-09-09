from django import forms
from .models import SecurityPolicy, SecurityAlertRule, SecurityIncident, ComplianceControl, SecurityRiskAssessment

class SecurityPolicyForm(forms.ModelForm):
    class Meta: model=SecurityPolicy; fields=["organization","name","code","description","is_active","password_min_length","password_history_count","max_login_attempts","lockout_minutes","session_timeout_minutes","require_mfa","require_device_registration","allow_concurrent_sessions","ip_allowlist","ip_blocklist"]
class SecurityAlertRuleForm(forms.ModelForm):
    class Meta: model=SecurityAlertRule; fields="__all__"
class SecurityIncidentForm(forms.ModelForm):
    class Meta: model=SecurityIncident; fields=["organization","title","description","status","priority","category","assigned_to","detected_at","resolution"]
class ComplianceControlForm(forms.ModelForm):
    class Meta: model=ComplianceControl; fields="__all__"
class RiskAssessmentForm(forms.ModelForm):
    class Meta: model=SecurityRiskAssessment; fields="__all__"
