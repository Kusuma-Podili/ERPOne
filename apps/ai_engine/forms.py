from django import forms
from .models import MLModel, DatasetDefinition, Experiment, FeatureDefinition

class MLModelForm(forms.ModelForm):
    class Meta:
        model=MLModel
        fields=['name','code','description','problem_type','target_field','source_module','feature_fields','configuration','status']
        widgets={'description':forms.Textarea(attrs={'rows':4}),'feature_fields':forms.Textarea(attrs={'rows':3}),'configuration':forms.Textarea(attrs={'rows':4})}

class DatasetDefinitionForm(forms.ModelForm):
    class Meta:
        model=DatasetDefinition
        fields=['name','code','source_module','query_definition','feature_schema','is_active']

class ExperimentForm(forms.ModelForm):
    class Meta:
        model=Experiment
        fields=['model','dataset','name','parameters']

class FeatureDefinitionForm(forms.ModelForm):
    class Meta:
        model=FeatureDefinition
        fields=['name','code','source_field','transform','configuration','is_active']
