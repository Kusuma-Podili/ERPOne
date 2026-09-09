import uuid
from datetime import timedelta
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

class TicketStatus(models.TextChoices):
    OPEN='open','Open'; IN_PROGRESS='in_progress','In Progress'; WAITING='waiting','Waiting for Customer'; RESOLVED='resolved','Resolved'; CLOSED='closed','Closed'; REOPENED='reopened','Reopened'
class TicketPriority(models.TextChoices):
    LOW='low','Low'; NORMAL='normal','Normal'; HIGH='high','High'; URGENT='urgent','Urgent'; CRITICAL='critical','Critical'
class TicketSource(models.TextChoices):
    PORTAL='portal','Customer Portal'; EMAIL='email','Email'; PHONE='phone','Phone'; CHAT='chat','Chat'; INTERNAL='internal','Internal'
class TicketType(models.TextChoices):
    INCIDENT='incident','Incident'; REQUEST='request','Service Request'; QUESTION='question','Question'; PROBLEM='problem','Problem'; COMPLAINT='complaint','Complaint'
class SlaStatus(models.TextChoices):
    ACTIVE='active','Active'; PAUSED='paused','Paused'; BREACHED='breached','Breached'; MET='met','Met'

class SupportCategory(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization=models.ForeignKey('organizations.Organization',on_delete=models.CASCADE,related_name='support_categories')
    name=models.CharField(max_length=120); code=models.CharField(max_length=30); description=models.TextField(blank=True)
    parent=models.ForeignKey('self',on_delete=models.SET_NULL,null=True,blank=True,related_name='children')
    is_active=models.BooleanField(default=True); default_priority=models.CharField(max_length=20,choices=TicketPriority.choices,default=TicketPriority.NORMAL)
    created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta:
        unique_together=('organization','code'); ordering=('name',)
        indexes=[models.Index(fields=('organization','is_active')),models.Index(fields=('organization','parent'))]
    def clean(self):
        if self.parent_id==self.id: raise ValidationError('A category cannot be its own parent.')

class SupportTeam(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization=models.ForeignKey('organizations.Organization',on_delete=models.CASCADE,related_name='support_teams')
    name=models.CharField(max_length=120); code=models.CharField(max_length=30); description=models.TextField(blank=True)
    manager=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='managed_support_teams')
    email=models.EmailField(blank=True); is_active=models.BooleanField(default=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: unique_together=('organization','code'); ordering=('name',)

class SupportTeamMember(models.Model):
    team=models.ForeignKey(SupportTeam,on_delete=models.CASCADE,related_name='members'); user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='support_team_memberships')
    is_lead=models.BooleanField(default=False); can_assign=models.BooleanField(default=True); joined_at=models.DateTimeField(auto_now_add=True); is_active=models.BooleanField(default=True)
    class Meta: unique_together=('team','user')

class SlaPolicy(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization=models.ForeignKey('organizations.Organization',on_delete=models.CASCADE,related_name='support_sla_policies')
    name=models.CharField(max_length=120); description=models.TextField(blank=True); priority=models.CharField(max_length=20,choices=TicketPriority.choices,default=TicketPriority.NORMAL)
    first_response_minutes=models.PositiveIntegerField(default=240); resolution_minutes=models.PositiveIntegerField(default=1440); business_hours_only=models.BooleanField(default=True); is_active=models.BooleanField(default=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: unique_together=('organization','name')
    def deadlines(self, start=None):
        start=start or timezone.now(); return start+timedelta(minutes=self.first_response_minutes),start+timedelta(minutes=self.resolution_minutes)

class SupportTicket(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization=models.ForeignKey('organizations.Organization',on_delete=models.CASCADE,related_name='support_tickets')
    number=models.CharField(max_length=40,db_index=True); subject=models.CharField(max_length=240); description=models.TextField()
    customer=models.ForeignKey('crm.Account',on_delete=models.SET_NULL,null=True,blank=True,related_name='support_tickets')
    requester=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='requested_support_tickets')
    category=models.ForeignKey(SupportCategory,on_delete=models.SET_NULL,null=True,blank=True,related_name='tickets')
    team=models.ForeignKey(SupportTeam,on_delete=models.SET_NULL,null=True,blank=True,related_name='tickets')
    assignee=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='assigned_support_tickets')
    sla_policy=models.ForeignKey(SlaPolicy,on_delete=models.SET_NULL,null=True,blank=True,related_name='tickets')
    status=models.CharField(max_length=20,choices=TicketStatus.choices,default=TicketStatus.OPEN,db_index=True)
    priority=models.CharField(max_length=20,choices=TicketPriority.choices,default=TicketPriority.NORMAL,db_index=True)
    source=models.CharField(max_length=20,choices=TicketSource.choices,default=TicketSource.PORTAL); ticket_type=models.CharField(max_length=20,choices=TicketType.choices,default=TicketType.INCIDENT)
    tags=models.JSONField(default=list,blank=True); due_at=models.DateTimeField(null=True,blank=True); first_response_at=models.DateTimeField(null=True,blank=True); resolved_at=models.DateTimeField(null=True,blank=True); closed_at=models.DateTimeField(null=True,blank=True)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='created_support_tickets')
    created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta:
        unique_together=('organization','number'); ordering=('-created_at',)
        indexes=[models.Index(fields=('organization','status')),models.Index(fields=('organization','priority')),models.Index(fields=('organization','assignee','status')),models.Index(fields=('organization','created_at'))]
    def save(self,*args,**kwargs):
        if not self.number:
            self.number=f'TKT-{timezone.now():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}'
        if self.sla_policy_id and not self.due_at:
            _,self.due_at=self.sla_policy.deadlines(self.created_at or timezone.now())
        super().save(*args,**kwargs)
    @property
    def is_overdue(self):
        return bool(self.due_at and timezone.now()>self.due_at and self.status not in {TicketStatus.RESOLVED,TicketStatus.CLOSED})
    @property
    def response_time_minutes(self):
        if not self.first_response_at:return None
        return int((self.first_response_at-self.created_at).total_seconds()/60)
    @property
    def age_hours(self): return round((timezone.now()-self.created_at).total_seconds()/3600,2)

class TicketMessage(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); ticket=models.ForeignKey(SupportTicket,on_delete=models.CASCADE,related_name='messages')
    author=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True); body=models.TextField(); is_internal=models.BooleanField(default=False); channel=models.CharField(max_length=20,choices=TicketSource.choices,default=TicketSource.PORTAL)
    created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta: ordering=('created_at',); indexes=[models.Index(fields=('ticket','created_at'))]

