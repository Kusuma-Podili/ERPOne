"""Framework-neutral scheduled analytics operations; callable from a task runner."""
from django.utils import timezone
from .models import ReportSchedule
from .services import ReportService

def due_schedules(now=None):
    now=now or timezone.now()
    return ReportSchedule.objects.filter(is_active=True,next_run_at__isnull=False,next_run_at__lte=now).select_related('report')

def execute_due_schedules(now=None):
    completed=[]
    for schedule in due_schedules(now):
        run=ReportService.run(schedule.report)
        schedule.last_run_at=timezone.now(); schedule.next_run_at=None; schedule.save(update_fields=['last_run_at','next_run_at'])
        completed.append(run)
    return completed
