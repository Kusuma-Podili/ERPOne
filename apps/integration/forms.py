from django import forms
from .models import IntegrationConnection, IntegrationJob, IntegrationMapping, FeatureFlag, SystemConfiguration, ReleaseRecord, ReconciliationRun
class ConnectionForm(forms.ModelForm):
    class Meta: model=IntegrationConnection; fields=["organization","name","code","provider","connection_type","base_url","status","configuration","secret_reference","retry_limit","timeout_seconds","metadata"]
class JobForm(forms.ModelForm):
    class Meta: model=IntegrationJob; fields=["organization","name","code","job_type","connection","endpoint","mapping","schedule_expression","batch_size","max_retries","enabled","parameters"]
class MappingForm(forms.ModelForm):
    class Meta: model=IntegrationMapping; fields=["organization","name","source_domain","target_domain","field_map","transforms","defaults","validation_rules","version","active"]
class FeatureFlagForm(forms.ModelForm):
    class Meta: model=FeatureFlag; fields=["organization","key","description","enabled","rollout_percent","environments","rules"]
class ConfigurationForm(forms.ModelForm):
    class Meta: model=SystemConfiguration; fields=["organization","key","value","value_type","environment","description","encrypted"]
class ReleaseForm(forms.ModelForm):
    class Meta: model=ReleaseRecord; fields=["version","commit_reference","environment","status","release_notes","migration_required","deployed_by"]
class ReconciliationForm(forms.ModelForm):
    class Meta: model=ReconciliationRun; fields=["organization","name","source_system","target_system"]
