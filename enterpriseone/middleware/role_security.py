"""
Role-Based URL Security Middleware.
Enforces strict backend endpoint protection across Admin, Employee, and Customer roles.
Blocks unauthorized cross-role route access with HTTP 403 Forbidden.
"""
from typing import Callable
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import render, redirect
from apps.accounts.permissions import is_admin, is_customer, is_employee


class RoleSecurityMiddleware:
    """
    Guards sensitive enterprise routes against unauthorized access by role tier.
    """
    # System Administration: strictly Admin and Superuser
    ADMIN_PREFIXES = (
        "/admin/",
        "/security/",
        "/monitoring/",
        "/integration/",
    )

    # Operational Enterprise ERP: Employees and Admins (Customers strictly forbidden)
    EMPLOYEE_ENTERPRISE_PREFIXES = (
        "/employee/",
        "/organizations/",
        "/finance/",
        "/hr/",
        "/payroll/",
        "/procurement/",
        "/inventory/",
        "/analytics/",
        "/ai/",
        "/crm/",
        "/sales/",
        "/projects/",
    )

    PUBLIC_OR_SHARED_PREFIXES = (
        "/static/",
        "/media/",
        "/favicon.ico",
        "/accounts/login/",
        "/accounts/logout/",
        "/accounts/register/",
        "/accounts/activate/",
        "/accounts/password-reset/",
        "/accounts/password-reset-confirm/",
        "/accounts/profile/",
        "/customer/",
    )

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        path = request.path

        # Allow public and shared authentication lifecycle routes
        for prefix in self.PUBLIC_OR_SHARED_PREFIXES:
            if path.startswith(prefix):
                return self.get_response(request)

        # Allow non-authenticated requests to reach login/views which handle login_required
        if not hasattr(request, "user") or not request.user.is_authenticated:
            return self.get_response(request)

        user = request.user

        # 1. Check Customer restrictions
        if is_customer(user) and not is_admin(user):
            # Customers are strictly forbidden from Admin and Employee enterprise routes
            if path.startswith(self.ADMIN_PREFIXES) or path.startswith(self.EMPLOYEE_ENTERPRISE_PREFIXES) or path == "/accounts/dashboard/":
                return self._forbidden_response(
                    request,
                    "Access Forbidden: Customer accounts are restricted to the Customer Portal.",
                )

        # 2. Check Employee restrictions
        if is_employee(user) and not is_admin(user):
            # Ordinary employees without administrative credentials cannot access admin systems
            if path.startswith(self.ADMIN_PREFIXES):
                return self._forbidden_response(
                    request,
                    "Access Forbidden: System administration privileges required.",
                )

        return self.get_response(request)

    def _forbidden_response(self, request: HttpRequest, message: str) -> HttpResponse:
        """Render a clean, secure HTTP 403 Forbidden response."""
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>403 Forbidden &bull; EnterpriseOne</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #f8fafc; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }}
        .box {{ background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 2.5rem; max-width: 480px; text-align: center; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }}
        h1 {{ color: #ef4444; font-size: 2rem; margin-top: 0; }}
        p {{ color: #94a3b8; line-height: 1.5; margin-bottom: 1.5rem; }}
        a {{ display: inline-block; background: #3b82f6; color: white; padding: 0.6rem 1.25rem; border-radius: 6px; text-decoration: none; font-weight: 500; }}
        a:hover {{ background: #2563eb; }}
    </style>
</head>
<body>
    <div class="box">
        <h1>403 Forbidden</h1>
        <p>{message}</p>
        <a href="/">Return to Dashboard</a>
    </div>
</body>
</html>"""
        return HttpResponseForbidden(html)
