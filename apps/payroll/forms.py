from django import forms
from .models import PayrollComponent,SalaryStructure,PayrollPeriod,PayrollAdjustment
class OrgForm(forms.ModelForm):
 def __init__(self,*a,organization=None,**k): super().__init__(*a,**k); self.organization=organization
class PayrollComponentForm(OrgForm):
 class Meta: model=PayrollComponent; exclude=('organization','created_at')
 def save(self,commit=True): o=super().save(False); o.organization=self.organization; commit and o.save(); return o
class SalaryStructureForm(OrgForm):
 class Meta: model=SalaryStructure; exclude=('organization','created_at','updated_at')
 def save(self,commit=True): o=super().save(False); o.organization=self.organization; commit and o.save(); return o
class PayrollPeriodForm(OrgForm):
 class Meta: model=PayrollPeriod; exclude=('organization','status','processed_at','processed_by','created_at','updated_at')
 def save(self,commit=True): o=super().save(False); o.organization=self.organization; commit and o.save(); return o
class PayrollAdjustmentForm(forms.ModelForm):
 class Meta: model=PayrollAdjustment; exclude=('created_by','created_at','approved','approved_by')
