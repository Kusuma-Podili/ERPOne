"""Enterprise security, compliance and auditing domain models."""
import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone

class SecurityPolicy(models.Model):
    id= models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization=models.ForeignKey("organizations.Organization",on_delete=models.CASCADE,related_name="security_policies")
    name=models.CharField(max_length=160); code=models.SlugField(max_length=100)
    description=models.TextField(blank=True); is_active=models.BooleanField(default=True)
    password_min_length=models.PositiveSmallIntegerField(default=10); password_history_count=models.PositiveSmallIntegerField(default=5)
    max_login_attempts=models.PositiveSmallIntegerField(default=5); lockout_minutes=models.PositiveSmallIntegerField(default=15)
    session_timeout_minutes=models.PositiveIntegerField(default=480); require_mfa=models.BooleanField(default=False)
    require_device_registration=models.BooleanField(default=False); allow_concurrent_sessions=models.BooleanField(default=True)
    ip_allowlist=models.JSONField(default=list,blank=True); ip_blocklist=models.JSONField(default=list,blank=True)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,related_name="created_security_policies")
    created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta: unique_together=("organization","code"); ordering=("name",)
    def __str__(self): return self.name

class SecurityPolicyVersion(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); policy=models.ForeignKey(SecurityPolicy,on_delete=models.CASCADE,related_name="versions")
    version=models.PositiveIntegerField(); snapshot=models.JSONField(default=dict); change_reason=models.TextField(blank=True)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True); created_at=models.DateTimeField(auto_now_add=True)
    class Meta: unique_together=("policy","version"); ordering=("-version",)

class RolePermissionSet(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); organization=models.ForeignKey("organizations.Organization",on_delete=models.CASCADE,related_name="security_permission_sets")
    name=models.CharField(max_length=160); code=models.SlugField(max_length=100); description=models.TextField(blank=True)
    permissions=models.JSONField(default=list); is_active=models.BooleanField(default=True); created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta: unique_together=("organization","code")

class AccessReview(models.Model):
    STATUS=(("OPEN","Open"),("IN_PROGRESS","In Progress"),("COMPLETED","Completed"),("CANCELLED","Cancelled"))
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); organization=models.ForeignKey("organizations.Organization",on_delete=models.CASCADE,related_name="access_reviews")
    title=models.CharField(max_length=200); scope=models.CharField(max_length=80,default="USERS"); status=models.CharField(max_length=20,choices=STATUS,default="OPEN")
    due_at=models.DateTimeField(null=True,blank=True); reviewer=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,related_name="security_reviews")
    started_at=models.DateTimeField(null=True,blank=True); completed_at=models.DateTimeField(null=True,blank=True); notes=models.TextField(blank=True); created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=("-created_at",)

class AccessReviewItem(models.Model):
    DECISIONS=(("PENDING","Pending"),("KEEP","Keep"),("REVOKE","Revoke"),("MODIFY","Modify"),("ESCALATE","Escalate"))
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); review=models.ForeignKey(AccessReview,on_delete=models.CASCADE,related_name="items")
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="access_review_items"); permission_code=models.CharField(max_length=180)
    current_value=models.JSONField(default=dict); decision=models.CharField(max_length=20,choices=DECISIONS,default="PENDING"); reviewer_comment=models.TextField(blank=True); decided_at=models.DateTimeField(null=True,blank=True)
    class Meta: unique_together=("review","user","permission_code")

class SecurityEvent(models.Model):
    SEVERITY=(("INFO","Info"),("LOW","Low"),("MEDIUM","Medium"),("HIGH","High"),("CRITICAL","Critical"))
    OUTCOME=(("SUCCESS","Success"),("FAILURE","Failure"),("BLOCKED","Blocked"),("CHALLENGED","Challenged"))
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); organization=models.ForeignKey("organizations.Organization",on_delete=models.SET_NULL,null=True,blank=True,related_name="security_events")
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="security_events")
    event_type=models.CharField(max_length=120,db_index=True); severity=models.CharField(max_length=20,choices=SEVERITY,default="INFO",db_index=True); outcome=models.CharField(max_length=20,choices=OUTCOME,default="SUCCESS")
    ip_address=models.GenericIPAddressField(null=True,blank=True); user_agent=models.TextField(blank=True); request_id=models.CharField(max_length=100,blank=True,db_index=True)
    resource_type=models.CharField(max_length=120,blank=True); resource_id=models.CharField(max_length=100,blank=True); action=models.CharField(max_length=80,blank=True)
    metadata=models.JSONField(default=dict,blank=True); risk_score=models.DecimalField(max_digits=6,decimal_places=2,default=0); occurred_at=models.DateTimeField(default=timezone.now,db_index=True)
    class Meta: ordering=("-occurred_at",); indexes=[models.Index(fields=("organization","event_type","occurred_at")),models.Index(fields=("severity","occurred_at"))]

