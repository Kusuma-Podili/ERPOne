"""
Employee Domain URL Routing.
Provides employee operational dashboard and operational workflows.
"""
from django.urls import path
from apps.accounts.views_employee import EmployeeDashboardView

app_name = "employee"

urlpatterns = [
    path("", EmployeeDashboardView.as_view(), name="dashboard"),
]
