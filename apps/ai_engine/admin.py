from django.contrib import admin
from .models import *
for model in [MLModel,DatasetDefinition,Experiment,ModelVersion,TrainingRun,PredictionRequest,FeatureDefinition,PredictionFeedback,ModelMonitoringMetric,ModelDriftEvent,ModelDeployment]:
    admin.site.register(model)
