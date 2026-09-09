from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.organizations.models import Organization
from .models import *
from .services import ProjectService, ProjectReportingService
User=get_user_model()
class ProjectPhase9Tests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user(email='project@example.com',password='StrongPass123!')
        self.org=Organization.objects.create(name='Project Test Org',slug='project-test-org')
    def test_project_progress_and_completion(self):
        p=ProjectService.create_project(organization=self.org,user=self.user,code='PRJ-001',name='Migration',budget=Decimal('10000'))
        ProjectMember.objects.create(project=p,user=self.user)
        ProjectTask.objects.create(project=p,task_key='TASK-1',title='Build',progress_percent=50)
        ProjectTask.objects.create(project=p,task_key='TASK-2',title='Test',progress_percent=100,status=TaskStatus.DONE)
        self.assertEqual(ProjectService.recalculate_progress(p),Decimal('75.00'))
        ProjectService.change_status(p,ProjectStatus.COMPLETED,self.user)
        p.refresh_from_db(); self.assertEqual(p.progress_percent,Decimal('100.00'))
    def test_reporting_summary(self):
        Project.objects.create(organization=self.org,code='PRJ-001',name='Active',status=ProjectStatus.ACTIVE,budget=5000,target_end_date=date.today()+timedelta(days=5))
        s=ProjectReportingService.organization_summary(self.org)
        self.assertEqual(s['projects'],1); self.assertEqual(s['active'],1); self.assertEqual(s['budget'],Decimal('5000'))
    def test_invalid_task_dates(self):
        from django.core.exceptions import ValidationError
        p=Project.objects.create(organization=self.org,code='PRJ-002',name='Dates')
        t=ProjectTask(project=p,task_key='T-1',title='Invalid',start_date=date.today(),due_date=date.today()-timedelta(days=1))
        with self.assertRaises(ValidationError): t.full_clean()
