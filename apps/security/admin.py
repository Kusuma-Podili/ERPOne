from django.contrib import admin
from .models import *

@admin.register(SecurityPolicy)
class SecurityPolicyAdmin(admin.ModelAdmin): list_display=("name","organization","is_active","require_mfa","updated_at"); search_fields=("name","code"); list_filter=("is_active","require_mfa")
@admin.register(SecurityEvent)
class SecurityEventAdmin(admin.ModelAdmin): list_display=("event_type","severity","outcome","user","organization","risk_score","occurred_at"); list_filter=("severity","outcome","event_type"); search_fields=("event_type","request_id","resource_id")
@admin.register(AuditEntry)
class AuditEntryAdmin(admin.ModelAdmin): list_display=("action","model_label","object_id","actor","organization","created_at"); list_filter=("action","model_label"); search_fields=("object_id","object_repr","request_id")
@admin.register(SecurityIncident)
class SecurityIncidentAdmin(admin.ModelAdmin): list_display=("title","priority","status","organization","assigned_to","detected_at"); list_filter=("status","priority","category"); search_fields=("title","description")
@admin.register(SecurityAlert)
class SecurityAlertAdmin(admin.ModelAdmin): list_display=("title","severity","status","organization","created_at"); list_filter=("severity","status")
@admin.register(SecurityPolicyVersion)
class SecurityPolicyVersionAdmin(admin.ModelAdmin): list_display=("policy","version","created_at","created_by")
@admin.register(AccessReview)
class AccessReviewAdmin(admin.ModelAdmin): list_display=("title","organization","status","reviewer","due_at"); list_filter=("status","scope")
@admin.register(AccessReviewItem)
class AccessReviewItemAdmin(admin.ModelAdmin): list_display=("review","user","permission_code","decision","decided_at"); list_filter=("decision",)
@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin): list_display=("user","ip_address","device_name","status","last_seen_at"); list_filter=("status",)
for model in [RolePermissionSet,AuditRetentionPolicy,AuditArchive,TrustedDevice,MFAChallenge,MFARecoveryCode,IncidentEvent,ComplianceControl,ComplianceEvidence,SecurityRiskAssessment,SecurityAlertRule]:
    try: admin.site.register(model)
    except admin.sites.AlreadyRegistered: pass
