import uuid
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

class EmploymentStatus(models.TextChoices):
    ACTIVE='active','Active'; ON_LEAVE='on_leave','On Leave'; SUSPENDED='suspended','Suspended'; TERMINATED='terminated','Terminated'; RESIGNED='resigned','Resigned'; RETIRED='retired','Retired'
class EmploymentType(models.TextChoices):
    FULL_TIME='full_time','Full Time'; PART_TIME='part_time','Part Time'; CONTRACT='contract','Contract'; INTERN='intern','Intern'; TEMPORARY='temporary','Temporary'
class AttendanceStatus(models.TextChoices):
    PRESENT='present','Present'; ABSENT='absent','Absent'; LATE='late','Late'; HALF_DAY='half_day','Half Day'; ON_LEAVE='on_leave','On Leave'; HOLIDAY='holiday','Holiday'
class LeaveStatus(models.TextChoices):
    DRAFT='draft','Draft'; PENDING='pending','Pending'; APPROVED='approved','Approved'; REJECTED='rejected','Rejected'; CANCELLED='cancelled','Cancelled'
class PerformanceStatus(models.TextChoices):
    DRAFT='draft','Draft'; OPEN='open','Open'; SUBMITTED='submitted','Submitted'; REVIEWED='reviewed','Reviewed'; FINALIZED='finalized','Finalized'

class JobPosition(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); organization=models.ForeignKey('organizations.Organization',on_delete=models.CASCADE,related_name='hr_job_positions'); department=models.ForeignKey('organizations.Department',on_delete=models.SET_NULL,null=True,blank=True,related_name='job_positions')
    title=models.CharField(max_length=150); code=models.CharField(max_length=50); description=models.TextField(blank=True); grade=models.CharField(max_length=30,blank=True); minimum_salary=models.DecimalField(max_digits=14,decimal_places=2,default=0); maximum_salary=models.DecimalField(max_digits=14,decimal_places=2,default=0); headcount_budget=models.PositiveIntegerField(default=1); is_active=models.BooleanField(default=True); created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta: unique_together=('organization','code'); ordering=('title',)
    def __str__(self): return f'{self.code} - {self.title}'
    def clean(self):
        if self.maximum_salary and self.maximum_salary<self.minimum_salary: raise ValidationError('Maximum salary cannot be below minimum salary.')

class Employee(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); organization=models.ForeignKey('organizations.Organization',on_delete=models.CASCADE,related_name='employees'); user=models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='employee_record')
    employee_number=models.CharField(max_length=40); first_name=models.CharField(max_length=100); last_name=models.CharField(max_length=100); personal_email=models.EmailField(blank=True); work_email=models.EmailField(blank=True); phone=models.CharField(max_length=30,blank=True)
    date_of_birth=models.DateField(null=True,blank=True); hire_date=models.DateField(default=timezone.now); termination_date=models.DateField(null=True,blank=True); employment_type=models.CharField(max_length=20,choices=EmploymentType.choices,default=EmploymentType.FULL_TIME); employment_status=models.CharField(max_length=20,choices=EmploymentStatus.choices,default=EmploymentStatus.ACTIVE,db_index=True)
    department=models.ForeignKey('organizations.Department',on_delete=models.SET_NULL,null=True,blank=True,related_name='employees'); position=models.ForeignKey(JobPosition,on_delete=models.SET_NULL,null=True,blank=True,related_name='employees'); manager=models.ForeignKey('self',on_delete=models.SET_NULL,null=True,blank=True,related_name='direct_reports'); branch=models.ForeignKey('organizations.Branch',on_delete=models.SET_NULL,null=True,blank=True,related_name='employees'); location=models.ForeignKey('organizations.Location',on_delete=models.SET_NULL,null=True,blank=True,related_name='employees')
    national_id=models.CharField(max_length=100,blank=True); emergency_contact_name=models.CharField(max_length=150,blank=True); emergency_contact_phone=models.CharField(max_length=30,blank=True); base_salary=models.DecimalField(max_digits=14,decimal_places=2,default=0); currency=models.CharField(max_length=10,default='USD'); bank_name=models.CharField(max_length=120,blank=True); bank_account_number=models.CharField(max_length=80,blank=True); notes=models.TextField(blank=True); created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta: unique_together=('organization','employee_number'); ordering=('employee_number',); indexes=[models.Index(fields=('organization','employment_status')),models.Index(fields=('organization','department'))]
    @property
    def full_name(self): return f'{self.first_name} {self.last_name}'.strip()
    @property
    def tenure_days(self): return ((self.termination_date or timezone.now().date())-self.hire_date).days
    def __str__(self): return f'{self.employee_number} - {self.full_name}'
    def clean(self):
        if self.termination_date and self.termination_date<self.hire_date: raise ValidationError('Termination date cannot precede hire date.')
        if self.base_salary<0: raise ValidationError('Base salary cannot be negative.')

