from django.contrib import admin
from .models import *
for model in [PayrollComponent,SalaryStructure,SalaryStructureLine,EmployeeSalaryAssignment,Payslip,PayslipLine,PayrollAdjustment,PayrollPayment,PayrollRunAudit]: admin.site.register(model)
@admin.register(PayrollPeriod)
class PayrollPeriodAdmin(admin.ModelAdmin): list_display=('code','name','start_date','end_date','pay_date','status'); list_filter=('status',); search_fields=('code','name')
