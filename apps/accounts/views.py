"""
Accounts Application Views.
Implements secure class-based views for Authentication, Registration, Dashboard, Profile, and RBAC Audit.
"""
from django.contrib import messages
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView, ListView, CreateView, UpdateView

from apps.accounts.models import User, UserProfile, Role, LoginHistory, AccountLockoutAudit
from apps.accounts.forms import (
    EnterpriseLoginForm,
    EnterpriseRegistrationForm,
    UserProfileForm,
    EnterprisePasswordChangeForm,
    EnterprisePasswordResetForm,
    EnterpriseSetPasswordForm,
    AdminUserCreateForm,
    AdminUserEditForm,
)
from apps.accounts.services import (
    AuthenticationService,
    TokenService,
    LockoutService,
)
from apps.accounts.permissions import RoleRequiredMixin, AdminRequiredMixin, is_admin, is_customer, is_employee
from enterpriseone.configuration.constants import AccountStatus, LoginStatus
from enterpriseone.configuration.roles import SystemRole


class EnterpriseLoginView(View):
    """
    Renders login interface and processes authentication requests with lockout and audit tracking.
    Enforces server-side role-based redirection to Admin, Employee, or Customer dashboards.
    """
    template_name = "accounts/login.html"

    def get_success_url(self, user):
        """Determine dashboard destination from the authenticated account's role."""
        if getattr(user, "is_admin", False):
            return reverse("accounts:dashboard")
        if getattr(user, "is_employee", False):
            return reverse("employee:dashboard")
        return reverse("customer:dashboard")

    def is_safe_redirect(self, user, next_url: str) -> bool:
        """Validate destination against role boundaries to prevent privilege escalation."""
        if not next_url or not next_url.startswith("/"):
            return False
        if getattr(user, "is_customer", False):
            return next_url.startswith(("/customer/", "/accounts/profile/", "/accounts/logout/"))
        if not getattr(user, "is_admin", False):
            if next_url.startswith(("/admin/", "/security/", "/monitoring/", "/integration/")):
                return False
        return True

    def get(self, request):
        if request.user.is_authenticated:
            return redirect(self.get_success_url(request.user))
        form = EnterpriseLoginForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        if request.user.is_authenticated:
            return redirect(self.get_success_url(request.user))

        form = EnterpriseLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get("email")
            password = form.cleaned_data.get("password")
            remember_me = form.cleaned_data.get("remember_me")

            user, error_msg = AuthenticationService.authenticate_and_login(
                request=request, email=email, password=password, remember_me=remember_me
            )
            if user:
                messages.success(request, f"Welcome back, {user.get_full_name()}!")
                next_url = request.GET.get("next") or request.POST.get("next")
                if next_url and self.is_safe_redirect(user, next_url):
                    return redirect(next_url)
                return redirect(self.get_success_url(user))
            else:
                messages.error(request, error_msg)
        return render(request, self.template_name, {"form": form})


class EnterpriseLogoutView(View):
    """
    Terminates user session, logs logout event, and redirects to login.
    """
    def get(self, request):
        if request.user.is_authenticated:
            LoginHistory.objects.create(
                user=request.user,
                email_attempted=request.user.email,
                status=LoginStatus.LOGOUT,
                ip_address=getattr(request, "client_ip", None),
                user_agent=getattr(request, "client_user_agent", ""),
            )
            logout(request)
            messages.info(request, "You have been successfully logged out.")
        return redirect("accounts:login")

    def post(self, request):
        return self.get(request)


class EnterpriseRegisterView(View):
    """
    Processes self-service registration and triggers activation token generation.
    Strictly creates customer client accounts.
    """
    template_name = "accounts/register.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("customer:dashboard")
        form = EnterpriseRegistrationForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        if request.user.is_authenticated:
            return redirect("customer:dashboard")

        form = EnterpriseRegistrationForm(request.POST)
        if form.is_valid():
            user = AuthenticationService.register_user(
                email=form.cleaned_data["email"],
                password=form.cleaned_data["password"],
                first_name=form.cleaned_data["first_name"],
                last_name=form.cleaned_data["last_name"],
                phone=form.cleaned_data.get("phone", ""),
                job_title=form.cleaned_data.get("job_title", ""),
                role="CUSTOMER",
                request=request,
            )
            messages.success(
                request,
                "Registration successful! Please check your email to activate your account before logging in.",
            )
            return redirect("accounts:login")
        return render(request, self.template_name, {"form": form})