class AuditEntry(models.Model):
    ACTIONS=(("CREATE","Create"),("UPDATE","Update"),("DELETE","Delete"),("READ","Read"),("EXPORT","Export"),("APPROVE","Approve"),("REJECT","Reject"),("LOGIN","Login"),("LOGOUT","Logout"))
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); organization=models.ForeignKey("organizations.Organization",on_delete=models.SET_NULL,null=True,blank=True,related_name="audit_entries")
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="audit_entries")
    action=models.CharField(max_length=20,choices=ACTIONS); model_label=models.CharField(max_length=160); object_id=models.CharField(max_length=100,blank=True)
    object_repr=models.CharField(max_length=500,blank=True); before_data=models.JSONField(default=dict,blank=True); after_data=models.JSONField(default=dict,blank=True); changed_fields=models.JSONField(default=list,blank=True)
    ip_address=models.GenericIPAddressField(null=True,blank=True); user_agent=models.TextField(blank=True); request_id=models.CharField(max_length=100,blank=True); reason=models.TextField(blank=True); created_at=models.DateTimeField(auto_now_add=True,db_index=True)
    class Meta: ordering=("-created_at",); indexes=[models.Index(fields=("model_label","object_id")),models.Index(fields=("actor","created_at"))]

class AuditRetentionPolicy(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); organization=models.ForeignKey("organizations.Organization",on_delete=models.CASCADE,related_name="audit_retention_policies")
    event_type=models.CharField(max_length=120,blank=True); retention_days=models.PositiveIntegerField(default=2555); archive_before_delete=models.BooleanField(default=True); is_active=models.BooleanField(default=True); created_at=models.DateTimeField(auto_now_add=True)

class AuditArchive(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); organization=models.ForeignKey("organizations.Organization",on_delete=models.SET_NULL,null=True,blank=True)
    source_model=models.CharField(max_length=160); source_count=models.PositiveIntegerField(default=0); period_start=models.DateTimeField(); period_end=models.DateTimeField(); checksum=models.CharField(max_length=128); payload=models.JSONField(default=list); archived_at=models.DateTimeField(auto_now_add=True); archived_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True)

class UserSession(models.Model):
    STATUS=(("ACTIVE","Active"),("REVOKED","Revoked"),("EXPIRED","Expired"))
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="security_sessions")
    session_key=models.CharField(max_length=80,unique=True); ip_address=models.GenericIPAddressField(null=True,blank=True); user_agent=models.TextField(blank=True); device_fingerprint=models.CharField(max_length=128,blank=True,db_index=True)
    device_name=models.CharField(max_length=160,blank=True); location_label=models.CharField(max_length=160,blank=True); status=models.CharField(max_length=20,choices=STATUS,default="ACTIVE"); started_at=models.DateTimeField(auto_now_add=True); last_seen_at=models.DateTimeField(default=timezone.now); expires_at=models.DateTimeField(null=True,blank=True); revoked_at=models.DateTimeField(null=True,blank=True); revoke_reason=models.TextField(blank=True)
    class Meta: ordering=("-last_seen_at",)

class TrustedDevice(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="trusted_devices")
    fingerprint=models.CharField(max_length=128); name=models.CharField(max_length=160); platform=models.CharField(max_length=100,blank=True); browser=models.CharField(max_length=100,blank=True); ip_address=models.GenericIPAddressField(null=True,blank=True); last_seen_at=models.DateTimeField(default=timezone.now); trusted_at=models.DateTimeField(auto_now_add=True); expires_at=models.DateTimeField(null=True,blank=True); is_active=models.BooleanField(default=True)
    class Meta: unique_together=("user","fingerprint")

class MFAChallenge(models.Model):
    METHODS=(("TOTP","Authenticator"),("EMAIL","Email"),("SMS","SMS"),("BACKUP","Backup Code"))
    STATUS=(("PENDING","Pending"),("VERIFIED","Verified"),("EXPIRED","Expired"),("FAILED","Failed"))
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="mfa_challenges"); method=models.CharField(max_length=20,choices=METHODS); status=models.CharField(max_length=20,choices=STATUS,default="PENDING"); challenge_hash=models.CharField(max_length=128); attempts=models.PositiveSmallIntegerField(default=0); max_attempts=models.PositiveSmallIntegerField(default=5); expires_at=models.DateTimeField(); verified_at=models.DateTimeField(null=True,blank=True); created_at=models.DateTimeField(auto_now_add=True)

class MFARecoveryCode(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="mfa_recovery_codes"); code_hash=models.CharField(max_length=128); used_at=models.DateTimeField(null=True,blank=True); created_at=models.DateTimeField(auto_now_add=True)