class EmploymentHistory(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); employee=models.ForeignKey(Employee,on_delete=models.CASCADE,related_name='employment_history'); effective_date=models.DateField(); action=models.CharField(max_length=100); previous_department=models.ForeignKey('organizations.Department',on_delete=models.SET_NULL,null=True,blank=True,related_name='hr_history_from'); new_department=models.ForeignKey('organizations.Department',on_delete=models.SET_NULL,null=True,blank=True,related_name='hr_history_to'); previous_position=models.ForeignKey(JobPosition,on_delete=models.SET_NULL,null=True,blank=True,related_name='hr_history_from_position'); new_position=models.ForeignKey(JobPosition,on_delete=models.SET_NULL,null=True,blank=True,related_name='hr_history_to_position'); previous_salary=models.DecimalField(max_digits=14,decimal_places=2,default=0); new_salary=models.DecimalField(max_digits=14,decimal_places=2,default=0); reason=models.TextField(blank=True); changed_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True); created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=('-effective_date','-created_at')

class Shift(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); organization=models.ForeignKey('organizations.Organization',on_delete=models.CASCADE,related_name='hr_shifts'); name=models.CharField(max_length=100); code=models.CharField(max_length=30); start_time=models.TimeField(); end_time=models.TimeField(); grace_minutes=models.PositiveIntegerField(default=10); break_minutes=models.PositiveIntegerField(default=0); is_overnight=models.BooleanField(default=False); is_active=models.BooleanField(default=True)
    class Meta: unique_together=('organization','code')

class EmployeeShift(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); employee=models.ForeignKey(Employee,on_delete=models.CASCADE,related_name='shift_assignments'); shift=models.ForeignKey(Shift,on_delete=models.CASCADE,related_name='employee_assignments'); effective_from=models.DateField(); effective_to=models.DateField(null=True,blank=True); is_primary=models.BooleanField(default=True)
    def clean(self):
        if self.effective_to and self.effective_to<self.effective_from: raise ValidationError('Shift end cannot precede start.')

class Holiday(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); organization=models.ForeignKey('organizations.Organization',on_delete=models.CASCADE,related_name='hr_holidays'); name=models.CharField(max_length=150); date=models.DateField(); is_optional=models.BooleanField(default=False); description=models.TextField(blank=True); is_active=models.BooleanField(default=True)
    class Meta: unique_together=('organization','date'); ordering=('date',)

class LeavePolicy(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); organization=models.ForeignKey('organizations.Organization',on_delete=models.CASCADE,related_name='leave_policies'); name=models.CharField(max_length=120); code=models.CharField(max_length=30); annual_entitlement=models.DecimalField(max_digits=7,decimal_places=2,default=0); carry_forward_limit=models.DecimalField(max_digits=7,decimal_places=2,default=0); requires_attachment=models.BooleanField(default=False); requires_manager_approval=models.BooleanField(default=True); allow_negative_balance=models.BooleanField(default=False); is_active=models.BooleanField(default=True)
    class Meta: unique_together=('organization','code')

class LeaveBalance(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); employee=models.ForeignKey(Employee,on_delete=models.CASCADE,related_name='leave_balances'); policy=models.ForeignKey(LeavePolicy,on_delete=models.CASCADE,related_name='balances'); year=models.PositiveIntegerField(); opening_balance=models.DecimalField(max_digits=7,decimal_places=2,default=0); accrued=models.DecimalField(max_digits=7,decimal_places=2,default=0); used=models.DecimalField(max_digits=7,decimal_places=2,default=0); adjustment=models.DecimalField(max_digits=7,decimal_places=2,default=0)
    class Meta: unique_together=('employee','policy','year')
    @property
    def available(self): return self.opening_balance+self.accrued+self.adjustment-self.used