class ActivateAccountView(View):
    """
    Validates activation token from email link and transitions account to verified state.
    """
    def get(self, request, uidb64, token):
        user = TokenService.verify_activation_token(uidb64, token)
        if user:
            user.is_verified = True
            user.account_status = AccountStatus.ACTIVE
            user.save(update_fields=["is_verified", "account_status"])
            messages.success(request, "Your account has been successfully verified! You may now log in.")
        else:
            messages.error(request, "The activation link is invalid or has expired. Please request a new activation link.")
        return redirect("accounts:login")


class EnterprisePasswordResetView(View):
    """
    Dispatches password reset instructions via HMAC-signed token.
    """
    template_name = "accounts/password_reset.html"

    def get(self, request):
        form = EnterprisePasswordResetForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = EnterprisePasswordResetForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            user = User.objects.filter(email__iexact=email).first()
            if user:
                uidb64, token = TokenService.generate_password_reset_token(user)
                reset_url = request.build_absolute_uri(
                    reverse("accounts:password_reset_confirm", kwargs={"uidb64": uidb64, "token": token})
                )
                subject = "Reset your EnterpriseOne Password"
                message = (
                    f"Hello {user.get_full_name()},\n\n"
                    f"A password reset was requested for your account. Click the link below to set a new password:\n\n"
                    f"{reset_url}\n\n"
                    f"This link is valid for 24 hours. If you did not request this, please contact security immediately.\n\n"
                    f"— The EnterpriseOne Security Team"
                )
                try:
                    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)
                except Exception:
                    pass

            messages.success(
                request,
                "If an account exists with the provided email, password reset instructions have been sent.",
            )
            return redirect("accounts:login")
        return render(request, self.template_name, {"form": form})


class EnterprisePasswordResetConfirmView(View):
    """
    Handles new password entry after verifying reset token.
    """
    template_name = "accounts/password_reset_confirm.html"

    def get(self, request, uidb64, token):
        user = TokenService.verify_password_reset_token(uidb64, token)
        if not user:
            messages.error(request, "The password reset link is invalid or has expired.")
            return redirect("accounts:password_reset")
        form = EnterpriseSetPasswordForm(user=user)
        return render(request, self.template_name, {"form": form, "validlink": True})

    def post(self, request, uidb64, token):
        user = TokenService.verify_password_reset_token(uidb64, token)
        if not user:
            messages.error(request, "The password reset link is invalid or has expired.")
            return redirect("accounts:password_reset")

        form = EnterpriseSetPasswordForm(user=user, data=request.POST)
        if form.is_valid():
            user.set_password(form.cleaned_data["new_password"])
            user.last_password_change = timezone.now()
            user.failed_login_attempts = 0
            user.locked_until = None
            user.save(update_fields=["password", "last_password_change", "failed_login_attempts", "locked_until"])
            messages.success(request, "Your password has been reset successfully! You can now log in.")
            return redirect("accounts:login")
        return render(request, self.template_name, {"form": form, "validlink": True})


