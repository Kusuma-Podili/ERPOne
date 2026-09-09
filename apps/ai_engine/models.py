import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone

class ProblemType(models.TextChoices):
    REGRESSION='regression','Regression'; CLASSIFICATION='classification','Classification'; FORECASTING='forecasting','Forecasting'; CLUSTERING='clustering','Clustering'; ANOMALY='anomaly','Anomaly Detection'; RANKING='ranking','Ranking'
class ModelStatus(models.TextChoices):
    DRAFT='draft','Draft'; TRAINING='training','Training'; READY='ready','Ready'; DEPLOYED='deployed','Deployed'; RETIRED='retired','Retired'; FAILED='failed','Failed'
class RunStatus(models.TextChoices):
    QUEUED='queued','Queued'; RUNNING='running','Running'; COMPLETED='completed','Completed'; FAILED='failed','Failed'
class PredictionStatus(models.TextChoices):
    SUCCESS='success','Success'; FAILED='failed','Failed'; REVIEW='review','Needs Review'

class MLModel(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization=models.ForeignKey('organizations.Organization',on_delete=models.CASCADE,related_name='ml_models')
    name=models.CharField(max_length=180); code=models.SlugField(max_length=100); description=models.TextField(blank=True)
    problem_type=models.CharField(max_length=30,choices=ProblemType.choices); target_field=models.CharField(max_length=120,blank=True)
    source_module=models.CharField(max_length=60); feature_fields=models.JSONField(default=list); configuration=models.JSONField(default=dict,blank=True)
    status=models.CharField(max_length=20,choices=ModelStatus.choices,default=ModelStatus.DRAFT)
    owner=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='owned_ml_models')
    created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta:
        unique_together=('organization','code'); ordering=('name',)
        indexes=[models.Index(fields=('organization','problem_type')),models.Index(fields=('organization','status'))]

class DatasetDefinition(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization=models.ForeignKey('organizations.Organization',on_delete=models.CASCADE,related_name='ml_datasets')
    name=models.CharField(max_length=180); code=models.SlugField(max_length=100); source_module=models.CharField(max_length=60)
    query_definition=models.JSONField(default=dict); feature_schema=models.JSONField(default=list); row_count=models.PositiveIntegerField(default=0)
    checksum=models.CharField(max_length=128,blank=True); is_active=models.BooleanField(default=True); created_at=models.DateTimeField(auto_now_add=True)
    class Meta: unique_together=('organization','code'); ordering=('-created_at',)

class Experiment(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization=models.ForeignKey('organizations.Organization',on_delete=models.CASCADE,related_name='ml_experiments')
    model=models.ForeignKey(MLModel,on_delete=models.CASCADE,related_name='experiments'); dataset=models.ForeignKey(DatasetDefinition,on_delete=models.SET_NULL,null=True,blank=True,related_name='experiments')
    name=models.CharField(max_length=180); parameters=models.JSONField(default=dict); metrics=models.JSONField(default=dict); status=models.CharField(max_length=20,choices=RunStatus.choices,default=RunStatus.QUEUED)
    started_at=models.DateTimeField(null=True,blank=True); completed_at=models.DateTimeField(null=True,blank=True); error_message=models.TextField(blank=True)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True); created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=('-created_at',)

class ModelVersion(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    model=models.ForeignKey(MLModel,on_delete=models.CASCADE,related_name='versions'); version=models.PositiveIntegerField(); artifact_path=models.CharField(max_length=500,blank=True)
    algorithm=models.CharField(max_length=100); hyperparameters=models.JSONField(default=dict); metrics=models.JSONField(default=dict); feature_importance=models.JSONField(default=dict)
    training_rows=models.PositiveIntegerField(default=0); validation_rows=models.PositiveIntegerField(default=0); is_deployed=models.BooleanField(default=False)
    trained_at=models.DateTimeField(default=timezone.now); created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True)
    class Meta: unique_together=('model','version'); ordering=('-version',); indexes=[models.Index(fields=('model','is_deployed'))]

class TrainingRun(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); model=models.ForeignKey(MLModel,on_delete=models.CASCADE,related_name='training_runs'); experiment=models.ForeignKey(Experiment,on_delete=models.SET_NULL,null=True,blank=True,related_name='training_runs')
    version=models.ForeignKey(ModelVersion,on_delete=models.SET_NULL,null=True,blank=True,related_name='training_runs'); status=models.CharField(max_length=20,choices=RunStatus.choices,default=RunStatus.QUEUED)
    parameters=models.JSONField(default=dict); metrics=models.JSONField(default=dict); logs=models.JSONField(default=list); started_at=models.DateTimeField(null=True,blank=True); completed_at=models.DateTimeField(null=True,blank=True); error_message=models.TextField(blank=True)
    created_at=models.DateTimeField(auto_now_add=True); created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True)
    class Meta: ordering=('-created_at',)

