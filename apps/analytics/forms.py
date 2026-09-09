from django import forms
from .models import *
class MetricDefinitionForm(forms.ModelForm):
    class Meta: model=MetricDefinition; fields=['name','code','description','source','metric_type','expression','unit','dimensions','filters','is_active']
class KPIForm(forms.ModelForm):
    class Meta: model=KPI; fields=['metric','name','target','warning_threshold','critical_threshold','owner','is_active','display_order']
class DashboardForm(forms.ModelForm):
    class Meta: model=Dashboard; fields=['name','slug','description','is_default','is_shared','layout','filters']
class WidgetForm(forms.ModelForm):
    class Meta: model=DashboardWidget; fields=['title','widget_type','metric','configuration','position','refresh_seconds','is_visible']
class ReportForm(forms.ModelForm):
    class Meta: model=Report; fields=['name','code','description','source','status','columns','filters','group_by','order_by','aggregation']
class ScheduleForm(forms.ModelForm):
    class Meta: model=ReportSchedule; fields=['frequency','hour','minute','recipients','export_format','is_active','next_run_at']
class AlertForm(forms.ModelForm):
    class Meta: model=AnalyticsAlert; fields=['kpi','name','operator','threshold','recipients','is_active']
