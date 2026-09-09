import uuid
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

class MetricType(models.TextChoices):
    COUNT='count','Count'; SUM='sum','Sum'; AVERAGE='average','Average'; RATIO='ratio','Ratio'; PERCENTAGE='percentage','Percentage'; CURRENCY='currency','Currency'; DURATION='duration','Duration'
class DataSource(models.TextChoices):
    CRM='crm','CRM'; SALES='sales','Sales'; INVENTORY='inventory','Inventory'; PROCUREMENT='procurement','Procurement'; FINANCE='finance','Finance'; HR='hr','HR'; PAYROLL='payroll','Payroll'; PROJECTS='projects','Projects'; SUPPORT='support','Support'; ORGANIZATIONS='organizations','Organizations'; CUSTOM='custom','Custom'
class WidgetType(models.TextChoices):
    KPI='kpi','KPI'; TABLE='table','Table'; BAR='bar','Bar'; LINE='line','Line'; PIE='pie','Pie'; AREA='area','Area'; FUNNEL='funnel','Funnel'; GAUGE='gauge','Gauge'; NUMBER='number','Number'
class ReportStatus(models.TextChoices):
    DRAFT='draft','Draft'; ACTIVE='active','Active'; ARCHIVED='archived','Archived'
class ScheduleFrequency(models.TextChoices):
    DAILY='daily','Daily'; WEEKLY='weekly','Weekly'; MONTHLY='monthly','Monthly'; QUARTERLY='quarterly','Quarterly'

class MetricDefinition(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization=models.ForeignKey('organizations.Organization',on_delete=models.CASCADE,related_name='analytics_metrics')
    name=models.CharField(max_length=160); code=models.SlugField(max_length=80); description=models.TextField(blank=True)
    source=models.CharField(max_length=30,choices=DataSource.choices); metric_type=models.CharField(max_length=20,choices=MetricType.choices)
    expression=models.TextField(help_text='Safe analytics expression describing the calculation.')
    unit=models.CharField(max_length=30,blank=True); dimensions=models.JSONField(default=list,blank=True); filters=models.JSONField(default=dict,blank=True)
    is_active=models.BooleanField(default=True); created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='created_metrics')
    created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta: unique_together=('organization','code'); ordering=('name',); indexes=[models.Index(fields=('organization','source')),models.Index(fields=('organization','is_active'))]
    def clean(self):
        if not self.name.strip() or not self.code.strip(): raise ValidationError('Metric name and code are required.')

class KPI(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization=models.ForeignKey('organizations.Organization',on_delete=models.CASCADE,related_name='kpis'); metric=models.ForeignKey(MetricDefinition,on_delete=models.CASCADE,related_name='kpis')
    name=models.CharField(max_length=160); target=models.DecimalField(max_digits=18,decimal_places=4,default=Decimal('0')); warning_threshold=models.DecimalField(max_digits=18,decimal_places=4,null=True,blank=True); critical_threshold=models.DecimalField(max_digits=18,decimal_places=4,null=True,blank=True)
    owner=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='owned_kpis'); is_active=models.BooleanField(default=True); display_order=models.PositiveIntegerField(default=0); created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta: ordering=('display_order','name'); unique_together=('organization','name')
    @property
    def target_gap(self): return self.target

class Dashboard(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); organization=models.ForeignKey('organizations.Organization',on_delete=models.CASCADE,related_name='analytics_dashboards'); name=models.CharField(max_length=180); slug=models.SlugField(max_length=220); description=models.TextField(blank=True); is_default=models.BooleanField(default=False); is_shared=models.BooleanField(default=True); layout=models.JSONField(default=dict,blank=True); filters=models.JSONField(default=dict,blank=True); owner=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True); created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta: unique_together=('organization','slug'); ordering=('name',)

class DashboardPermission(models.Model):
    dashboard=models.ForeignKey(Dashboard,on_delete=models.CASCADE,related_name='permissions'); user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='dashboard_permissions'); can_view=models.BooleanField(default=True); can_edit=models.BooleanField(default=False); can_share=models.BooleanField(default=False)
    class Meta: unique_together=('dashboard','user')

