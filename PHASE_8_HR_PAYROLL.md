# EnterpriseOne Phase 8 - HR & Payroll

Phase 8 adds a production-oriented workforce and payroll domain while preserving organization-level tenancy.

## HR
- Employee master and lifecycle status
- Job positions and salary bands
- Employment history
- Shifts and employee shift assignments
- Holidays
- Leave policies and yearly balances
- Working-day leave calculation
- Leave submission and approval workflow
- Attendance records and worked/overtime/late calculations
- Timesheets
- Performance cycles and reviews

## Payroll
- Payroll components: earnings, deductions and employer costs
- Salary structures and component lines
- Employee salary assignments with effective dates
- Payroll periods and validation
- Payslip and payslip line generation
- Approved payroll adjustments
- Payroll payment records
- Payroll run audit events
- Deterministic payroll calculation and processing services

## Routes
- `/hr/`
- `/hr/employees/`
- `/hr/positions/`
- `/hr/shifts/`
- `/hr/leave/`
- `/hr/attendance/`
- `/payroll/`
- `/payroll/components/`
- `/payroll/structures/`
- `/payroll/periods/`
- `/payroll/payslips/`

## Validation
Python source compilation was run across the Phase 8 modules and project configuration.
Django test execution requires the dependencies from `requirements.txt` to be installed in the runtime environment.
