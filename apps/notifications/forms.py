from django import forms
from .models import NotificationTemplate, NotificationPreference, Reminder, NotificationRule
class NotificationTemplateForm(forms.ModelForm):
    class Meta: model=NotificationTemplate; fields=['name','code','channel','subject_template','body_template','variables','version','is_active']
class NotificationPreferenceForm(forms.ModelForm):
    class Meta: model=NotificationPreference; fields=['event_code','channel','enabled','quiet_start','quiet_end','digest_enabled']
class ReminderForm(forms.ModelForm):
    class Meta: model=Reminder; fields=['user','title','message','remind_at','repeat_rule']
class NotificationRuleForm(forms.ModelForm):
    class Meta: model=NotificationRule; fields=['name','event_code','condition','template','channels','recipient_strategy','recipient_config','priority','is_active']
