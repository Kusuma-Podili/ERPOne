import uuid
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

class ProjectStatus(models.TextChoices):
    PLANNING='planning','Planning'; ACTIVE='active','Active'; ON_HOLD='on_hold','On Hold'; COMPLETED='completed','Completed'; CANCELLED='cancelled','Cancelled'; ARCHIVED='archived','Archived'
class ProjectPriority(models.TextChoices):
    LOW='low','Low'; MEDIUM='medium','Medium'; HIGH='high','High'; CRITICAL='critical','Critical'
class TaskStatus(models.TextChoices):
    BACKLOG='backlog','Backlog'; TODO='todo','To Do'; IN_PROGRESS='in_progress','In Progress'; BLOCKED='blocked','Blocked'; REVIEW='review','Review'; DONE='done','Done'; CANCELLED='cancelled','Cancelled'
class TaskPriority(models.TextChoices):
    LOW='low','Low'; MEDIUM='medium','Medium'; HIGH='high','High'; URGENT='urgent','Urgent'
class MemberRole(models.TextChoices):
    SPONSOR='sponsor','Sponsor'; MANAGER='manager','Project Manager'; LEAD='lead','Team Lead'; MEMBER='member','Member'; VIEWER='viewer','Viewer'; FINANCE='finance','Finance'
class MilestoneStatus(models.TextChoices):
    PLANNED='planned','Planned'; ACTIVE='active','Active'; COMPLETED='completed','Completed'; DELAYED='delayed','Delayed'; CANCELLED='cancelled','Cancelled'
class ExpenseStatus(models.TextChoices):
    DRAFT='draft','Draft'; SUBMITTED='submitted','Submitted'; APPROVED='approved','Approved'; REJECTED='rejected','Rejected'; REIMBURSED='reimbursed','Reimbursed'

class Project(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization=models.ForeignKey('organizations.Organization',on_delete=models.CASCADE,related_name='projects')
    code=models.CharField(max_length=40); name=models.CharField(max_length=180); description=models.TextField(blank=True)
    client=models.ForeignKey('crm.Account',on_delete=models.SET_NULL,null=True,blank=True,related_name='projects')
    project_manager=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='managed_projects')
    status=models.CharField(max_length=20,choices=ProjectStatus.choices,default=ProjectStatus.PLANNING,db_index=True)
    priority=models.CharField(max_length=20,choices=ProjectPriority.choices,default=ProjectPriority.MEDIUM,db_index=True)
    start_date=models.DateField(null=True,blank=True); target_end_date=models.DateField(null=True,blank=True); actual_end_date=models.DateField(null=True,blank=True)
    budget=models.DecimalField(max_digits=16,decimal_places=2,default=Decimal('0')); currency=models.CharField(max_length=10,default='INR')
    progress_percent=models.DecimalField(max_digits=5,decimal_places=2,default=Decimal('0')); tags=models.JSONField(default=list,blank=True)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,related_name='created_projects'); created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta:
        unique_together=('organization','code'); ordering=('-created_at',); indexes=[models.Index(fields=('organization','status')),models.Index(fields=('organization','priority'))]
    def __str__(self): return f'{self.code} - {self.name}'
    def clean(self):
        if self.target_end_date and self.start_date and self.target_end_date<self.start_date: raise ValidationError('Target end date cannot precede start date.')
        if not Decimal('0')<=self.progress_percent<=Decimal('100'): raise ValidationError('Progress must be between 0 and 100.')
        if self.budget<0: raise ValidationError('Budget cannot be negative.')
    @property
    def is_overdue(self): return bool(self.target_end_date and self.target_end_date<timezone.now().date() and self.status not in [ProjectStatus.COMPLETED,ProjectStatus.CANCELLED,ProjectStatus.ARCHIVED])
    @property
    def completion_ratio(self): return self.progress_percent/Decimal('100')

class ProjectMember(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); project=models.ForeignKey(Project,on_delete=models.CASCADE,related_name='members'); user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='project_memberships'); role=models.CharField(max_length=20,choices=MemberRole.choices,default=MemberRole.MEMBER); allocation_percent=models.DecimalField(max_digits=5,decimal_places=2,default=100); hourly_rate=models.DecimalField(max_digits=12,decimal_places=2,default=0); joined_on=models.DateField(default=timezone.now); left_on=models.DateField(null=True,blank=True); is_active=models.BooleanField(default=True)
    class Meta: unique_together=('project','user'); indexes=[models.Index(fields=('project','role')),models.Index(fields=('user','is_active'))]
    def clean(self):
        if not 0<=self.allocation_percent<=100: raise ValidationError('Allocation must be between 0 and 100 percent.')
        if self.left_on and self.left_on<self.joined_on: raise ValidationError('Leave date cannot precede join date.')

class ProjectMilestone(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); project=models.ForeignKey(Project,on_delete=models.CASCADE,related_name='milestones'); name=models.CharField(max_length=180); code=models.CharField(max_length=40); description=models.TextField(blank=True); due_date=models.DateField(null=True,blank=True); completed_date=models.DateField(null=True,blank=True); status=models.CharField(max_length=20,choices=MilestoneStatus.choices,default=MilestoneStatus.PLANNED); progress_percent=models.DecimalField(max_digits=5,decimal_places=2,default=0); owner=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='project_milestones')
    class Meta: unique_together=('project','code'); ordering=('due_date','name')

