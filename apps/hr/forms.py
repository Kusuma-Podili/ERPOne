from django import forms
from .models import Employee,JobPosition,Shift,Holiday,LeavePolicy,LeaveRequest,PerformanceCycle
class OrgForm(forms.ModelForm):
 def __init__(self,*a,organization=None,**k): super().__init__(*a,**k); self.organization=organization
class EmployeeForm(OrgForm):
 class Meta: model=Employee; exclude=('organization','created_at','updated_at')
 def save(self,commit=True): o=super().save(False); o.organization=self.organization; commit and o.save(); return o
class JobPositionForm(OrgForm):
 class Meta: model=JobPosition; exclude=('organization',)
 def save(self,commit=True): o=super().save(False); o.organization=self.organization; commit and o.save(); return o
class ShiftForm(OrgForm):
 class Meta: model=Shift; exclude=('organization',)
 def save(self,commit=True): o=super().save(False); o.organization=self.organization; commit and o.save(); return o
class HolidayForm(OrgForm):
 class Meta: model=Holiday; exclude=('organization',)
 def save(self,commit=True): o=super().save(False); o.organization=self.organization; commit and o.save(); return o
class LeavePolicyForm(OrgForm):
 class Meta: model=LeavePolicy; exclude=('organization',)
 def save(self,commit=True): o=super().save(False); o.organization=self.organization; commit and o.save(); return o
class LeaveRequestForm(forms.ModelForm):
 class Meta: model=LeaveRequest; exclude=('employee','status','approver','decision_note','decided_at','created_by','created_at','updated_at')
class PerformanceCycleForm(OrgForm):
 class Meta: model=PerformanceCycle; exclude=('organization','created_by','created_at')
 def save(self,commit=True): o=super().save(False); o.organization=self.organization; commit and o.save(); return o
