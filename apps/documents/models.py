import hashlib, uuid
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

class DocumentStatus(models.TextChoices):
    DRAFT='draft','Draft'; PENDING='pending','Pending Approval'; APPROVED='approved','Approved'; REJECTED='rejected','Rejected'; ARCHIVED='archived','Archived'; EXPIRED='expired','Expired'
class DocumentVisibility(models.TextChoices):
    PRIVATE='private','Private'; ORGANIZATION='organization','Organization'; SHARED='shared','Shared'
class ApprovalStatus(models.TextChoices):
    PENDING='pending','Pending'; APPROVED='approved','Approved'; REJECTED='rejected','Rejected'; CHANGES='changes','Changes Requested'; SKIPPED='skipped','Skipped'

class DocumentCategory(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); organization=models.ForeignKey('organizations.Organization',on_delete=models.CASCADE,related_name='document_categories'); name=models.CharField(max_length=120); code=models.SlugField(max_length=60); description=models.TextField(blank=True); parent=models.ForeignKey('self',null=True,blank=True,on_delete=models.SET_NULL,related_name='children'); retention_days=models.PositiveIntegerField(default=0); requires_approval=models.BooleanField(default=False); is_active=models.BooleanField(default=True); created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta: unique_together=('organization','code'); ordering=('name',)

class DocumentFolder(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); organization=models.ForeignKey('organizations.Organization',on_delete=models.CASCADE,related_name='document_folders'); name=models.CharField(max_length=160); path=models.CharField(max_length=500); parent=models.ForeignKey('self',null=True,blank=True,on_delete=models.CASCADE,related_name='children'); owner=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL); is_system=models.BooleanField(default=False); created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta: unique_together=('organization','path'); ordering=('path',)

class Document(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); organization=models.ForeignKey('organizations.Organization',on_delete=models.CASCADE,related_name='documents'); title=models.CharField(max_length=240); document_number=models.CharField(max_length=80,blank=True,db_index=True); description=models.TextField(blank=True); category=models.ForeignKey(DocumentCategory,null=True,blank=True,on_delete=models.SET_NULL,related_name='documents'); folder=models.ForeignKey(DocumentFolder,null=True,blank=True,on_delete=models.SET_NULL,related_name='documents'); owner=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL,related_name='owned_documents'); status=models.CharField(max_length=20,choices=DocumentStatus.choices,default=DocumentStatus.DRAFT,db_index=True); visibility=models.CharField(max_length=20,choices=DocumentVisibility.choices,default=DocumentVisibility.PRIVATE); tags=models.JSONField(default=list,blank=True); metadata=models.JSONField(default=dict,blank=True); current_version=models.PositiveIntegerField(default=0); expires_at=models.DateTimeField(null=True,blank=True); archived_at=models.DateTimeField(null=True,blank=True); created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    content_type=models.ForeignKey(ContentType,null=True,blank=True,on_delete=models.SET_NULL); object_id=models.CharField(max_length=80,blank=True); linked_object=GenericForeignKey('content_type','object_id')
    class Meta: unique_together=('organization','document_number'); ordering=('-updated_at',); indexes=[models.Index(fields=('organization','status')),models.Index(fields=('organization','category')),models.Index(fields=('organization','folder')),models.Index(fields=('organization','expires_at'))]
    def next_number(self): return f'DOC-{timezone.now():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}'
    def save(self,*args,**kwargs):
        if not self.document_number: self.document_number=self.next_number()
        super().save(*args,**kwargs)

class DocumentVersion(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); document=models.ForeignKey(Document,on_delete=models.CASCADE,related_name='versions'); version=models.PositiveIntegerField(); file=models.FileField(upload_to='documents/%Y/%m/'); original_filename=models.CharField(max_length=255); mime_type=models.CharField(max_length=120,blank=True); file_size=models.BigIntegerField(default=0,validators=[MinValueValidator(0)]); checksum=models.CharField(max_length=64,blank=True); change_summary=models.TextField(blank=True); uploaded_by=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL); created_at=models.DateTimeField(auto_now_add=True); is_current=models.BooleanField(default=False)
    class Meta: unique_together=('document','version'); ordering=('-version',); indexes=[models.Index(fields=('document','is_current'))]
    def calculate_checksum(self):
        if self.file and self.file.storage.exists(self.file.name):
            h=hashlib.sha256()
            for chunk in self.file.chunks(): h.update(chunk)
            self.checksum=h.hexdigest()
        return self.checksum

class DocumentPermission(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); document=models.ForeignKey(Document,on_delete=models.CASCADE,related_name='permissions'); user=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.CASCADE,related_name='document_permissions'); role_code=models.CharField(max_length=80,blank=True); can_view=models.BooleanField(default=True); can_download=models.BooleanField(default=True); can_edit=models.BooleanField(default=False); can_share=models.BooleanField(default=False); can_approve=models.BooleanField(default=False); expires_at=models.DateTimeField(null=True,blank=True); created_at=models.DateTimeField(auto_now_add=True)
    class Meta: unique_together=('document','user','role_code')
    def active(self): return not self.expires_at or self.expires_at>timezone.now()

