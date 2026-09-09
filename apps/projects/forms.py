from django import forms
from .models import Project, ProjectMember, ProjectMilestone, ProjectTask, TaskComment, TaskChecklistItem, ProjectTimeEntry, ProjectExpense, ProjectBudgetLine
class ProjectForm(forms.ModelForm):
    class Meta:
        model=Project; fields=['code','name','description','client','project_manager','status','priority','start_date','target_end_date','budget','currency','tags']; widgets={'description':forms.Textarea(attrs={'rows':4}),'start_date':forms.DateInput(attrs={'type':'date'}),'target_end_date':forms.DateInput(attrs={'type':'date'})}
class ProjectMemberForm(forms.ModelForm):
    class Meta: model=ProjectMember; fields=['user','role','allocation_percent','hourly_rate','joined_on','left_on','is_active']
class ProjectMilestoneForm(forms.ModelForm):
    class Meta: model=ProjectMilestone; fields=['name','code','description','due_date','status','progress_percent','owner']; widgets={'due_date':forms.DateInput(attrs={'type':'date'})}
class ProjectTaskForm(forms.ModelForm):
    class Meta: model=ProjectTask; fields=['milestone','parent','title','task_key','description','status','priority','assignee','start_date','due_date','estimated_hours','progress_percent','labels']; widgets={'description':forms.Textarea(attrs={'rows':4}),'start_date':forms.DateInput(attrs={'type':'date'}),'due_date':forms.DateInput(attrs={'type':'date'})}
class TaskCommentForm(forms.ModelForm):
    class Meta: model=TaskComment; fields=['body','is_internal']; widgets={'body':forms.Textarea(attrs={'rows':4})}
class ChecklistForm(forms.ModelForm):
    class Meta: model=TaskChecklistItem; fields=['title','sort_order']
class TimeEntryForm(forms.ModelForm):
    class Meta: model=ProjectTimeEntry; fields=['task','work_date','hours','description','billable']; widgets={'work_date':forms.DateInput(attrs={'type':'date'})}
class ExpenseForm(forms.ModelForm):
    class Meta: model=ProjectExpense; fields=['task','expense_date','category','description','amount','currency']; widgets={'expense_date':forms.DateInput(attrs={'type':'date'})}
class BudgetLineForm(forms.ModelForm):
    class Meta: model=ProjectBudgetLine; fields=['category','description','planned_amount','committed_amount','actual_amount','currency']
