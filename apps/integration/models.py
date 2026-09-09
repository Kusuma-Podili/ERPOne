import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone

class IntegrationStatus(models.TextChoices):
    ACTIVE="ACTIVE","Active"; PAUSED="PAUSED","Paused"; FAILED="FAILED","Failed"; DISABLED="DISABLED","Disabled"
class RunStatus(models.TextChoices):
    QUEUED="QUEUED","Queued"; RUNNING="RUNNING","Running"; SUCCEEDED="SUCCEEDED","Succeeded"; PARTIAL="PARTIAL","Partial"; FAILED="FAILED","Failed"; CANCELLED="CANCELLED","Cancelled"

class IntegrationConnection(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization=models.ForeignKey("organizations.Organization",on_delete=models.CASCADE,related_name="integration_connections")
    name=models.CharField(max_length=180); code=models.SlugField(max_length=100)
    provider=models.CharField(max_length=100); connection_type=models.CharField(max_length=60,default="HTTP")
    base_url=models.URLField(blank=True); status=models.CharField(max_length=20,choices=IntegrationStatus.choices,default=IntegrationStatus.ACTIVE)
    configuration=models.JSONField(default=dict,blank=True); secret_reference=models.CharField(max_length=180,blank=True)
    retry_limit=models.PositiveSmallIntegerField(default=3); timeout_seconds=models.PositiveIntegerField(default=30)
    last_success_at=models.DateTimeField(null=True,blank=True); last_failure_at=models.DateTimeField(null=True,blank=True)
    failure_count=models.PositiveIntegerField(default=0); metadata=models.JSONField(default=dict,blank=True)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.SET_NULL,related_name="created_integrations")
    created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta: unique_together=(("organization","code"),); ordering=("name",)