class DashboardView(LoginRequiredMixin, TemplateView):
    """
    Executive Admin Dashboard showing platform KPIs, role status, and recent activity.
    Restricted to ADMIN tier.
    """
    template_name = "dashboard/index.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("accounts:login")
        if not request.user.is_admin:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("Access Forbidden: Administrative authorization required.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["total_users_count"] = User.objects.count()
        context["active_users_count"] = User.objects.filter(is_active=True).count()
        context["roles_count"] = Role.objects.count()
        context["recent_logins"] = LoginHistory.objects.filter(user=user)[:5]
        context["system_recent_logins"] = LoginHistory.objects.select_related("user")[:10] if user.is_superuser else []

        # Platform domain summaries
        try:
            from apps.organizations.models import Organization
            context["total_orgs_count"] = Organization.objects.count()
        except Exception:
            context["total_orgs_count"] = 1

        try:
            from apps.crm.models import Account, Deal
            context["total_crm_accounts"] = Account.objects.count()
            context["active_deals_count"] = Deal.objects.filter(is_closed=False).count()
        except Exception:
            pass

        try:
            from apps.sales.models import SalesOrder
            from django.db.models import Sum
            from decimal import Decimal
            context["total_orders_count"] = SalesOrder.objects.count()
            context["total_revenue"] = SalesOrder.objects.exclude(status="CANCELLED").aggregate(total=Sum("grand_total"))["total"] or Decimal("0.00")
        except Exception:
            context["total_revenue"] = "0.00"

        try:
            from apps.inventory.models import StockItem
            context["total_inventory_items"] = StockItem.objects.count()
        except Exception:
            context["total_inventory_items"] = 0

        try:
            from apps.projects.models import Project
            context["active_projects_count"] = Project.objects.filter(status="ACTIVE").count()
        except Exception:
            context["active_projects_count"] = 0

        try:
            from apps.support.models import SupportTicket
            context["open_tickets_count"] = SupportTicket.objects.exclude(status__in=["RESOLVED", "CLOSED"]).count()
        except Exception:
            pass

        return context


class UserProfileView(LoginRequiredMixin, View):
    """
    View and edit user profile preferences and details.
    """
    template_name = "accounts/profile.html"

    def get(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        form = UserProfileForm(instance=profile, user=request.user)
        return render(request, self.template_name, {"form": form, "profile": profile})

    def post(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        form = UserProfileForm(request.POST, instance=profile, user=request.user)
        if form.is_valid():
            user = request.user
            user.first_name = form.cleaned_data.get("first_name", user.first_name)
            user.last_name = form.cleaned_data.get("last_name", user.last_name)
            user.phone = form.cleaned_data.get("phone", user.phone)
            user.job_title = form.cleaned_data.get("job_title", user.job_title)
            user.save()

            form.save()
            messages.success(request, "Your profile preferences have been updated successfully.")
            return redirect("accounts:profile")
        return render(request, self.template_name, {"form": form, "profile": profile})


class EnterprisePasswordChangeView(LoginRequiredMixin, View):
    """
    Secure password change for authenticated users.
    """
    template_name = "accounts/password_change.html"

    def get(self, request):
        form = EnterprisePasswordChangeForm(user=request.user)
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = EnterprisePasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            new_password = form.cleaned_data["new_password"]
            request.user.set_password(new_password)
            request.user.last_password_change = timezone.now()
            request.user.save(update_fields=["password", "last_password_change"])
            update_session_auth_hash(request, request.user)
            messages.success(request, "Your password has been changed successfully.")
            return redirect("accounts:profile")
        return render(request, self.template_name, {"form": form})


class SecurityAuditView(LoginRequiredMixin, ListView):
    """
    Displays the authenticated user's login history and security events.
    """
    template_name = "accounts/security_audit.html"
    context_object_name = "history_entries"
    paginate_by = 25

    def get_queryset(self):
        return LoginHistory.objects.filter(user=self.request.user).order_by("-timestamp")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["lockout_audits"] = AccountLockoutAudit.objects.filter(user=self.request.user)[:10]
        return context


class UserListView(RoleRequiredMixin, ListView):
    """
    Administrative list of enterprise users with role filters and lockout status.
    """
    template_name = "accounts/user_list.html"
    model = User
    context_object_name = "users"
    paginate_by = 20
    required_roles = [SystemRole.ADMIN, SystemRole.SUPER_ADMIN, SystemRole.ORG_ADMIN]

    def get_queryset(self):
        qs = User.objects.all().prefetch_related("user_roles__role").order_by("-created_at")
        query = self.request.GET.get("q")
        role_filter = self.request.GET.get("role")
        if query:
            qs = qs.filter(email__icontains=query) | qs.filter(first_name__icontains=query) | qs.filter(last_name__icontains=query)
        if role_filter:
            qs = qs.filter(role=role_filter)
        return qs


class AdminUserCreateView(AdminRequiredMixin, View):
    """
    Administrative action to provision a new user with explicit role and organization assignment.
    """
    template_name = "accounts/user_form.html"

    def get(self, request):
        form = AdminUserCreateForm()
        return render(request, self.template_name, {"form": form, "title": "Create User"})

    def post(self, request):
        form = AdminUserCreateForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            password = form.cleaned_data["password"]
            user.set_password(password)
            user.save()
            user.set_role(user.role, actor=request.user, reason="Provisioned by Admin")
            messages.success(request, f"User {user.email} with role {user.role} was created successfully.")
            return redirect("accounts:user_list")
        return render(request, self.template_name, {"form": form, "title": "Create User"})


class AdminUserEditView(AdminRequiredMixin, View):
    """
    Administrative action to edit user details and change application role.
    """
    template_name = "accounts/user_form.html"

    def get(self, request, user_id):
        target_user = get_object_or_404(User, pk=user_id)
        form = AdminUserEditForm(instance=target_user)
        return render(request, self.template_name, {"form": form, "title": f"Edit User: {target_user.email}", "target_user": target_user})

    def post(self, request, user_id):
        target_user = get_object_or_404(User, pk=user_id)
        old_role = target_user.role
        form = AdminUserEditForm(request.POST, instance=target_user)
        if form.is_valid():
            updated_user = form.save()
            if updated_user.role != old_role:
                updated_user.set_role(updated_user.role, actor=request.user, reason=f"Role changed by {request.user.email}")
            messages.success(request, f"User {updated_user.email} updated successfully.")
            return redirect("accounts:user_list")
        return render(request, self.template_name, {"form": form, "title": f"Edit User: {target_user.email}", "target_user": target_user})


class AdminUserToggleStatusView(AdminRequiredMixin, View):
    """
    Administrative action to activate or deactivate a user account.
    """
    def post(self, request, user_id):
        target_user = get_object_or_404(User, pk=user_id)
        if target_user == request.user:
            messages.error(request, "You cannot deactivate your own administrative account.")
            return redirect("accounts:user_list")

        target_user.is_active = not target_user.is_active
        target_user.account_status = AccountStatus.ACTIVE if target_user.is_active else AccountStatus.DEACTIVATED
        target_user.save(update_fields=["is_active", "account_status", "updated_at"])

        # Audit event
        try:
            from apps.security.services import AuditService, SecurityEventService
            AuditService.record(
                actor=request.user,
                action="UPDATE",
                instance=target_user,
                after={"is_active": target_user.is_active, "account_status": target_user.account_status},
                reason="Account active status toggled by admin",
            )
            SecurityEventService.emit(
                event_type="ACCOUNT_DISABLED" if not target_user.is_active else "ACCOUNT_ENABLED",
                user=target_user,
                severity="HIGH" if not target_user.is_active else "INFO",
                outcome="SUCCESS",
                action="toggle_status",
                resource=target_user,
            )
        except Exception:
            pass

        state_str = "activated" if target_user.is_active else "deactivated"
        messages.success(request, f"User {target_user.email} has been {state_str}.")
        return redirect("accounts:user_list")


class UnlockUserView(RoleRequiredMixin, View):
    """
    Administrative action to release an account lockout.
    """
    required_roles = [SystemRole.ADMIN, SystemRole.SUPER_ADMIN, SystemRole.ORG_ADMIN]

    def post(self, request, user_id):
        target_user = get_object_or_404(User, pk=user_id)
        LockoutService.unlock_user(target_user, unlocked_by=request.user)
        messages.success(request, f"User account {target_user.email} has been unlocked successfully.")
        return redirect("accounts:user_list")