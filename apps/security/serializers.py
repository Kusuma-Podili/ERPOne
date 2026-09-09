from rest_framework import serializers
from .models import *

class SecurityEventSerializer(serializers.ModelSerializer):
    class Meta: model=SecurityEvent; fields="__all__"
class AuditEntrySerializer(serializers.ModelSerializer):
    class Meta: model=AuditEntry; fields="__all__"
class SecurityPolicySerializer(serializers.ModelSerializer):
    class Meta: model=SecurityPolicy; fields="__all__"
class SecurityIncidentSerializer(serializers.ModelSerializer):
    class Meta: model=SecurityIncident; fields="__all__"
class SecurityAlertSerializer(serializers.ModelSerializer):
    class Meta: model=SecurityAlert; fields="__all__"
class ComplianceControlSerializer(serializers.ModelSerializer):
    class Meta: model=ComplianceControl; fields="__all__"
class RiskAssessmentSerializer(serializers.ModelSerializer):
    class Meta: model=SecurityRiskAssessment; fields="__all__"
class UserSessionSerializer(serializers.ModelSerializer):
    class Meta: model=UserSession; fields="__all__"