class TicketAttachment(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); ticket=models.ForeignKey(SupportTicket,on_delete=models.CASCADE,related_name='attachments'); message=models.ForeignKey(TicketMessage,on_delete=models.CASCADE,null=True,blank=True,related_name='attachments')
    file=models.FileField(upload_to='support/tickets/%Y/%m/'); original_name=models.CharField(max_length=255); content_type=models.CharField(max_length=120,blank=True); size_bytes=models.PositiveBigIntegerField(default=0); uploaded_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True); created_at=models.DateTimeField(auto_now_add=True)

class TicketAssignmentHistory(models.Model):
    ticket=models.ForeignKey(SupportTicket,on_delete=models.CASCADE,related_name='assignment_history'); previous_assignee=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='+'); new_assignee=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='+'); previous_team=models.ForeignKey(SupportTeam,on_delete=models.SET_NULL,null=True,blank=True,related_name='+'); new_team=models.ForeignKey(SupportTeam,on_delete=models.SET_NULL,null=True,blank=True,related_name='+'); changed_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='+'); reason=models.CharField(max_length=255,blank=True); changed_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=('-changed_at',)

class TicketStatusHistory(models.Model):
    ticket=models.ForeignKey(SupportTicket,on_delete=models.CASCADE,related_name='status_history'); from_status=models.CharField(max_length=20,blank=True); to_status=models.CharField(max_length=20); changed_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True); note=models.TextField(blank=True); changed_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=('-changed_at',)

