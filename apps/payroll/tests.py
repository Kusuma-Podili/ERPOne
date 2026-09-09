from datetime import date
from decimal import Decimal
from django.test import TestCase
from apps.accounts.models import User
from apps.organizations.models import Organization
from apps.hr.models import Employee
from .models import *
from .services import PayrollCalculationService,PayrollRunService
class PayrollPhase8Tests(TestCase):
 def setUp(self):
  self.user=User.objects.create_user(email='payroll@test.local',password='StrongPassword123!',first_name='Payroll',last_name='Admin'); self.org=Organization.objects.create(name='Payroll Org',slug='payroll-org',code='PAY'); self.emp=Employee.objects.create(organization=self.org,employee_number='E100',first_name='John',last_name='Smith',base_salary=Decimal('50000'))
  self.basic=PayrollComponent.objects.create(organization=self.org,name='Basic',code='BASIC',component_type='earning',calculation_method='fixed'); self.hra=PayrollComponent.objects.create(organization=self.org,name='Housing',code='HRA',component_type='earning',calculation_method='percentage',percentage=20); self.tax=PayrollComponent.objects.create(organization=self.org,name='Tax',code='TAX',component_type='deduction',calculation_method='percentage',percentage=10)
  self.structure=SalaryStructure.objects.create(organization=self.org,name='Standard',code='STD'); SalaryStructureLine.objects.create(structure=self.structure,component=self.basic,sequence=1,calculation_method='fixed',amount=50000); SalaryStructureLine.objects.create(structure=self.structure,component=self.hra,sequence=2,calculation_method='percentage',percentage=20); SalaryStructureLine.objects.create(structure=self.structure,component=self.tax,sequence=3,calculation_method='percentage',percentage=10); EmployeeSalaryAssignment.objects.create(employee=self.emp,structure=self.structure,effective_from=date(2026,1,1),monthly_base=50000); self.period=PayrollPeriod.objects.create(organization=self.org,name='January',code='2026-01',start_date=date(2026,1,1),end_date=date(2026,1,31),pay_date=date(2026,2,5))
 def test_calculation(self): s=PayrollCalculationService.calculate(self.emp,self.period); self.assertEqual(s.gross_pay,Decimal('60000.00')); self.assertEqual(s.total_deductions,Decimal('6000.00')); self.assertEqual(s.net_pay,Decimal('54000.00'))
 def test_run(self): self.assertEqual(PayrollRunService.process(self.period,self.user),1); self.assertEqual(self.period.status,'processed')
