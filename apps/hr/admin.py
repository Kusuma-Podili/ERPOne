from django.contrib import admin
from .models import *
for model in [JobPosition,EmploymentHistory,Shift,EmployeeShift,Holiday,LeavePolicy,LeaveBalance,LeaveRequest,AttendanceRecord,Timesheet,PerformanceCycle,PerformanceReview]: admin.site.register(model)
@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
 list_display=('employee_number','first_name','last_name','department','position','employment_status','hire_date'); search_fields=('employee_number','first_name','last_name','work_email'); list_filter=('employment_status','employment_type')
