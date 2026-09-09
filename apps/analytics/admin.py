from django.contrib import admin
from .models import *
for model in [MetricDefinition,KPI,Dashboard,DashboardPermission,DashboardWidget,Report,ReportRun,ReportSchedule,AnalyticsSnapshot,AnalyticsAlert,AnalyticsAuditEvent]:
    admin.site.register(model)