class DocumentShare(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); document=models.ForeignKey(Document,on_delete=models.CASCADE,related_name='shares'); shared_by=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.SET_NULL,related_name='document_shares'); recipient_email=models.EmailField(); token=models.UUIDField(default=uuid.uuid4,unique=True,editable=False); can_download=models.BooleanField(default=True); expires_at=models.DateTimeField(null=True,blank=True); accessed_at=models.DateTimeField(null=True,blank=True); revoked_at=models.DateTimeField(null=True,blank=True); created_at=models.DateTimeField(auto_now_add=True)
    def usable(self): return not self.revoked_at and (not self.expires_at or self.expires_at>timezone.now())

class DocumentApprovalWorkflow(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); organization=models.ForeignKey('organizations.Organization',on_delete=models.CASCADE,related_name='document_approval_workflows'); name=models.CharField(max_length=160); code=models.SlugField(max_length=80); description=models.TextField(blank=True); is_active=models.BooleanField(default=True); created_at=models.DateTimeField(auto_now_add=True)
    class Meta: unique_together=('organization','code')
class DocumentApprovalStep(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); workflow=models.ForeignKey(DocumentApprovalWorkflow,on_delete=models.CASCADE,related_name='steps'); sequence=models.PositiveIntegerField(); approver_role=models.CharField(max_length=100,blank=True); approver_user=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL,related_name='document_approval_steps'); required=models.BooleanField(default=True); created_at=models.DateTimeField(auto_now_add=True)
    class Meta: unique_together=('workflow','sequence'); ordering=('sequence',)
class DocumentApproval(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); document=models.ForeignKey(Document,on_delete=models.CASCADE,related_name='approvals'); workflow=models.ForeignKey(DocumentApprovalWorkflow,on_delete=models.SET_NULL,null=True,related_name='approvals'); step=models.ForeignKey(DocumentApprovalStep,on_delete=models.SET_NULL,null=True,related_name='approvals'); approver=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL,related_name='document_approvals'); status=models.CharField(max_length=20,choices=ApprovalStatus.choices,default=ApprovalStatus.PENDING); comments=models.TextField(blank=True); decided_at=models.DateTimeField(null=True,blank=True); created_at=models.DateTimeField(auto_now_add=True)

class DocumentComment(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); document=models.ForeignKey(Document,on_delete=models.CASCADE,related_name='comments'); author=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.SET_NULL); body=models.TextField(); version=models.PositiveIntegerField(null=True,blank=True); parent=models.ForeignKey('self',null=True,blank=True,on_delete=models.CASCADE,related_name='replies'); is_resolved=models.BooleanField(default=False); created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
class DocumentTag(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); organization=models.ForeignKey('organizations.Organization',on_delete=models.CASCADE,related_name='document_tags'); name=models.CharField(max_length=80); color=models.CharField(max_length=20,default='neutral'); created_at=models.DateTimeField(auto_now_add=True)
    class Meta: unique_together=('organization','name')
class DocumentAccessLog(models.Model):
    ACTIONS=[('view','View'),('download','Download'),('upload','Upload'),('share','Share'),('approve','Approve'),('reject','Reject'),('restore','Restore'),('archive','Archive'),('delete','Delete')]
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); organization=models.ForeignKey('organizations.Organization',on_delete=models.CASCADE,related_name='document_access_logs'); document=models.ForeignKey(Document,on_delete=models.CASCADE,related_name='access_logs'); user=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL); action=models.CharField(max_length=30,choices=ACTIONS); ip_address=models.GenericIPAddressField(null=True,blank=True); user_agent=models.TextField(blank=True); details=models.JSONField(default=dict,blank=True); created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering=('-created_at',)
        indexes=[models.Index(fields=('organization','created_at')),models.Index(fields=('document','created_at'))]
class DocumentRetentionPolicy(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); organization=models.ForeignKey('organizations.Organization',on_delete=models.CASCADE,related_name='document_retention_policies'); name=models.CharField(max_length=160); category=models.ForeignKey(DocumentCategory,null=True,blank=True,on_delete=models.CASCADE,related_name='retention_policies'); retention_days=models.PositiveIntegerField(); archive_after_days=models.PositiveIntegerField(default=0); delete_after_days=models.PositiveIntegerField(default=0); legal_hold_supported=models.BooleanField(default=True); is_active=models.BooleanField(default=True); created_at=models.DateTimeField(auto_now_add=True)
class DocumentRetentionEvent(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); document=models.ForeignKey(Document,on_delete=models.CASCADE,related_name='retention_events'); policy=models.ForeignKey(DocumentRetentionPolicy,null=True,on_delete=models.SET_NULL,related_name='events'); event_type=models.CharField(max_length=30); scheduled_for=models.DateTimeField(); executed_at=models.DateTimeField(null=True,blank=True); success=models.BooleanField(default=False); details=models.JSONField(default=dict); created_at=models.DateTimeField(auto_now_add=True)
class DocumentTemplate(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); organization=models.ForeignKey('organizations.Organization',on_delete=models.CASCADE,related_name='document_templates'); name=models.CharField(max_length=160); code=models.SlugField(max_length=80); description=models.TextField(blank=True); category=models.ForeignKey(DocumentCategory,null=True,blank=True,on_delete=models.SET_NULL,related_name='templates'); template_body=models.TextField(); variables=models.JSONField(default=list); version=models.PositiveIntegerField(default=1); is_active=models.BooleanField(default=True); created_by=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.SET_NULL); created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta: unique_together=('organization','code','version')
