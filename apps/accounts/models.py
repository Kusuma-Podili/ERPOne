"""
Enterprise Accounts & Role-Based Access Control Models.
Defines User, UserProfile, Role, Permission, LoginHistory, and AccountLockoutAudit entities.
"""
import uuid
from datetime import timedelta
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from enterpriseone.configuration.constants import AccountStatus, LoginStatus, ThemePreference
from enterpriseone.configuration.roles import SystemRole, ROLE_METADATA
from apps.accounts.managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom Enterprise User model identified by unique email and UUID.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_("Email Address"), unique=True, db_index=True, max_length=255)
    first_name = models.CharField(_("First Name"), max_length=150, blank=True)
    last_name = models.CharField(_("Last Name"), max_length=150, blank=True)
    phone = models.CharField(_("Phone Number"), max_length=30, blank=True)
    job_title = models.CharField(_("Job Title"), max_length=100, blank=True)
    avatar = models.ImageField(_("Avatar"), upload_to="avatars/%Y/%m/", blank=True, null=True)

    # Status & Flags
    account_status = models.CharField(
        _("Account Status"),
        max_length=30,
        choices=AccountStatus.CHOICES,
        default=AccountStatus.ACTIVE,
        db_index=True,
    )
    is_active = models.BooleanField(_("Active"), default=True)
    is_staff = models.BooleanField(_("Staff Status"), default=False)
    is_superuser = models.BooleanField(_("Superuser Status"), default=False)
    is_verified = models.BooleanField(_("Email Verified"), default=False)

    # Security & Lockout Tracking
    failed_login_attempts = models.PositiveIntegerField(_("Failed Login Attempts"), default=0)
    locked_until = models.DateTimeField(_("Locked Until"), null=True, blank=True, db_index=True)
    last_password_change = models.DateTimeField(_("Last Password Change"), default=timezone.now)
    force_password_change = models.BooleanField(_("Force Password Change"), default=False)

    # Timestamps
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email", "account_status"]),
            models.Index(fields=["locked_until"]),
        ]

    def __str__(self):
        return f"{self.email} ({self.get_full_name() or 'User'})"

    def get_full_name(self) -> str:
        """Return trimmed first and last name."""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.email

    def get_short_name(self) -> str:
        """Return first name or email prefix."""
        return self.first_name or self.email.split("@")[0]

    @property
    def is_locked(self) -> bool:
        """Check whether the account is currently in a locked state."""
        if self.locked_until and self.locked_until > timezone.now():
            return True
        return False

    @property
    def primary_role(self):
        """Retrieve highest priority assigned role."""
        assignment = self.user_roles.select_related("role").order_by("-role__priority").first()
        return assignment.role if assignment else None

    @property
    def display_role(self) -> str:
        """Formatted role title for UI display."""
        if self.is_superuser:
            return "Super Administrator"
        role = self.primary_role
        return role.name if role else "Employee"

    def has_role(self, role_code: str) -> bool:
        """Check if user is assigned a specific role code or has superuser override."""
        if self.is_superuser:
            return True
        return self.user_roles.filter(role__code=role_code).exists()

    def get_roles(self):
        """Retrieve QuerySet of all assigned roles."""
        return Role.objects.filter(role_assignments__user=self)

    def get_permissions_list(self) -> set[str]:
        """Retrieve all permission codes across all assigned roles."""
        if self.is_superuser:
            return set(Permission.objects.values_list("code", flat=True))
        return set(
            Permission.objects.filter(
                permission_roles__role__role_assignments__user=self
            ).values_list("code", flat=True)
        )

    def has_enterprise_perm(self, perm_code: str) -> bool:
        """Granular permission verification."""
        if self.is_superuser:
            return True
        return perm_code in self.get_permissions_list()

    def record_login_success(self, ip_address: str = None, user_agent: str = ""):
        """Reset failed login counters and audit successful login."""
        self.failed_login_attempts = 0
        self.locked_until = None
        if self.account_status == AccountStatus.LOCKED:
            self.account_status = AccountStatus.ACTIVE
        self.save(update_fields=["failed_login_attempts", "locked_until", "account_status"])

        LoginHistory.objects.create(
            user=self,
            email_attempted=self.email,
            status=LoginStatus.SUCCESS,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    def record_login_failure(self, ip_address: str = None, user_agent: str = "", reason: str = "Invalid credentials"):
        """Increment failed attempts and trigger lockout if threshold is exceeded."""
        self.failed_login_attempts += 1
        max_attempts = getattr(settings, "AUTH_MAX_LOGIN_ATTEMPTS", 5)
        lockout_minutes = getattr(settings, "AUTH_LOCKOUT_DURATION_MINUTES", 15)

        status = LoginStatus.FAILED_INVALID_CREDENTIALS

        if self.failed_login_attempts >= max_attempts:
            self.locked_until = timezone.now() + timedelta(minutes=lockout_minutes)
            self.account_status = AccountStatus.LOCKED
            status = LoginStatus.FAILED_ACCOUNT_LOCKED

            AccountLockoutAudit.objects.create(
                user=self,
                duration_minutes=lockout_minutes,
                reason=f"Exceeded {max_attempts} failed login attempts: {reason}",
                ip_address=ip_address,
            )

        self.save(update_fields=["failed_login_attempts", "locked_until", "account_status"])

        LoginHistory.objects.create(
            user=self,
            email_attempted=self.email,
            status=status,
            ip_address=ip_address,
            user_agent=user_agent,
            failure_reason=reason,
        )

    def unlock_account(self, unlocked_by=None, reason: str = "Administrative unlock"):
        """Reset lockout status manually."""
        self.failed_login_attempts = 0
        self.locked_until = None
        if self.account_status == AccountStatus.LOCKED:
            self.account_status = AccountStatus.ACTIVE
        self.save(update_fields=["failed_login_attempts", "locked_until", "account_status"])

        audit = self.lockout_audits.filter(unlocked_at__isnull=True).order_by("-locked_at").first()
        if audit:
            audit.unlocked_at = timezone.now()
            audit.unlocked_by = unlocked_by
            audit.save(update_fields=["unlocked_at", "unlocked_by"])


class UserProfile(models.Model):
    """
    User Preferences, Locale, and Organizational Profile settings.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    timezone = models.CharField(_("Timezone"), max_length=50, default="UTC")
    language = models.CharField(_("Language"), max_length=10, default="en")
    theme = models.CharField(
        _("Theme"),
        max_length=20,
        choices=ThemePreference.CHOICES,
        default=ThemePreference.SYSTEM,
    )
    bio = models.TextField(_("Biography"), blank=True)
    department_name = models.CharField(_("Department Name"), max_length=100, blank=True)
    notification_email = models.BooleanField(_("Email Notifications"), default=True)
    notification_inapp = models.BooleanField(_("In-App Notifications"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("User Profile")
        verbose_name_plural = _("User Profiles")

    def __str__(self):
        return f"Profile: {self.user.email}"


class Role(models.Model):
    """
    Enterprise Role entity defining authorization privileges and priorities.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(_("Role Code"), max_length=50, unique=True, db_index=True)
    name = models.CharField(_("Role Name"), max_length=100)
    description = models.TextField(_("Description"), blank=True)
    priority = models.PositiveIntegerField(_("Priority Level"), default=10, db_index=True)
    is_system_role = models.BooleanField(_("System Built-in Role"), default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Role")
        verbose_name_plural = _("Roles")
        ordering = ["-priority", "name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class Permission(models.Model):
    """
    Fine-grained permission action mapped to application modules.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(_("Permission Code"), max_length=100, unique=True, db_index=True)
    name = models.CharField(_("Permission Name"), max_length=150)
    module = models.CharField(_("Module"), max_length=50, db_index=True)
    action = models.CharField(_("Action"), max_length=50)
    description = models.TextField(_("Description"), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Permission")
        verbose_name_plural = _("Permissions")
        ordering = ["module", "code"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class UserRole(models.Model):
    """
    Explicit user-to-role assignment junction with audit trail.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_roles")
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="role_assignments")
    assigned_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_roles"
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("User Role Assignment")
        verbose_name_plural = _("User Role Assignments")
        unique_together = ("user", "role")

    def __str__(self):
        return f"{self.user.email} -> {self.role.code}"


class RolePermission(models.Model):
    """
    Explicit role-to-permission mapping junction.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="role_permissions")
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name="permission_roles")
    granted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Role Permission Mapping")
        verbose_name_plural = _("Role Permission Mappings")
        unique_together = ("role", "permission")

    def __str__(self):
        return f"{self.role.code} -> {self.permission.code}"


class LoginHistory(models.Model):
    """
    Audit log of all login attempts and session terminations.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, blank=True, related_name="login_history"
    )
    email_attempted = models.EmailField(_("Attempted Email"), max_length=255, db_index=True)
    status = models.CharField(_("Login Status"), max_length=50, choices=LoginStatus.CHOICES)
    ip_address = models.GenericIPAddressField(_("IP Address"), null=True, blank=True)
    user_agent = models.CharField(_("User Agent"), max_length=500, blank=True)
    failure_reason = models.CharField(_("Failure Reason"), max_length=255, blank=True)
    timestamp = models.DateTimeField(_("Timestamp"), auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("Login History")
        verbose_name_plural = _("Login Histories")
        ordering = ["-timestamp"]

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M:%S}] {self.email_attempted} - {self.status}"


class AccountLockoutAudit(models.Model):
    """
    Audit records for automated and manual account lockouts and unlocks.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="lockout_audits")
    locked_at = models.DateTimeField(_("Locked At"), auto_now_add=True, db_index=True)
    unlocked_at = models.DateTimeField(_("Unlocked At"), null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(_("Duration (Minutes)"), default=15)
    reason = models.CharField(_("Lockout Reason"), max_length=255)
    ip_address = models.GenericIPAddressField(_("Triggering IP"), null=True, blank=True)
    unlocked_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="unlocked_accounts"
    )

    class Meta:
        verbose_name = _("Account Lockout Audit")
        verbose_name_plural = _("Account Lockout Audits")
        ordering = ["-locked_at"]

    def __str__(self):
        return f"Lockout: {self.user.email} at {self.locked_at:%Y-%m-%d %H:%M:%S}"