class IntegrationEndpoint(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    connection=models.ForeignKey(IntegrationConnection,on_delete=models.CASCADE,related_name="endpoints")
    name=models.CharField(max_length=180); code=models.SlugField(max_length=100); direction=models.CharField(max_length=20,default="OUTBOUND")
    path=models.CharField(max_length=300); method=models.CharField(max_length=12,default="POST"); event_code=models.CharField(max_length=120,blank=True)
    headers=models.JSONField(default=dict,blank=True); query_params=models.JSONField(default=dict,blank=True); payload_template=models.JSONField(default=dict,blank=True)
    active=models.BooleanField(default=True); rate_limit_per_minute=models.PositiveIntegerField(default=60); created_at=models.DateTimeField(auto_now_add=True)
    class Meta: unique_together=(("connection","code"),)

class IntegrationMapping(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization=models.ForeignKey("organizations.Organization",on_delete=models.CASCADE,related_name="integration_mappings")
    name=models.CharField(max_length=180); source_domain=models.CharField(max_length=80); target_domain=models.CharField(max_length=80)
    field_map=models.JSONField(default=dict); transforms=models.JSONField(default=dict,blank=True); defaults=models.JSONField(default=dict,blank=True)
    validation_rules=models.JSONField(default=dict,blank=True); version=models.PositiveIntegerField(default=1); active=models.BooleanField(default=True)
    created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)

class IntegrationJob(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization=models.ForeignKey("organizations.Organization",on_delete=models.CASCADE,related_name="integration_jobs")
    name=models.CharField(max_length=180); code=models.SlugField(max_length=100); job_type=models.CharField(max_length=60,default="SYNC")
    connection=models.ForeignKey(IntegrationConnection,null=True,blank=True,on_delete=models.SET_NULL,related_name="jobs")
    endpoint=models.ForeignKey(IntegrationEndpoint,null=True,blank=True,on_delete=models.SET_NULL,related_name="jobs")
    mapping=models.ForeignKey(IntegrationMapping,null=True,blank=True,on_delete=models.SET_NULL,related_name="jobs")
    schedule_expression=models.CharField(max_length=120,blank=True); batch_size=models.PositiveIntegerField(default=100)
    max_retries=models.PositiveSmallIntegerField(default=3); enabled=models.BooleanField(default=True); parameters=models.JSONField(default=dict,blank=True)
    created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta: unique_together=(("organization","code"),)

class IntegrationJobRun(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    job=models.ForeignKey(IntegrationJob,on_delete=models.CASCADE,related_name="runs")
    status=models.CharField(max_length=20,choices=RunStatus.choices,default=RunStatus.QUEUED)
    correlation_id=models.CharField(max_length=120,db_index=True); idempotency_key=models.CharField(max_length=180,blank=True,db_index=True)
    started_at=models.DateTimeField(null=True,blank=True); finished_at=models.DateTimeField(null=True,blank=True)
    processed_count=models.PositiveIntegerField(default=0); success_count=models.PositiveIntegerField(default=0); failed_count=models.PositiveIntegerField(default=0)
    duration_ms=models.PositiveIntegerField(default=0); error_message=models.TextField(blank=True); metrics=models.JSONField(default=dict,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=("-created_at",); indexes=[models.Index(fields=("job","created_at")),models.Index(fields=("status","created_at"))]
    def complete(self,status,**metrics):
        self.status=status; self.finished_at=timezone.now(); self.metrics={**self.metrics,**metrics}; self.save(update_fields=["status","finished_at","metrics"])

class IntegrationEvent(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization=models.ForeignKey("organizations.Organization",on_delete=models.CASCADE,related_name="integration_events")
    event_code=models.CharField(max_length=140,db_index=True); aggregate_type=models.CharField(max_length=100); aggregate_id=models.CharField(max_length=120)
    payload=models.JSONField(default=dict); headers=models.JSONField(default=dict,blank=True); correlation_id=models.CharField(max_length=120,db_index=True)
    idempotency_key=models.CharField(max_length=180,unique=True); occurred_at=models.DateTimeField(default=timezone.now)
    published_at=models.DateTimeField(null=True,blank=True); processed_at=models.DateTimeField(null=True,blank=True); retry_count=models.PositiveSmallIntegerField(default=0)
    status=models.CharField(max_length=20,choices=RunStatus.choices,default=RunStatus.QUEUED); error_message=models.TextField(blank=True)
    class Meta: ordering=("-occurred_at",); indexes=[models.Index(fields=("organization","event_code","occurred_at")),models.Index(fields=("status","occurred_at"))]

class IntegrationDelivery(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    event=models.ForeignKey(IntegrationEvent,on_delete=models.CASCADE,related_name="deliveries")
    endpoint=models.ForeignKey(IntegrationEndpoint,on_delete=models.CASCADE,related_name="deliveries")
    status=models.CharField(max_length=20,choices=RunStatus.choices,default=RunStatus.QUEUED); attempt_count=models.PositiveSmallIntegerField(default=0)
    response_code=models.PositiveSmallIntegerField(null=True,blank=True); response_body=models.TextField(blank=True); error_message=models.TextField(blank=True)
    next_retry_at=models.DateTimeField(null=True,blank=True); sent_at=models.DateTimeField(null=True,blank=True); delivered_at=models.DateTimeField(null=True,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: unique_together=(("event","endpoint"),); indexes=[models.Index(fields=("status","next_retry_at"))]

class DeadLetterEvent(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization=models.ForeignKey("organizations.Organization",on_delete=models.CASCADE,related_name="integration_dead_letters")
    event=models.ForeignKey(IntegrationEvent,null=True,on_delete=models.SET_NULL,related_name="dead_letter")
    delivery=models.ForeignKey(IntegrationDelivery,null=True,on_delete=models.SET_NULL,related_name="dead_letter")
    reason=models.TextField(); payload=models.JSONField(default=dict); retry_count=models.PositiveSmallIntegerField(default=0)
    reprocessed_at=models.DateTimeField(null=True,blank=True); resolved=models.BooleanField(default=False); created_at=models.DateTimeField(auto_now_add=True)

class SyncCursor(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    job=models.OneToOneField(IntegrationJob,on_delete=models.CASCADE,related_name="cursor")
    cursor=models.CharField(max_length=500,blank=True); last_source_timestamp=models.DateTimeField(null=True,blank=True)
    last_external_id=models.CharField(max_length=180,blank=True); records_synced=models.PositiveBigIntegerField(default=0); updated_at=models.DateTimeField(auto_now=True)

class ReconciliationRun(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization=models.ForeignKey("organizations.Organization",on_delete=models.CASCADE,related_name="reconciliation_runs")
    name=models.CharField(max_length=180); source_system=models.CharField(max_length=100); target_system=models.CharField(max_length=100)
    started_at=models.DateTimeField(null=True,blank=True); finished_at=models.DateTimeField(null=True,blank=True); status=models.CharField(max_length=20,choices=RunStatus.choices,default=RunStatus.QUEUED)
    source_count=models.PositiveIntegerField(default=0); target_count=models.PositiveIntegerField(default=0); matched_count=models.PositiveIntegerField(default=0); mismatch_count=models.PositiveIntegerField(default=0)
    summary=models.JSONField(default=dict,blank=True); created_at=models.DateTimeField(auto_now_add=True)

class ReconciliationItem(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    run=models.ForeignKey(ReconciliationRun,on_delete=models.CASCADE,related_name="items")
    external_key=models.CharField(max_length=180); status=models.CharField(max_length=30,default="MATCHED"); source_value=models.JSONField(default=dict); target_value=models.JSONField(default=dict)
    differences=models.JSONField(default=list); resolution=models.CharField(max_length=60,blank=True); resolved_at=models.DateTimeField(null=True,blank=True)

class FeatureFlag(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization=models.ForeignKey("organizations.Organization",null=True,blank=True,on_delete=models.CASCADE,related_name="feature_flags")
    key=models.SlugField(max_length=120); description=models.CharField(max_length=300,blank=True); enabled=models.BooleanField(default=False)
    rollout_percent=models.PositiveSmallIntegerField(default=100); environments=models.JSONField(default=list,blank=True); rules=models.JSONField(default=dict,blank=True)
    created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta: unique_together=(("organization","key"),)

class SystemConfiguration(models.Model):
    SENSITIVE=("secret","password","token","credential","private_key")
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization=models.ForeignKey("organizations.Organization",null=True,blank=True,on_delete=models.CASCADE,related_name="system_configurations")
    key=models.SlugField(max_length=160); value=models.JSONField(default=dict); value_type=models.CharField(max_length=30,default="json")
    environment=models.CharField(max_length=40,default="production"); description=models.TextField(blank=True); encrypted=models.BooleanField(default=False); version=models.PositiveIntegerField(default=1)
    updated_by=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.SET_NULL,related_name="updated_system_configs")
    created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta: unique_together=(("organization","key","environment"),)

class ReleaseRecord(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    version=models.CharField(max_length=80,unique=True); commit_reference=models.CharField(max_length=160,blank=True); environment=models.CharField(max_length=40,default="production")
    status=models.CharField(max_length=30,default="PLANNED"); release_notes=models.TextField(blank=True); migration_required=models.BooleanField(default=False)
    started_at=models.DateTimeField(null=True,blank=True); completed_at=models.DateTimeField(null=True,blank=True); deployed_by=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.SET_NULL,related_name="releases")
    created_at=models.DateTimeField(auto_now_add=True)

class ReleaseCheck(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    release=models.ForeignKey(ReleaseRecord,on_delete=models.CASCADE,related_name="checks")
    name=models.CharField(max_length=180); category=models.CharField(max_length=60); passed=models.BooleanField(default=False); required=models.BooleanField(default=True)
    duration_ms=models.PositiveIntegerField(default=0); details=models.JSONField(default=dict,blank=True); checked_at=models.DateTimeField(default=timezone.now)

class DataMigrationRun(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    name=models.CharField(max_length=180); version=models.CharField(max_length=80); status=models.CharField(max_length=20,choices=RunStatus.choices,default=RunStatus.QUEUED)
    started_at=models.DateTimeField(null=True,blank=True); finished_at=models.DateTimeField(null=True,blank=True); rows_read=models.PositiveBigIntegerField(default=0); rows_written=models.PositiveBigIntegerField(default=0); rows_failed=models.PositiveBigIntegerField(default=0)
    checksum_before=models.CharField(max_length=128,blank=True); checksum_after=models.CharField(max_length=128,blank=True); log=models.TextField(blank=True); created_at=models.DateTimeField(auto_now_add=True)

class IntegrationAuditEvent(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization=models.ForeignKey("organizations.Organization",null=True,on_delete=models.SET_NULL,related_name="integration_audits")
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.SET_NULL)
    action=models.CharField(max_length=100); resource_type=models.CharField(max_length=100); resource_id=models.CharField(max_length=120,blank=True)
    correlation_id=models.CharField(max_length=120,blank=True); details=models.JSONField(default=dict,blank=True); occurred_at=models.DateTimeField(default=timezone.now)
    class Meta: ordering=("-occurred_at",); indexes=[models.Index(fields=("organization","occurred_at")),models.Index(fields=("action","occurred_at"))]
