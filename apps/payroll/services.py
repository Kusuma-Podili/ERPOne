from decimal import Decimal,ROUND_HALF_UP
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from apps.hr.models import Employee
from .models import *
CENT=Decimal('0.01')
def money(v): return Decimal(v or 0).quantize(CENT,rounding=ROUND_HALF_UP)
class PayrollCalculationService:
 @staticmethod
 def assignment(employee,as_of): return EmployeeSalaryAssignment.objects.filter(employee=employee,effective_from__lte=as_of).filter(effective_to__isnull=True).order_by('-effective_from').first() or EmployeeSalaryAssignment.objects.filter(employee=employee,effective_from__lte=as_of,effective_to__gte=as_of).order_by('-effective_from').first()
 @classmethod
 def calculate(cls,employee,period):
  assignment=cls.assignment(employee,period.end_date); base=money(assignment.monthly_base if assignment else employee.base_salary); structure=assignment.structure if assignment else None; slip=Payslip.objects.create(period=period,employee=employee,payslip_number=f'PS-{period.code}-{employee.employee_number}'); gross=deductions=employer=Decimal('0'); values={}; seq=1
  if structure:
   for line in structure.lines.select_related('component').order_by('sequence'):
    if line.calculation_method==CalculationMethod.PERCENTAGE:
     calc_base = gross if line.component.component_type == ComponentType.DEDUCTION else base
     amount=money(calc_base*line.percentage/100)
    elif line.calculation_method==CalculationMethod.FORMULA: amount=money(line.amount)
    else: amount=money(line.amount)
    if line.min_amount is not None: amount=max(amount,line.min_amount)
    if line.max_amount is not None: amount=min(amount,line.max_amount)
    values[str(line.component_id)]=amount; c=line.component; PayslipLine.objects.create(payslip=slip,component=c,description=c.name,component_type=c.component_type,amount=amount,rate=amount,taxable_amount=amount if c.taxable else 0,sequence=seq); seq+=1
    if c.component_type==ComponentType.EARNING: gross+=amount
    elif c.component_type==ComponentType.DEDUCTION: deductions+=amount
    else: employer+=amount
  else:
   c=PayrollComponent.objects.filter(organization=employee.organization,code='BASIC',is_active=True).first(); gross=base
   if c: PayslipLine.objects.create(payslip=slip,component=c,description=c.name,component_type=c.component_type,amount=base,rate=base,taxable_amount=base,sequence=1)
  for a in period.adjustments.filter(employee=employee,approved=True).select_related('component'):
   PayslipLine.objects.create(payslip=slip,component=a.component,description=a.reason,component_type=a.component.component_type,amount=a.amount,rate=a.amount,sequence=seq); seq+=1
   if a.component.component_type==ComponentType.EARNING: gross+=a.amount
   elif a.component.component_type==ComponentType.DEDUCTION: deductions+=a.amount
   else: employer+=a.amount
  slip.gross_pay=money(gross); slip.total_deductions=money(deductions); slip.employer_cost=money(employer); slip.net_pay=money(gross-deductions); slip.status=PayrollStatus.PROCESSED; slip.save(); return slip
class PayrollRunService:
 @staticmethod
 @transaction.atomic
 def process(period,actor=None):
  if period.status not in (PayrollStatus.DRAFT,PayrollStatus.CANCELLED): raise ValidationError('Payroll period is not available for processing.')
  period.status=PayrollStatus.PROCESSING; period.save(update_fields=['status','updated_at']); PayrollRunAudit.objects.create(period=period,action='processing_started',message='Payroll processing started',actor=actor); count=0
  for e in Employee.objects.filter(organization=period.organization,employment_status__in=['active','on_leave']):
   Payslip.objects.filter(period=period,employee=e).delete(); PayrollCalculationService.calculate(e,period); count+=1
  period.status=PayrollStatus.PROCESSED; period.processed_at=timezone.now(); period.processed_by=actor; period.save(update_fields=['status','processed_at','processed_by','updated_at']); PayrollRunAudit.objects.create(period=period,action='processing_completed',message=f'Generated {count} payslips',actor=actor); return count
 @staticmethod
 def approve(period,actor):
  if period.status!=PayrollStatus.PROCESSED: raise ValidationError('Only processed payroll can be approved.'); period.status=PayrollStatus.APPROVED; period.save(update_fields=['status','updated_at']); return period
 @staticmethod
 def totals(period):
  ps=period.payslips.all(); return {'employees':ps.count(),'gross':sum((x.gross_pay for x in ps),Decimal('0')),'deductions':sum((x.total_deductions for x in ps),Decimal('0')),'net':sum((x.net_pay for x in ps),Decimal('0')),'employer_cost':sum((x.employer_cost for x in ps),Decimal('0'))}