class PredictionRequest(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); model=models.ForeignKey(MLModel,on_delete=models.CASCADE,related_name='prediction_requests'); version=models.ForeignKey(ModelVersion,on_delete=models.SET_NULL,null=True,blank=True,related_name='predictions')
    features=models.JSONField(default=dict); prediction=models.JSONField(default=dict); probability=models.DecimalField(max_digits=12,decimal_places=8,null=True,blank=True); status=models.CharField(max_length=20,choices=PredictionStatus.choices,default=PredictionStatus.SUCCESS)
    latency_ms=models.PositiveIntegerField(default=0); requested_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True); created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=('-created_at',); indexes=[models.Index(fields=('model','created_at')),models.Index(fields=('status','created_at'))]

class FeatureDefinition(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); organization=models.ForeignKey('organizations.Organization',on_delete=models.CASCADE,related_name='ml_features'); name=models.CharField(max_length=160); code=models.SlugField(max_length=100); source_field=models.CharField(max_length=160); transform=models.CharField(max_length=80,default='identity'); configuration=models.JSONField(default=dict); is_active=models.BooleanField(default=True); created_at=models.DateTimeField(auto_now_add=True)
    class Meta: unique_together=('organization','code')

class PredictionFeedback(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); prediction=models.OneToOneField(PredictionRequest,on_delete=models.CASCADE,related_name='feedback'); actual_value=models.JSONField(default=dict); is_correct=models.BooleanField(null=True); rating=models.PositiveSmallIntegerField(null=True,blank=True); notes=models.TextField(blank=True); reviewed_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True); reviewed_at=models.DateTimeField(null=True,blank=True)

class ModelMonitoringMetric(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); model=models.ForeignKey(MLModel,on_delete=models.CASCADE,related_name='monitoring_metrics'); name=models.CharField(max_length=100); value=models.DecimalField(max_digits=20,decimal_places=8); baseline=models.DecimalField(max_digits=20,decimal_places=8,null=True,blank=True); threshold=models.DecimalField(max_digits=20,decimal_places=8,null=True,blank=True); window_start=models.DateTimeField(); window_end=models.DateTimeField(); metadata=models.JSONField(default=dict); created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=('-window_end',); indexes=[models.Index(fields=('model','name','window_end'))]

class ModelDriftEvent(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); model=models.ForeignKey(MLModel,on_delete=models.CASCADE,related_name='drift_events'); feature=models.CharField(max_length=160); score=models.DecimalField(max_digits=18,decimal_places=8); threshold=models.DecimalField(max_digits=18,decimal_places=8); detected_at=models.DateTimeField(default=timezone.now); resolved_at=models.DateTimeField(null=True,blank=True); details=models.JSONField(default=dict); is_resolved=models.BooleanField(default=False)
    class Meta: ordering=('-detected_at',)

class ModelDeployment(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); model=models.ForeignKey(MLModel,on_delete=models.CASCADE,related_name='deployments'); version=models.ForeignKey(ModelVersion,on_delete=models.CASCADE,related_name='deployments'); environment=models.CharField(max_length=40,default='production'); endpoint_name=models.SlugField(max_length=120); replicas=models.PositiveIntegerField(default=1); traffic_percent=models.PositiveSmallIntegerField(default=100); active=models.BooleanField(default=True); deployed_at=models.DateTimeField(default=timezone.now); retired_at=models.DateTimeField(null=True,blank=True)
    class Meta: indexes=[models.Index(fields=('environment','active'))]
