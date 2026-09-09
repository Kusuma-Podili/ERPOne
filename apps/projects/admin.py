from django.contrib import admin
from .models import *
@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display=('code','name','status','priority','project_manager','target_end_date','progress_percent','budget')
    list_filter=('status','priority'); search_fields=('code','name','description'); autocomplete_fields=('project_manager','client','created_by')
for model in [ProjectMember,ProjectMilestone,ProjectTask,TaskDependency,TaskComment,TaskChecklistItem,ProjectTimeEntry,ProjectExpense,ProjectBudgetLine,ProjectStatusHistory,ProjectActivity]:
    admin.site.register(model)
