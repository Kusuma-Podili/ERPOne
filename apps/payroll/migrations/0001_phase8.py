from django.db import migrations

def create_tables(apps,schema_editor):
    from apps.payroll import models
    for model in [models.PayrollComponent,models.SalaryStructure,models.SalaryStructureLine,models.EmployeeSalaryAssignment,models.PayrollPeriod,models.Payslip,models.PayslipLine,models.PayrollAdjustment,models.PayrollPayment,models.PayrollRunAudit]: schema_editor.create_model(model)
def drop_tables(apps,schema_editor):
    from apps.payroll import models
    for model in reversed([models.PayrollRunAudit,models.PayrollPayment,models.PayrollAdjustment,models.PayslipLine,models.Payslip,models.PayrollPeriod,models.EmployeeSalaryAssignment,models.SalaryStructureLine,models.SalaryStructure,models.PayrollComponent]): schema_editor.delete_model(model)
class Migration(migrations.Migration):
    initial=True; dependencies=[('hr','0001_phase8')]; operations=[]
