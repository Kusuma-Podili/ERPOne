from datetime import date,datetime,time,timezone
from decimal import Decimal
from django.test import TestCase
from apps.accounts.models import User
from apps.organizations.models import Organization,Department
from .models import Employee,JobPosition,LeavePolicy,LeaveBalance,LeaveRequest,Shift
from .services import LeaveService,EmployeeService,AttendanceService
class HRPhase8Tests(TestCase):
 def setUp(self):
  self.user=User.objects.create_user(email='hr@test.local',password='StrongPassword123!',first_name='HR',last_name='Admin'); self.org=Organization.objects.create(name='HR Org',slug='hr-org',code='HRO'); self.dept=Department.objects.create(organization=self.org,name='Engineering',code='ENG'); self.pos=JobPosition.objects.create(organization=self.org,title='Developer',code='DEV'); self.emp=Employee.objects.create(organization=self.org,employee_number='E001',first_name='Jane',last_name='Doe',department=self.dept,position=self.pos,base_salary=Decimal('50000'))
 def test_employee_change_history(self): EmployeeService.change(self.emp,salary=Decimal('55000'),actor=self.user); self.assertEqual(self.emp.base_salary,Decimal('55000')); self.assertEqual(self.emp.employment_history.count(),1)
 def test_working_days(self): LeavePolicy.objects.create(organization=self.org,name='Annual',code='AL'); self.assertEqual(LeaveService.working_days(date(2026,1,5),date(2026,1,9),self.org),Decimal('5'))
 def test_leave_balance_enforced(self):
  policy=LeavePolicy.objects.create(organization=self.org,name='Annual',code='AL'); LeaveBalance.objects.create(employee=self.emp,policy=policy,year=2026,accrued=Decimal('10')); req=LeaveRequest(employee=self.emp,policy=policy,start_date=date(2026,1,5),end_date=date(2026,1,7),days=Decimal('3'),reason='Vacation'); LeaveService.submit(req,self.user); self.assertEqual(req.status,'pending')
 def test_attendance_minutes(self):
  shift=Shift.objects.create(organization=self.org,name='Day',code='DAY',start_time=time(9),end_time=time(17),break_minutes=60,grace_minutes=10); r=AttendanceService.record(self.emp,date(2026,1,5),datetime(2026,1,5,9,15,tzinfo=timezone.utc),datetime(2026,1,5,18,15,tzinfo=timezone.utc),shift=shift); self.assertEqual(r.worked_minutes,480); self.assertEqual(r.late_minutes,5)
