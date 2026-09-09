from rest_framework import serializers
from .models import MLModel, DatasetDefinition, Experiment, ModelVersion, PredictionRequest, FeatureDefinition, ModelDriftEvent

class MLModelSerializer(serializers.ModelSerializer):
    class Meta: model=MLModel; fields='__all__'
class DatasetSerializer(serializers.ModelSerializer):
    class Meta: model=DatasetDefinition; fields='__all__'
class ExperimentSerializer(serializers.ModelSerializer):
    class Meta: model=Experiment; fields='__all__'
class ModelVersionSerializer(serializers.ModelSerializer):
    class Meta: model=ModelVersion; fields='__all__'
class PredictionSerializer(serializers.ModelSerializer):
    class Meta: model=PredictionRequest; fields='__all__'
class FeatureSerializer(serializers.ModelSerializer):
    class Meta: model=FeatureDefinition; fields='__all__'
class DriftSerializer(serializers.ModelSerializer):
    class Meta: model=ModelDriftEvent; fields='__all__'