class SecurityIncident(models.Model):
    STATUS=(("OPEN","Open"),("INVESTIGATING","Investigating"),("CONTAINED","Contained"),("RESOLVED","Resolved"),("CLOSED","Closed"))
    PRIORITY=(("P1","Critical"),("P2","High"),("P3","Medium"),("P4","Low"))
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); organization=models.ForeignKey("organizations.Organization",on_delete=models.CASCADE,related_name="security_incidents"); title=models.CharField(max_length=220); description=models.TextField(); status=models.CharField(max_length=20,choices=STATUS,default="OPEN"); priority=models.CharField(max_length=5,choices=PRIORITY,default="P3"); category=models.CharField(max_length=100); assigned_to=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="security_incidents_assigned"); source_event=models.ForeignKey(SecurityEvent,on_delete=models.SET_NULL,null=True,blank=True,related_name="incidents"); detected_at=models.DateTimeField(default=timezone.now); resolved_at=models.DateTimeField(null=True,blank=True); resolution=models.TextField(blank=True); created_at=models.DateTimeField(auto_now_add=True)

class IncidentEvent(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); incident=models.ForeignKey(SecurityIncident,on_delete=models.CASCADE,related_name="timeline"); actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,related_name="security_incident_events"); event_type=models.CharField(max_length=100); message=models.TextField(); metadata=models.JSONField(default=dict); created_at=models.DateTimeField(auto_now_add=True)

class ComplianceControl(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); organization=models.ForeignKey("organizations.Organization",on_delete=models.CASCADE,related_name="compliance_controls"); framework=models.CharField(max_length=80); control_id=models.CharField(max_length=80); title=models.CharField(max_length=220); description=models.TextField(); owner=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True); status=models.CharField(max_length=30,default="NOT_STARTED"); evidence_required=models.BooleanField(default=True); evidence_notes=models.TextField(blank=True); last_reviewed_at=models.DateTimeField(null=True,blank=True); next_review_at=models.DateTimeField(null=True,blank=True); created_at=models.DateTimeField(auto_now_add=True)
    class Meta: unique_together=("organization","framework","control_id")

class ComplianceEvidence(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); control=models.ForeignKey(ComplianceControl,on_delete=models.CASCADE,related_name="evidence"); title=models.CharField(max_length=220); source_type=models.CharField(max_length=60); source_reference=models.CharField(max_length=300); checksum=models.CharField(max_length=128,blank=True); collected_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True); collected_at=models.DateTimeField(auto_now_add=True); expires_at=models.DateTimeField(null=True,blank=True); notes=models.TextField(blank=True)

class SecurityRiskAssessment(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); organization=models.ForeignKey("organizations.Organization",on_delete=models.CASCADE,related_name="security_risk_assessments"); name=models.CharField(max_length=200); scope=models.JSONField(default=dict); inherent_score=models.DecimalField(max_digits=6,decimal_places=2,default=0); control_score=models.DecimalField(max_digits=6,decimal_places=2,default=0); residual_score=models.DecimalField(max_digits=6,decimal_places=2,default=0); methodology=models.CharField(max_length=100,default="weighted"); assessor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True); assessed_at=models.DateTimeField(default=timezone.now); next_review_at=models.DateTimeField(null=True,blank=True); status=models.CharField(max_length=30,default="DRAFT")

class SecurityAlertRule(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); organization=models.ForeignKey("organizations.Organization",on_delete=models.CASCADE,related_name="security_alert_rules"); name=models.CharField(max_length=160); event_type=models.CharField(max_length=120); condition=models.JSONField(default=dict); severity=models.CharField(max_length=20,default="MEDIUM"); threshold=models.PositiveIntegerField(default=1); window_minutes=models.PositiveIntegerField(default=15); create_incident=models.BooleanField(default=True); notify_user=models.BooleanField(default=True); is_active=models.BooleanField(default=True); created_at=models.DateTimeField(auto_now_add=True)

class SecurityAlert(models.Model):
    STATUS=(("OPEN","Open"),("ACK","Acknowledged"),("RESOLVED","Resolved"),("FALSE_POSITIVE","False Positive"))
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); organization=models.ForeignKey("organizations.Organization",on_delete=models.CASCADE,related_name="security_alerts"); rule=models.ForeignKey(SecurityAlertRule,on_delete=models.CASCADE,related_name="alerts"); event=models.ForeignKey(SecurityEvent,on_delete=models.SET_NULL,null=True); title=models.CharField(max_length=220); details=models.JSONField(default=dict); severity=models.CharField(max_length=20); status=models.CharField(max_length=30,choices=STATUS,default="OPEN"); acknowledged_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,related_name="acknowledged_security_alerts"); created_at=models.DateTimeField(auto_now_add=True); resolved_at=models.DateTimeField(null=True,blank=True)
