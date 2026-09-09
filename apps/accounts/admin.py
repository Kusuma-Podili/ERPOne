"""
Django Administration Configuration for Accounts.
Provides rich administrative interfaces for User, UserProfile, Role, Permission, and Audit models.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from apps.accounts.models import (
    User,
    UserProfile,
    Role,
    Permission,
    UserRole,
    RolePermission,
    LoginHistory,
    AccountLockoutAudit,
)


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = "Profile Details"
    fk_name = "user"


class UserRoleInline(admin.TabularInline):
    model = UserRole
    extra = 1
    fk_name = "user"
    autocomplete_fields = ["role"]


class RolePermissionInline(admin.TabularInline):
    model = RolePermission
    extra = 1
    fk_name = "role"
    autocomplete_fields = ["permission"]


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "email",
        "first_name",
        "last_name",
        "account_status",
        "is_active",
        "is_staff",
        "failed_login_attempts",
        "is_locked",
        "created_at",
    )
    list_filter = ("account_status", "is_active", "is_staff", "is_superuser", "created_at")
    search_fields = ("email", "first_name", "last_name", "phone")
    ordering = ("-created_at",)
    inlines = [UserProfileInline, UserRoleInline]

    fieldsets = (
        (_("Authentication Credentials"), {"fields": ("email", "password")}),
        (
            _("Personal Information"),
            {"fields": ("first_name", "last_name", "phone", "job_title", "avatar")},
        ),
        (
            _("Permissions & Access"),
            {
                "fields": (
                    "account_status",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "is_verified",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            _("Security & Lockout Audit"),
            {
                "fields": (
                    "failed_login_attempts",
                    "locked_until",
                    "force_password_change",
                    "last_password_change",
                )
            },
        ),
        (_("Timestamps"), {"fields": ("last_login", "created_at", "updated_at")}),
    )
    readonly_fields = ("last_login", "created_at", "updated_at", "last_password_change")

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "first_name", "last_name", "password"),
            },
        ),
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "priority", "is_system_role", "created_at")
    list_filter = ("is_system_role",)
    search_fields = ("name", "code", "description")
    ordering = ("-priority", "name")
    inlines = [RolePermissionInline]


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "module", "action", "created_at")
    list_filter = ("module", "action")
    search_fields = ("code", "name", "module", "description")
    ordering = ("module", "code")


@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    list_display = ("email_attempted", "status", "ip_address", "timestamp")
    list_filter = ("status", "timestamp")
    search_fields = ("email_attempted", "ip_address", "failure_reason")
    readonly_fields = ("id", "user", "email_attempted", "status", "ip_address", "user_agent", "failure_reason", "timestamp")
    ordering = ("-timestamp",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(AccountLockoutAudit)
class AccountLockoutAuditAdmin(admin.ModelAdmin):
    list_display = ("user", "locked_at", "unlocked_at", "duration_minutes", "reason", "ip_address")
    list_filter = ("locked_at", "unlocked_at")
    search_fields = ("user__email", "reason", "ip_address")
    readonly_fields = ("id", "user", "locked_at", "reason", "ip_address")
    ordering = ("-locked_at",)
