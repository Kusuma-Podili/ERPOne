from decimal import Decimal
from django.db import transaction
from django.db.models import Sum, Count, Q
from django.utils import timezone
from .models import *

class ProjectService:
    @staticmethod
    @transaction.atomic
    def create_project(*, organization, user, **data):
        project=Project.objects.create(organization=organization,created_by=user,**data)
        ProjectActivity.objects.create(project=project,actor=user,action='created',entity_type='project',entity_id=str(project.pk),summary=f'Project {project.code} created.')
        return project
    @staticmethod
    @transaction.atomic
    def change_status(project, status, user, note=''):
        old=project.status
        if old==status: return project
        project.status=status
        if status==ProjectStatus.COMPLETED:
            project.progress_percent=Decimal('100')
            project.actual_end_date=project.actual_end_date or timezone.now().date()
        project.save(update_fields=['status','progress_percent','actual_end_date','updated_at'])
        ProjectStatusHistory.objects.create(project=project,from_status=old,to_status=status,note=note,changed_by=user)
        ProjectActivity.objects.create(project=project,actor=user,action='status_changed',entity_type='project',entity_id=str(project.pk),summary=f'Status changed from {old} to {status}.',metadata={'from':old,'to':status})
        return project
    @staticmethod
    def recalculate_progress(project):
        tasks=list(project.tasks.exclude(status=TaskStatus.CANCELLED))
        if not tasks: return project.progress_percent
        total=sum((Decimal(str(t.progress_percent)) for t in tasks),Decimal('0'))
        progress=(total/Decimal(len(tasks))).quantize(Decimal('0.01'))
        project.progress_percent=progress
        project.save(update_fields=['progress_percent','updated_at'])
        return progress
    @staticmethod
    def summary(project):
        tasks=project.tasks.all()
        return {'task_count':tasks.count(),'completed_tasks':tasks.filter(status=TaskStatus.DONE).count(),'open_tasks':tasks.exclude(status__in=[TaskStatus.DONE,TaskStatus.CANCELLED]).count(),'overdue_tasks':tasks.filter(due_date__lt=timezone.now().date()).exclude(status__in=[TaskStatus.DONE,TaskStatus.CANCELLED]).count(),'member_count':project.members.filter(is_active=True).count(),'hours':project.time_entries.aggregate(v=Sum('hours'))['v'] or Decimal('0'),'expenses':project.expenses.filter(status__in=[ExpenseStatus.APPROVED,ExpenseStatus.REIMBURSED]).aggregate(v=Sum('amount'))['v'] or Decimal('0')}

class TaskService:
    @staticmethod
    @transaction.atomic
    def complete(task, user):
        task.status=TaskStatus.DONE; task.progress_percent=Decimal('100'); task.save(update_fields=['status','progress_percent','updated_at'])
        ProjectActivity.objects.create(project=task.project,actor=user,action='task_completed',entity_type='task',entity_id=str(task.pk),summary=f'Task {task.task_key} completed.')
        ProjectService.recalculate_progress(task.project)
        return task
    @staticmethod
    def assign(task,user,actor=None):
        task.assignee=user; task.save(update_fields=['assignee','updated_at'])
        ProjectActivity.objects.create(project=task.project,actor=actor,action='task_assigned',entity_type='task',entity_id=str(task.pk),summary=f'Task {task.task_key} assigned to {user}.')
        return task

class ProjectReportingService:
    @staticmethod
    def organization_summary(organization):
        qs=Project.objects.filter(organization=organization)
        return {'projects':qs.count(),'active':qs.filter(status=ProjectStatus.ACTIVE).count(),'completed':qs.filter(status=ProjectStatus.COMPLETED).count(),'overdue':qs.filter(target_end_date__lt=timezone.now().date()).exclude(status__in=[ProjectStatus.COMPLETED,ProjectStatus.CANCELLED,ProjectStatus.ARCHIVED]).count(),'budget':qs.aggregate(v=Sum('budget'))['v'] or Decimal('0'),'tasks':ProjectTask.objects.filter(project__organization=organization).count(),'hours':ProjectTimeEntry.objects.filter(project__organization=organization).aggregate(v=Sum('hours'))['v'] or Decimal('0'),'expenses':ProjectExpense.objects.filter(project__organization=organization,status__in=[ExpenseStatus.APPROVED,ExpenseStatus.REIMBURSED]).aggregate(v=Sum('amount'))['v'] or Decimal('0')}
    @staticmethod
    def workload(organization):
        return ProjectMember.objects.filter(project__organization=organization,is_active=True).values('user_id').annotate(projects=Count('project',distinct=True),tasks=Count('project__tasks',filter=Q(project__tasks__status__in=[TaskStatus.TODO,TaskStatus.IN_PROGRESS,TaskStatus.REVIEW]))).order_by('-tasks')
