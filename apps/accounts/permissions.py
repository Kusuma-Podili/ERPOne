"""
Role-Based Access Control (RBAC) Permissions and Decorators.
Provides decorators and class-based view mixins for enforcing role and permission boundaries.
"""
from functools import wraps
from typing import Sequence
from django.contrib import messages
from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


def require_role(roles: Sequence[str] | str, redirect_url: str = "accounts:dashboard"):
    """
    Decorator for views that checks whether a user has at least one of the specified roles.
    """
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
            if any(role in user_role_codes for role in roles):
                return view_func(request, *args, **kwargs)

            messages.error(request, "Access denied. You do not possess the required role permissions.")
            if redirect_url:
                return redirect(redirect_url)
            raise PermissionDenied

        return _wrapped_view

    return decorator


def require_permission(permissions: Sequence[str] | str, redirect_url: str = "accounts:dashboard"):
    """
    Decorator for views checking if a user has the specified granular permission codes.
    """
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
            raise PermissionDenied

        return _wrapped_view

    return decorator


class RoleRequiredMixin(AccessMixin):
    """
    Class-Based View mixin verifying user holds required roles.
    """
    required_roles: Sequence[str] = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)

        user_role_codes = set(request.user.user_roles.values_list("role__code", flat=True))
        if any(role in user_role_codes for role in self.required_roles):
            return super().dispatch(request, *args, **kwargs)

        messages.error(request, "Access denied. You do not possess the required role permissions.")
        return redirect("accounts:dashboard")


class EnterprisePermissionRequiredMixin(AccessMixin):
    """
    Class-Based View mixin verifying granular enterprise permissions.
    """
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
        return redirect("accounts:dashboard")
