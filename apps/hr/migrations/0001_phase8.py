from django.db import migrations

def create_tables(apps,schema_editor):
    from apps.hr import models
    for model in [models.JobPosition,models.Employee,models.EmploymentHistory,models.Shift,models.EmployeeShift,models.Holiday,models.LeavePolicy,models.LeaveBalance,models.LeaveRequest,models.AttendanceRecord,models.Timesheet,models.PerformanceCycle,models.PerformanceReview]: schema_editor.create_model(model)
def drop_tables(apps,schema_editor):
    from apps.hr import models
    for model in reversed([models.PerformanceReview,models.PerformanceCycle,models.Timesheet,models.AttendanceRecord,models.LeaveRequest,models.LeaveBalance,models.LeavePolicy,models.Holiday,models.EmployeeShift,models.Shift,models.EmploymentHistory,models.Employee,models.JobPosition]): schema_editor.delete_model(model)
class Migration(migrations.Migration):
    initial=True; dependencies=[('organizations','0001_initial')]; operations=[migrations.RunPython(create_tables,drop_tables)]