class LeaveRequest(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); employee=models.ForeignKey(Employee,on_delete=models.CASCADE,related_name='leave_requests'); policy=models.ForeignKey(LeavePolicy,on_delete=models.PROTECT,related_name='requests'); start_date=models.DateField(); end_date=models.DateField(); days=models.DecimalField(max_digits=6,decimal_places=2,default=0); reason=models.TextField(); status=models.CharField(max_length=20,choices=LeaveStatus.choices,default=LeaveStatus.DRAFT,db_index=True); approver=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='approved_leave_requests'); decision_note=models.TextField(blank=True); decided_at=models.DateTimeField(null=True,blank=True); created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,related_name='created_leave_requests'); created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta: ordering=('-created_at',)
    def clean(self):
        if self.end_date<self.start_date: raise ValidationError('End date must be on or after start date.')

class AttendanceRecord(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); employee=models.ForeignKey(Employee,on_delete=models.CASCADE,related_name='attendance_records'); work_date=models.DateField(); shift=models.ForeignKey(Shift,on_delete=models.SET_NULL,null=True,blank=True); check_in=models.DateTimeField(null=True,blank=True); check_out=models.DateTimeField(null=True,blank=True); status=models.CharField(max_length=20,choices=AttendanceStatus.choices,default=AttendanceStatus.PRESENT); worked_minutes=models.PositiveIntegerField(default=0); overtime_minutes=models.PositiveIntegerField(default=0); late_minutes=models.PositiveIntegerField(default=0); notes=models.TextField(blank=True); source=models.CharField(max_length=30,default='manual'); approved_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='approved_attendance'); created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta: unique_together=('employee','work_date'); ordering=('-work_date',)
    def calculate_minutes(self):
        if self.check_in and self.check_out:
            raw=max(0,int((self.check_out-self.check_in).total_seconds()/60)); self.worked_minutes=max(0,raw-(self.shift.break_minutes if self.shift else 0)); expected=(self.shift.start_time.hour*60+self.shift.start_time.minute) if self.shift else None; actual=self.check_in.hour*60+self.check_in.minute; self.late_minutes=max(0,actual-expected-(self.shift.grace_minutes if self.shift and expected is not None else 0)) if expected is not None else 0
        return self

class Timesheet(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); employee=models.ForeignKey(Employee,on_delete=models.CASCADE,related_name='timesheets'); work_date=models.DateField(); description=models.CharField(max_length=255); hours=models.DecimalField(max_digits=6,decimal_places=2); billable=models.BooleanField(default=False); approved=models.BooleanField(default=False); approved_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True); created_at=models.DateTimeField(auto_now_add=True)
    def clean(self):
        if self.hours<=0 or self.hours>24: raise ValidationError('Hours must be between 0 and 24.')

class PerformanceCycle(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); organization=models.ForeignKey('organizations.Organization',on_delete=models.CASCADE,related_name='performance_cycles'); name=models.CharField(max_length=150); start_date=models.DateField(); end_date=models.DateField(); status=models.CharField(max_length=20,choices=PerformanceStatus.choices,default=PerformanceStatus.DRAFT); rating_scale=models.DecimalField(max_digits=4,decimal_places=2,default=5); created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True); created_at=models.DateTimeField(auto_now_add=True)
    def clean(self):
        if self.end_date<self.start_date: raise ValidationError('Performance cycle end must follow start.')

class PerformanceReview(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); cycle=models.ForeignKey(PerformanceCycle,on_delete=models.CASCADE,related_name='reviews'); employee=models.ForeignKey(Employee,on_delete=models.CASCADE,related_name='performance_reviews'); reviewer=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='performance_reviews_given'); self_rating=models.DecimalField(max_digits=4,decimal_places=2,null=True,blank=True); manager_rating=models.DecimalField(max_digits=4,decimal_places=2,null=True,blank=True); final_rating=models.DecimalField(max_digits=4,decimal_places=2,null=True,blank=True); strengths=models.TextField(blank=True); development_areas=models.TextField(blank=True); goals=models.TextField(blank=True); comments=models.TextField(blank=True); status=models.CharField(max_length=20,choices=PerformanceStatus.choices,default=PerformanceStatus.DRAFT); created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta: unique_together=('cycle','employee')
