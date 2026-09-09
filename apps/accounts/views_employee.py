"""
Employee Domain Views.
Operational workspace for enterprise employees showing assigned tasks, tickets, attendance, and department KPIs.
"""
from django.views.generic import TemplateView
from django.shortcuts import redirect
from django.utils import timezone
from apps.accounts.permissions import EmployeeRequiredMixin, is_customer, is_admin


class EmployeeDashboardView(EmployeeRequiredMixin, TemplateView):
    """
    Operational Enterprise Dashboard tailored to enterprise staff and managers.
    """
    template_name = "employee/dashboard.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("accounts:login")
        if is_customer(request.user) and not is_admin(request.user):
            return redirect("customer:dashboard")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Employee profile from HR module
        employee_record = getattr(user, "employee_record", None)
        context["employee_record"] = employee_record
        context["org_member"] = getattr(self.request, "organization_member", None)

        # Assigned tasks
        try:
            from apps.projects.models import ProjectTask
            context["my_tasks"] = ProjectTask.objects.filter(assignee=user).exclude(status__in=["done", "completed"]).order_by("due_date")[:6]
            context["total_assigned_tasks"] = ProjectTask.objects.filter(assignee=user).exclude(status__in=["done", "completed"]).count()
        except Exception:
            context["my_tasks"] = []
            context["total_assigned_tasks"] = 0

        # Assigned support tickets
        try:
            from apps.support.models import SupportTicket
            context["my_tickets"] = SupportTicket.objects.filter(assignee=user).exclude(status__in=["resolved", "closed", "RESOLVED", "CLOSED"]).order_by("-created_at")[:6]
            context["total_assigned_tickets"] = SupportTicket.objects.filter(assignee=user).exclude(status__in=["resolved", "closed", "RESOLVED", "CLOSED"]).count()
        except Exception:
            context["my_tickets"] = []
            context["total_assigned_tickets"] = 0

        # HR Attendance & Leave
        try:
            from apps.hr.models import AttendanceRecord, LeaveBalance, LeaveRequest
            if employee_record:
                context["attendance_recent"] = AttendanceRecord.objects.filter(employee=employee_record).order_by("-work_date")[:5]
                context["leave_balance"] = LeaveBalance.objects.filter(employee=employee_record).first()
                context["pending_leave_requests"] = LeaveRequest.objects.filter(employee=employee_record, status="PENDING")
            else:
                context["attendance_recent"] = []
                context["leave_balance"] = None
                context["pending_leave_requests"] = []
        except Exception:
            pass

        # Department operations & Sales activity
        try:
            from apps.sales.models import SalesOrder, Quote
            context["recent_orders"] = SalesOrder.objects.all().order_by("-created_at")[:5]
            context["recent_quotes"] = Quote.objects.all().order_by("-created_at")[:5]
        except Exception:
            pass

        # Notifications
        try:
            from apps.notifications.models import Notification
            context["unread_notifications_count"] = Notification.objects.filter(recipient=user, is_read=False).count()
            context["recent_notifications"] = Notification.objects.filter(recipient=user).order_by("-created_at")[:5]
        except Exception:
            context["unread_notifications_count"] = 0
            context["recent_notifications"] = []

        return context
