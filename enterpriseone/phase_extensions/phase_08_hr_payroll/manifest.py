"""Feature manifest for this phase."""

PHASE = 8
NAME = 'hr_payroll'
APPLICATION = 'hr'
FEATURES = ['employee', 'recruiting', 'compensation', 'benefit', 'leave', 'attendance', 'shift', 'performance', 'learning', 'payroll', 'deduction', 'timesheet', 'succession', 'engagement', 'workforce']

def describe() -> dict:
    return {"phase": PHASE, "name": NAME, "application": APPLICATION, "features": list(FEATURES)}