class ProjectTask(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); project=models.ForeignKey(Project,on_delete=models.CASCADE,related_name='tasks'); milestone=models.ForeignKey(ProjectMilestone,on_delete=models.SET_NULL,null=True,blank=True,related_name='tasks'); parent=models.ForeignKey('self',on_delete=models.SET_NULL,null=True,blank=True,related_name='subtasks'); title=models.CharField(max_length=220); task_key=models.CharField(max_length=50); description=models.TextField(blank=True); status=models.CharField(max_length=20,choices=TaskStatus.choices,default=TaskStatus.BACKLOG,db_index=True); priority=models.CharField(max_length=20,choices=TaskPriority.choices,default=TaskPriority.MEDIUM); assignee=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='assigned_project_tasks'); reporter=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='reported_project_tasks'); start_date=models.DateField(null=True,blank=True); due_date=models.DateField(null=True,blank=True); estimated_hours=models.DecimalField(max_digits=8,decimal_places=2,default=0); logged_hours=models.DecimalField(max_digits=8,decimal_places=2,default=0); progress_percent=models.DecimalField(max_digits=5,decimal_places=2,default=0); sort_order=models.PositiveIntegerField(default=0); labels=models.JSONField(default=list,blank=True); created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta: unique_together=('project','task_key'); ordering=('sort_order','due_date','title'); indexes=[models.Index(fields=('project','status')),models.Index(fields=('assignee','status'))]
    def clean(self):
        if self.due_date and self.start_date and self.due_date<self.start_date: raise ValidationError('Task due date cannot precede start date.')
        if not 0<=self.progress_percent<=100: raise ValidationError('Task progress must be between 0 and 100.')
        if self.estimated_hours<0 or self.logged_hours<0: raise ValidationError('Hours cannot be negative.')

class TaskDependency(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); predecessor=models.ForeignKey(ProjectTask,on_delete=models.CASCADE,related_name='successor_links'); successor=models.ForeignKey(ProjectTask,on_delete=models.CASCADE,related_name='predecessor_links'); dependency_type=models.CharField(max_length=20,choices=(('finish_start','Finish to Start'),('start_start','Start to Start'),('finish_finish','Finish to Finish'),('start_finish','Start to Finish')),default='finish_start'); lag_days=models.IntegerField(default=0); created_at=models.DateTimeField(auto_now_add=True)
    class Meta: unique_together=('predecessor','successor')
    def clean(self):
        if self.predecessor_id==self.successor_id: raise ValidationError('A task cannot depend on itself.')

class TaskComment(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); task=models.ForeignKey(ProjectTask,on_delete=models.CASCADE,related_name='comments'); author=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True); body=models.TextField(); is_internal=models.BooleanField(default=False); created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)

class TaskChecklistItem(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); task=models.ForeignKey(ProjectTask,on_delete=models.CASCADE,related_name='checklist'); title=models.CharField(max_length=220); is_completed=models.BooleanField(default=False); completed_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True); completed_at=models.DateTimeField(null=True,blank=True); sort_order=models.PositiveIntegerField(default=0)

class ProjectTimeEntry(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); project=models.ForeignKey(Project,on_delete=models.CASCADE,related_name='time_entries'); task=models.ForeignKey(ProjectTask,on_delete=models.SET_NULL,null=True,blank=True,related_name='time_entries'); user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='project_time_entries'); work_date=models.DateField(); hours=models.DecimalField(max_digits=7,decimal_places=2); description=models.TextField(blank=True); billable=models.BooleanField(default=True); approved=models.BooleanField(default=False); approved_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='approved_project_time'); created_at=models.DateTimeField(auto_now_add=True)
    class Meta: indexes=[models.Index(fields=('project','work_date')),models.Index(fields=('user','work_date'))]
    def clean(self):
        if self.hours<=0 or self.hours>24: raise ValidationError('Hours must be greater than zero and no more than 24.')

class ProjectExpense(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); project=models.ForeignKey(Project,on_delete=models.CASCADE,related_name='expenses'); task=models.ForeignKey(ProjectTask,on_delete=models.SET_NULL,null=True,blank=True,related_name='expenses'); submitted_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,related_name='submitted_project_expenses'); expense_date=models.DateField(); category=models.CharField(max_length=80); description=models.CharField(max_length=255); amount=models.DecimalField(max_digits=14,decimal_places=2); currency=models.CharField(max_length=10,default='INR'); status=models.CharField(max_length=20,choices=ExpenseStatus.choices,default=ExpenseStatus.DRAFT); approved_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='approved_project_expenses'); approved_at=models.DateTimeField(null=True,blank=True); created_at=models.DateTimeField(auto_now_add=True)
    def clean(self):
        if self.amount<=0: raise ValidationError('Expense amount must be positive.')

class ProjectBudgetLine(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); project=models.ForeignKey(Project,on_delete=models.CASCADE,related_name='budget_lines'); category=models.CharField(max_length=100); description=models.CharField(max_length=255,blank=True); planned_amount=models.DecimalField(max_digits=14,decimal_places=2); committed_amount=models.DecimalField(max_digits=14,decimal_places=2,default=0); actual_amount=models.DecimalField(max_digits=14,decimal_places=2,default=0); currency=models.CharField(max_length=10,default='INR')
    @property
    def remaining_amount(self): return self.planned_amount-self.actual_amount

class ProjectStatusHistory(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); project=models.ForeignKey(Project,on_delete=models.CASCADE,related_name='status_history'); from_status=models.CharField(max_length=20,blank=True); to_status=models.CharField(max_length=20); note=models.TextField(blank=True); changed_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True); changed_at=models.DateTimeField(auto_now_add=True)

class ProjectActivity(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); project=models.ForeignKey(Project,on_delete=models.CASCADE,related_name='activities'); actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True); action=models.CharField(max_length=80); entity_type=models.CharField(max_length=80,blank=True); entity_id=models.CharField(max_length=64,blank=True); summary=models.CharField(max_length=255); metadata=models.JSONField(default=dict,blank=True); created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=('-created_at',); indexes=[models.Index(fields=('project','created_at'))]
