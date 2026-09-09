"""
Role-Based Access Control (RBAC) Permissions, Decorators, and Mixins.
Enforces multi-role authorization boundaries across ADMIN, EMPLOYEE, and CUSTOMER tiers.
"""
from functools import wraps
from typing import Sequence
from django.contrib import messages
from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from enterpriseone.configuration.roles import SystemRole


def is_admin(user) -> bool:
    """Check if the user has administrative authority."""
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "is_superuser", False):
        return True
    if getattr(user, "role", "") == "ADMIN":
        return True
    return user.has_role(SystemRole.ADMIN) or user.has_role(SystemRole.SUPER_ADMIN) or user.has_role(SystemRole.ORG_ADMIN)


def is_customer(user) -> bool:
    """Check if the user is a customer client."""
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "is_superuser", False) or getattr(user, "role", "") in ("ADMIN", "AppRole.ADMIN"):
        return False
    if getattr(user, "role", "") == "CUSTOMER":
        return True
    if hasattr(user, "user_roles"):
        return user.user_roles.filter(role__code=SystemRole.CUSTOMER).exists()
    return False


def is_employee(user) -> bool:
    """Check if the user is an enterprise employee."""
    if not user or not user.is_authenticated:
        return False
    if is_customer(user):
        return False
    if is_admin(user):
        return True
    return getattr(user, "role", "") == "EMPLOYEE" or user.has_role(SystemRole.EMPLOYEE)


# Module Level Permission Checkers
def can_view_crm(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    if is_admin(user):
        return True
    return is_employee(user) and (
        user.has_enterprise_perm("crm.view")
        or user.has_role(SystemRole.SALES_USER)
        or user.has_role(SystemRole.MANAGER)
        or user.has_role(SystemRole.EMPLOYEE)
    )


def can_edit_sales(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    if is_admin(user):
        return True
    return is_employee(user) and (
        user.has_enterprise_perm("sales.edit")
        or user.has_role(SystemRole.SALES_USER)
        or user.has_role(SystemRole.MANAGER)
    )


def can_manage_inventory(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    if is_admin(user):
        return True
    return is_employee(user) and (
        user.has_enterprise_perm("inventory.manage")
        or user.has_role(SystemRole.INVENTORY_USER)
        or user.has_role(SystemRole.MANAGER)
    )


def can_view_finance(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    if is_admin(user):
        return True
    return is_employee(user) and (
        user.has_enterprise_perm("finance.view")
        or user.has_role(SystemRole.FINANCE_USER)
        or user.has_role(SystemRole.MANAGER)
    )


def can_manage_hr(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    if is_admin(user):
        return True
    return is_employee(user) and (
        user.has_enterprise_perm("hr.manage")
        or user.has_role(SystemRole.HR_USER)
        or user.has_role(SystemRole.MANAGER)
    )


def can_manage_security(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    return is_admin(user) or user.has_enterprise_perm("security.manage")


# Role Decorators
def admin_required(view_func):
    """View decorator restricting access strictly to Admins and Superusers."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("accounts:login")
        if is_admin(request.user):
            return view_func(request, *args, **kwargs)
        raise PermissionDenied("Administrative authorization required.")
    return _wrapped


def employee_required(view_func):
    """View decorator restricting access to authenticated Employees and Admins."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("accounts:login")
        if is_employee(request.user) or is_admin(request.user):
            return view_func(request, *args, **kwargs)
        raise PermissionDenied("Employee authorization required.")
    return _wrapped


def customer_required(view_func):
    """View decorator restricting access to Customers and Admins."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("accounts:login")
        if is_customer(request.user) or is_admin(request.user):
            return view_func(request, *args, **kwargs)
        raise PermissionDenied("Customer portal authorization required.")
    return _wrapped


def require_role(roles: Sequence[str] | str, redirect_url: str = None):
    """Decorator checking if a user holds at least one of the specified roles."""
    if isinstance(roles, str):
        roles = [roles]

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("accounts:login")

            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            user_role_codes = set(request.user.user_roles.values_list("role__code", flat=True))
            if getattr(request.user, "role", ""):
                user_role_codes.add(request.user.role)

            if any(role in user_role_codes for role in roles):
                return view_func(request, *args, **kwargs)

            messages.error(request, "Access denied. You do not possess the required role permissions.")
            if redirect_url:
                return redirect(redirect_url)
            if is_admin(request.user):
                return redirect("accounts:dashboard")
            elif is_customer(request.user):
                return redirect("customer:dashboard")
            return redirect("employee:dashboard")

        return _wrapped_view

    return decorator


def require_permission(permissions: Sequence[str] | str, redirect_url: str = None):
    """Decorator checking if a user holds required granular permission codes."""
    if isinstance(permissions, str):
        permissions = [permissions]

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("accounts:login")

            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            user_perms = request.user.get_permissions_list()
            if all(perm in user_perms for perm in permissions):
                return view_func(request, *args, **kwargs)

            messages.error(request, "Access denied. You lack required operational permissions.")
            if redirect_url:
                return redirect(redirect_url)
            if is_admin(request.user):
                return redirect("accounts:dashboard")
            elif is_customer(request.user):
                return redirect("customer:dashboard")
            return redirect("employee:dashboard")

        return _wrapped_view

    return decorator


# Class-Based View Mixins
class AdminRequiredMixin(AccessMixin):
    """CBV mixin enforcing Admin status."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not is_admin(request.user):
            raise PermissionDenied("Administrative authorization required.")
        return super().dispatch(request, *args, **kwargs)


class EmployeeRequiredMixin(AccessMixin):
    """CBV mixin enforcing Employee or Admin status."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if is_customer(request.user) and not is_admin(request.user):
            raise PermissionDenied("Employee authorization required.")
        return super().dispatch(request, *args, **kwargs)


class CustomerRequiredMixin(AccessMixin):
    """CBV mixin enforcing Customer status (or Admin override)."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not is_customer(request.user) and not is_admin(request.user):
            raise PermissionDenied("Customer portal authorization required.")
        return super().dispatch(request, *args, **kwargs)


class RoleRequiredMixin(AccessMixin):
    """CBV mixin verifying user holds required roles."""
    required_roles: Sequence[str] = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)

        user_role_codes = set(request.user.user_roles.values_list("role__code", flat=True))
        if getattr(request.user, "role", ""):
            user_role_codes.add(request.user.role)

        if any(role in user_role_codes for role in self.required_roles):
            return super().dispatch(request, *args, **kwargs)

        messages.error(request, "Access denied. You do not possess the required role permissions.")
        if is_admin(request.user):
            return redirect("accounts:dashboard")
        elif is_customer(request.user):
            return redirect("customer:dashboard")
        return redirect("employee:dashboard")


class EnterprisePermissionRequiredMixin(AccessMixin):
    """CBV mixin verifying granular enterprise permissions."""
    required_permissions: Sequence[str] = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)

        user_perms = request.user.get_permissions_list()
        if all(perm in user_perms for perm in self.required_permissions):
            return super().dispatch(request, *args, **kwargs)

        messages.error(request, "Access denied. You lack required operational permissions.")
        if is_admin(request.user):
            return redirect("accounts:dashboard")
        elif is_customer(request.user):
            return redirect("customer:dashboard")
        return redirect("employee:dashboard")
