from django import forms
from .models import *
class TicketForm(forms.ModelForm):
    class Meta:
        model=SupportTicket; fields=['subject','description','customer','category','priority','source','ticket_type','tags']
        widgets={'description':forms.Textarea(attrs={'rows':7}),'tags':forms.TextInput(attrs={'placeholder':'billing, login, urgent'})}
    def clean_tags(self):
        value=self.cleaned_data.get('tags')
        if isinstance(value,str): return [x.strip() for x in value.split(',') if x.strip()]
        return value or []
class TicketMessageForm(forms.ModelForm):
    class Meta: model=TicketMessage; fields=['body','is_internal','channel']; widgets={'body':forms.Textarea(attrs={'rows':5})}
class AssignmentForm(forms.Form):
    assignee=forms.ModelChoiceField(queryset=None,required=False); team=forms.ModelChoiceField(queryset=None,required=False); reason=forms.CharField(required=False)
    def __init__(self,*args,organization=None,**kwargs):
        super().__init__(*args,**kwargs)
        if organization:
            from apps.accounts.models import User
            self.fields['assignee'].queryset=User.objects.filter(is_active=True)
            self.fields['team'].queryset=SupportTeam.objects.filter(organization=organization,is_active=True)
class SatisfactionForm(forms.ModelForm):
    class Meta: model=TicketSatisfaction; fields=['rating','comment']; widgets={'rating':forms.NumberInput(attrs={'min':1,'max':5}),'comment':forms.Textarea(attrs={'rows':4})}
class KnowledgeArticleForm(forms.ModelForm):
    class Meta: model=KnowledgeArticle; fields=['category','title','slug','summary','content','tags','is_published']
class CannedResponseForm(forms.ModelForm):
    class Meta: model=CannedResponse; fields=['name','shortcut','body','category','is_active']