class TicketSlaEvent(models.Model):
    ticket=models.ForeignKey(SupportTicket,on_delete=models.CASCADE,related_name='sla_events'); event_type=models.CharField(max_length=40); status=models.CharField(max_length=20,choices=SlaStatus.choices,default=SlaStatus.ACTIVE); target_at=models.DateTimeField(null=True,blank=True); occurred_at=models.DateTimeField(auto_now_add=True); notes=models.TextField(blank=True)
    class Meta: ordering=('-occurred_at',)

class TicketSatisfaction(models.Model):
    ticket=models.OneToOneField(SupportTicket,on_delete=models.CASCADE,related_name='satisfaction'); rating=models.PositiveSmallIntegerField(); comment=models.TextField(blank=True); submitted_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True); submitted_at=models.DateTimeField(auto_now_add=True)
    def clean(self):
        if not 1<=self.rating<=5: raise ValidationError('Rating must be between 1 and 5.')

class KnowledgeBaseCategory(models.Model):
    organization=models.ForeignKey('organizations.Organization',on_delete=models.CASCADE,related_name='knowledge_categories'); name=models.CharField(max_length=120); description=models.TextField(blank=True); parent=models.ForeignKey('self',on_delete=models.SET_NULL,null=True,blank=True,related_name='children'); is_active=models.BooleanField(default=True)
    class Meta: unique_together=('organization','name')

class KnowledgeArticle(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); organization=models.ForeignKey('organizations.Organization',on_delete=models.CASCADE,related_name='knowledge_articles'); category=models.ForeignKey(KnowledgeBaseCategory,on_delete=models.SET_NULL,null=True,blank=True,related_name='articles'); title=models.CharField(max_length=240); slug=models.SlugField(max_length=260); summary=models.CharField(max_length=500,blank=True); content=models.TextField(); tags=models.JSONField(default=list,blank=True); is_published=models.BooleanField(default=False); view_count=models.PositiveIntegerField(default=0); helpful_count=models.PositiveIntegerField(default=0); not_helpful_count=models.PositiveIntegerField(default=0); author=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True); published_at=models.DateTimeField(null=True,blank=True); created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta: unique_together=('organization','slug'); indexes=[models.Index(fields=('organization','is_published')),models.Index(fields=('organization','category'))]
    def publish(self): self.is_published=True; self.published_at=self.published_at or timezone.now(); self.save(update_fields=['is_published','published_at','updated_at'])
    @property
    def helpful_ratio(self):
        total=self.helpful_count+self.not_helpful_count
        return round(self.helpful_count/total*100,1) if total else 0

class CannedResponse(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); organization=models.ForeignKey('organizations.Organization',on_delete=models.CASCADE,related_name='canned_support_responses'); name=models.CharField(max_length=160); shortcut=models.CharField(max_length=40); body=models.TextField(); category=models.ForeignKey(SupportCategory,on_delete=models.SET_NULL,null=True,blank=True,related_name='canned_responses'); is_active=models.BooleanField(default=True); created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True); created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta: unique_together=('organization','shortcut'); ordering=('name',)

class SupportEscalationRule(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); organization=models.ForeignKey('organizations.Organization',on_delete=models.CASCADE,related_name='support_escalation_rules'); name=models.CharField(max_length=160); priority=models.CharField(max_length=20,choices=TicketPriority.choices,blank=True); category=models.ForeignKey(SupportCategory,on_delete=models.SET_NULL,null=True,blank=True); after_minutes=models.PositiveIntegerField(default=60); target_team=models.ForeignKey(SupportTeam,on_delete=models.SET_NULL,null=True,blank=True); target_user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True); is_active=models.BooleanField(default=True); created_at=models.DateTimeField(auto_now_add=True)

class SupportBusinessHour(models.Model):
    organization=models.ForeignKey('organizations.Organization',on_delete=models.CASCADE,related_name='support_business_hours'); weekday=models.PositiveSmallIntegerField(); start_time=models.TimeField(); end_time=models.TimeField(); is_working_day=models.BooleanField(default=True)
    class Meta: unique_together=('organization','weekday'); ordering=('weekday',)
    def clean(self):
        if not 0<=self.weekday<=6: raise ValidationError('Weekday must be 0 through 6.')
        if self.is_working_day and self.start_time>=self.end_time: raise ValidationError('End time must be after start time.')
