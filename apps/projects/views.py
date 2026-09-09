from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import TemplateView,ListView,CreateView,DetailView,UpdateView
from apps.organizations.views import OrganizationAccessMixin
from .models import *
from .forms import *
from .services import ProjectService,TaskService,ProjectReportingService

class ProjectDashboardView(OrganizationAccessMixin,TemplateView):
    template_name='projects/dashboard.html'
    def get_context_data(self,**kwargs):
        c=super().get_context_data(**kwargs); o=self.request.organization
        c['summary']=ProjectReportingService.organization_summary(o); c['projects']=Project.objects.filter(organization=o).select_related('project_manager','client')[:10]; c['overdue']=Project.objects.filter(organization=o,target_end_date__lt=__import__('django').utils.timezone.now().date()).exclude(status__in=[ProjectStatus.COMPLETED,ProjectStatus.CANCELLED,ProjectStatus.ARCHIVED])[:10]; return c
class ProjectListView(OrganizationAccessMixin,ListView):
    model=Project; template_name='projects/project_list.html'; context_object_name='projects'; paginate_by=25
    def get_queryset(self):
        qs=Project.objects.filter(organization=self.request.organization).select_related('project_manager','client'); q=self.request.GET.get('q','').strip(); status=self.request.GET.get('status',''); priority=self.request.GET.get('priority','')
        if q: qs=qs.filter(Q(code__icontains=q)|Q(name__icontains=q)|Q(description__icontains=q))
        if status: qs=qs.filter(status=status)
        if priority: qs=qs.filter(priority=priority)
        return qs
class ProjectCreateView(OrganizationAccessMixin,CreateView):
    form_class=ProjectForm; template_name='projects/form.html'; success_url=reverse_lazy('projects:list')
    def form_valid(self,form): self.object=ProjectService.create_project(organization=self.request.organization,user=self.request.user,**form.cleaned_data); messages.success(self.request,'Project created.'); return redirect(self.success_url)
class ProjectDetailView(OrganizationAccessMixin,DetailView):
    model=Project; template_name='projects/detail.html'; context_object_name='project'
    def get_queryset(self): return Project.objects.filter(organization=self.request.organization).select_related('client','project_manager')
    def get_context_data(self,**kwargs):
        c=super().get_context_data(**kwargs); c['summary']=ProjectService.summary(self.object); c['tasks']=self.object.tasks.select_related('assignee','milestone')[:50]; c['members']=self.object.members.select_related('user')[:30]; c['milestones']=self.object.milestones.select_related('owner')[:20]; return c
class ProjectUpdateView(OrganizationAccessMixin,UpdateView):
    model=Project; form_class=ProjectForm; template_name='projects/form.html'; success_url=reverse_lazy('projects:list')
    def get_queryset(self): return Project.objects.filter(organization=self.request.organization)
    def form_valid(self,form): messages.success(self.request,'Project updated.'); return super().form_valid(form)
class TaskListView(OrganizationAccessMixin,ListView):
    model=ProjectTask; template_name='projects/task_list.html'; context_object_name='tasks'
    def get_queryset(self):
        self.project=get_object_or_404(Project,pk=self.kwargs['project_id'],organization=self.request.organization); qs=self.project.tasks.select_related('assignee','milestone'); q=self.request.GET.get('q',''); status=self.request.GET.get('status','');
        if q: qs=qs.filter(Q(title__icontains=q)|Q(task_key__icontains=q))
        return qs.filter(status=status) if status else qs
    def get_context_data(self,**kwargs): c=super().get_context_data(**kwargs); c['project']=self.project; return c
class TaskCreateView(OrganizationAccessMixin,CreateView):
    form_class=ProjectTaskForm; template_name='projects/form.html'
    def dispatch(self,request,*args,**kwargs): self.project=get_object_or_404(Project,pk=kwargs['project_id'],organization=request.organization); return super().dispatch(request,*args,**kwargs)
    def get_form(self,*a,**k): f=super().get_form(*a,**k); f.fields['milestone'].queryset=self.project.milestones.all(); f.fields['parent'].queryset=self.project.tasks.all(); return f
    def form_valid(self,form): self.object=form.save(commit=False); self.object.project=self.project; self.object.reporter=self.request.user; self.object.save(); ProjectActivity.objects.create(project=self.project,actor=self.request.user,action='task_created',entity_type='task',entity_id=str(self.object.pk),summary=f'Task {self.object.task_key} created.'); messages.success(self.request,'Task created.'); return redirect('projects:tasks',project_id=self.project.pk)
class TaskDetailView(OrganizationAccessMixin,DetailView):
    model=ProjectTask; template_name='projects/task_detail.html'; context_object_name='task'
    def get_queryset(self): return ProjectTask.objects.filter(project__organization=self.request.organization).select_related('project','assignee','milestone')
class TaskUpdateView(OrganizationAccessMixin,UpdateView):
    model=ProjectTask; form_class=ProjectTaskForm; template_name='projects/form.html'
    def get_queryset(self): return ProjectTask.objects.filter(project__organization=self.request.organization)
    def get_success_url(self): return reverse_lazy('projects:task_detail',kwargs={'pk':self.object.pk})
    def form_valid(self,form): response=super().form_valid(form); ProjectService.recalculate_progress(self.object.project); return response
class MilestoneCreateView(OrganizationAccessMixin,CreateView):
    form_class=ProjectMilestoneForm; template_name='projects/form.html'
    def dispatch(self,request,*args,**kwargs): self.project=get_object_or_404(Project,pk=kwargs['project_id'],organization=request.organization); return super().dispatch(request,*args,**kwargs)
    def form_valid(self,form): self.object=form.save(commit=False); self.object.project=self.project; self.object.save(); messages.success(self.request,'Milestone created.'); return redirect('projects:detail',pk=self.project.pk)
class TimeEntryCreateView(OrganizationAccessMixin,CreateView):
    form_class=TimeEntryForm; template_name='projects/form.html'
    def dispatch(self,request,*args,**kwargs): self.project=get_object_or_404(Project,pk=kwargs['project_id'],organization=request.organization); return super().dispatch(request,*args,**kwargs)
    def get_form(self,*a,**k): f=super().get_form(*a,**k); f.fields['task'].queryset=self.project.tasks.all(); return f
    def form_valid(self,form): self.object=form.save(commit=False); self.object.project=self.project; self.object.user=self.request.user; self.object.save(); messages.success(self.request,'Time entry recorded.'); return redirect('projects:detail',pk=self.project.pk)
class ExpenseCreateView(OrganizationAccessMixin,CreateView):
    form_class=ExpenseForm; template_name='projects/form.html'
    def dispatch(self,request,*args,**kwargs): self.project=get_object_or_404(Project,pk=kwargs['project_id'],organization=request.organization); return super().dispatch(request,*args,**kwargs)
    def form_valid(self,form): self.object=form.save(commit=False); self.object.project=self.project; self.object.submitted_by=self.request.user; self.object.status=ExpenseStatus.SUBMITTED; self.object.save(); messages.success(self.request,'Expense submitted.'); return redirect('projects:detail',pk=self.project.pk)
