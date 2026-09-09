from datetime import timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from .models import Employee,EmploymentHistory,LeaveBalance,LeaveRequest,LeaveStatus,AttendanceRecord,AttendanceStatus,Holiday
class EmployeeService:
 @staticmethod
 @transaction.atomic
 def change(employee,department=None,position=None,salary=None,effective_date=None,reason='',actor=None):
  old=(employee.department,employee.position,employee.base_salary); employee.department=department or employee.department; employee.position=position or employee.position; employee.base_salary=Decimal(salary) if salary is not None else employee.base_salary; employee.save(); EmploymentHistory.objects.create(employee=employee,effective_date=effective_date or timezone.now().date(),action='Employee change',previous_department=old[0],new_department=employee.department,previous_position=old[1],new_position=employee.position,previous_salary=old[2],new_salary=employee.base_salary,reason=reason,changed_by=actor); return employee
 @staticmethod
 @transaction.atomic
 def terminate(employee,date=None,reason='',actor=None):
  d=date or timezone.now().date(); employee.termination_date=d; employee.employment_status='terminated'; employee.save(update_fields=['termination_date','employment_status','updated_at']); EmploymentHistory.objects.create(employee=employee,effective_date=d,action='Termination',previous_department=employee.department,new_department=employee.department,previous_position=employee.position,new_position=employee.position,previous_salary=employee.base_salary,new_salary=employee.base_salary,reason=reason,changed_by=actor); return employee
class AttendanceService:
 @staticmethod
 def record(employee,work_date,check_in=None,check_out=None,shift=None,status=AttendanceStatus.PRESENT,notes=''):
  r,_=AttendanceRecord.objects.update_or_create(employee=employee,work_date=work_date,defaults={'check_in':check_in,'check_out':check_out,'shift':shift,'status':status,'notes':notes}); r.calculate_minutes(); r.overtime_minutes=max(0,r.worked_minutes-480); r.save(); return r
 @staticmethod
 def summary(employee,start,end):
  qs=employee.attendance_records.filter(work_date__range=(start,end)); return {'total':qs.count(),'present':qs.filter(status='present').count(),'absent':qs.filter(status='absent').count(),'late':qs.filter(status='late').count(),'leave':qs.filter(status='on_leave').count(),'worked_minutes':sum(x.worked_minutes for x in qs),'overtime_minutes':sum(x.overtime_minutes for x in qs)}
class LeaveService:
 @staticmethod
 def working_days(start,end,organization):
  holidays=set(Holiday.objects.filter(organization=organization,date__range=(start,end),is_active=True).values_list('date',flat=True)); cur=start; total=0
  while cur<=end:
   if cur.weekday()<5 and cur not in holidays: total+=1
   cur+=timedelta(days=1)
  return Decimal(total)
 @staticmethod
 @transaction.atomic
 def submit(request,actor):
  request.days=LeaveService.working_days(request.start_date,request.end_date,request.employee.organization); request.created_by=actor; request.full_clean(); balance,_=LeaveBalance.objects.get_or_create(employee=request.employee,policy=request.policy,year=request.start_date.year)
  if not request.policy.allow_negative_balance and balance.available<request.days: raise ValidationError('Insufficient leave balance.')
  request.status=LeaveStatus.PENDING; request.save(); return request
 @staticmethod
 @transaction.atomic
 def decide(request,approved,actor,note=''):
  if request.status!=LeaveStatus.PENDING: raise ValidationError('Only pending requests can be decided.')
  request.status=LeaveStatus.APPROVED if approved else LeaveStatus.REJECTED; request.approver=actor; request.decision_note=note; request.decided_at=timezone.now(); request.save()
  if approved: b,_=LeaveBalance.objects.get_or_create(employee=request.employee,policy=request.policy,year=request.start_date.year); b.used+=request.days; b.save(update_fields=['used'])
  return request
