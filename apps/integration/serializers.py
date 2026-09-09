from rest_framework import serializers
from .models import IntegrationConnection, IntegrationJob, IntegrationEvent, DeadLetterEvent, ReconciliationRun, ReleaseRecord, FeatureFlag
class ConnectionSerializer(serializers.ModelSerializer):
    class Meta: model=IntegrationConnection; fields="__all__"
class JobSerializer(serializers.ModelSerializer):
    class Meta: model=IntegrationJob; fields="__all__"
class EventSerializer(serializers.ModelSerializer):
    class Meta: model=IntegrationEvent; fields="__all__"
class DeadLetterSerializer(serializers.ModelSerializer):
    class Meta: model=DeadLetterEvent; fields="__all__"
class ReconciliationSerializer(serializers.ModelSerializer):
    class Meta: model=ReconciliationRun; fields="__all__"
class ReleaseSerializer(serializers.ModelSerializer):
    class Meta: model=ReleaseRecord; fields="__all__"
class FeatureFlagSerializer(serializers.ModelSerializer):
    class Meta: model=FeatureFlag; fields="__all__"