class DashboardWidget(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); dashboard=models.ForeignKey(Dashboard,on_delete=models.CASCADE,related_name='widgets'); title=models.CharField(max_length=180); widget_type=models.CharField(max_length=20,choices=WidgetType.choices); metric=models.ForeignKey(MetricDefinition,on_delete=models.SET_NULL,null=True,blank=True,related_name='widgets'); configuration=models.JSONField(default=dict,blank=True); position=models.JSONField(default=dict,blank=True); refresh_seconds=models.PositiveIntegerField(default=300); is_visible=models.BooleanField(default=True); created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta: ordering=('id',); indexes=[models.Index(fields=('dashboard','widget_type'))]

class Report(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); organization=models.ForeignKey('organizations.Organization',on_delete=models.CASCADE,related_name='analytics_reports'); name=models.CharField(max_length=180); code=models.SlugField(max_length=100); description=models.TextField(blank=True); source=models.CharField(max_length=30,choices=DataSource.choices); status=models.CharField(max_length=20,choices=ReportStatus.choices,default=ReportStatus.DRAFT); columns=models.JSONField(default=list); filters=models.JSONField(default=dict,blank=True); group_by=models.JSONField(default=list,blank=True); order_by=models.JSONField(default=list,blank=True); aggregation=models.JSONField(default=dict,blank=True); owner=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True); created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta: unique_together=('organization','code'); ordering=('-updated_at',); indexes=[models.Index(fields=('organization','source')),models.Index(fields=('organization','status'))]

class ReportRun(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); report=models.ForeignKey(Report,on_delete=models.CASCADE,related_name='runs'); requested_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True); started_at=models.DateTimeField(default=timezone.now); completed_at=models.DateTimeField(null=True,blank=True); row_count=models.PositiveIntegerField(default=0); duration_ms=models.PositiveIntegerField(default=0); status=models.CharField(max_length=20,default='completed'); parameters=models.JSONField(default=dict,blank=True); result_snapshot=models.JSONField(default=dict,blank=True); error_message=models.TextField(blank=True)
    class Meta: ordering=('-started_at',); indexes=[models.Index(fields=('report','started_at'))]

class ReportSchedule(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); report=models.ForeignKey(Report,on_delete=models.CASCADE,related_name='schedules'); frequency=models.CharField(max_length=20,choices=ScheduleFrequency.choices); hour=models.PositiveSmallIntegerField(default=8); minute=models.PositiveSmallIntegerField(default=0); recipients=models.JSONField(default=list); export_format=models.CharField(max_length=10,default='csv'); is_active=models.BooleanField(default=True); next_run_at=models.DateTimeField(null=True,blank=True); last_run_at=models.DateTimeField(null=True,blank=True); created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True); created_at=models.DateTimeField(auto_now_add=True)
    class Meta: indexes=[models.Index(fields=('is_active','next_run_at'))]

class AnalyticsSnapshot(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); organization=models.ForeignKey('organizations.Organization',on_delete=models.CASCADE,related_name='analytics_snapshots'); metric=models.ForeignKey(MetricDefinition,on_delete=models.CASCADE,related_name='snapshots'); captured_for=models.DateTimeField(); value=models.DecimalField(max_digits=20,decimal_places=6,default=0); dimensions=models.JSONField(default=dict,blank=True); metadata=models.JSONField(default=dict,blank=True); created_at=models.DateTimeField(auto_now_add=True)
    class Meta: unique_together=('metric','captured_for'); ordering=('-captured_for',); indexes=[models.Index(fields=('organization','captured_for')),models.Index(fields=('metric','captured_for'))]

class AnalyticsAlert(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); organization=models.ForeignKey('organizations.Organization',on_delete=models.CASCADE,related_name='analytics_alerts'); kpi=models.ForeignKey(KPI,on_delete=models.CASCADE,related_name='alerts'); name=models.CharField(max_length=180); operator=models.CharField(max_length=10,default='lt'); threshold=models.DecimalField(max_digits=18,decimal_places=4); recipients=models.JSONField(default=list); is_active=models.BooleanField(default=True); last_triggered_at=models.DateTimeField(null=True,blank=True); created_at=models.DateTimeField(auto_now_add=True)

class AnalyticsAuditEvent(models.Model):
    organization=models.ForeignKey('organizations.Organization',on_delete=models.CASCADE,related_name='analytics_audit_events'); actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True); action=models.CharField(max_length=60); entity_type=models.CharField(max_length=60); entity_id=models.CharField(max_length=80); details=models.JSONField(default=dict,blank=True); created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=('-created_at',); indexes=[models.Index(fields=('organization','created_at')),models.Index(fields=('entity_type','entity_id'))]
