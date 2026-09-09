"""
Accounts Domain Services.
Encapsulates business logic for Authentication, Lockout Management, Token Generation, and RBAC.
"""
from datetime import timedelta
from typing import Optional, Tuple
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.core.mail import send_mail
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.http import HttpRequest
from django.utils import timezone
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str

from apps.accounts.models import (
    User,
    Role,
    Permission,
    UserRole,
    RolePermission,
    LoginHistory,
    AccountLockoutAudit,
)
from enterpriseone.configuration.constants import AccountStatus, LoginStatus
from enterpriseone.configuration.roles import SystemRole


class TokenService:
    """
    Cryptographic HMAC token service with expiration for account activation and password resets.
    """
    SIGNER_SALT_ACTIVATION = "enterpriseone-account-activation-salt"
    SIGNER_SALT_PASSWORD_RESET = "enterpriseone-password-reset-salt"

    @classmethod
    def generate_activation_token(cls, user: User) -> Tuple[str, str]:
        """Generates a base64 encoded user ID and timestamp-signed activation token."""
        uidb64 = urlsafe_base64_encode(force_bytes(str(user.id)))
        signer = TimestampSigner(salt=cls.SIGNER_SALT_ACTIVATION)
        token = signer.sign(str(user.id))
        return uidb64, token

    @classmethod
    def verify_activation_token(cls, uidb64: str, token: str, max_age_hours: int = 48) -> Optional[User]:
        """Validates an activation token and returns the corresponding User if valid."""
        try:
            user_id = force_str(urlsafe_base64_decode(uidb64))
            signer = TimestampSigner(salt=cls.SIGNER_SALT_ACTIVATION)
            signed_user_id = signer.unsign(token, max_age=max_age_hours * 3600)
            if signed_user_id != user_id:
                return None
            user = User.objects.get(pk=user_id)
            return user
        except (BadSignature, SignatureExpired, User.DoesNotExist, ValueError):
            return None

    @classmethod
    def generate_password_reset_token(cls, user: User) -> Tuple[str, str]:
        """Generates a base64 encoded user ID and timestamp-signed password reset token."""
        import hashlib
        uidb64 = urlsafe_base64_encode(force_bytes(str(user.id)))
        signer = TimestampSigner(salt=cls.SIGNER_SALT_PASSWORD_RESET)
        pwd_fingerprint = hashlib.sha256(user.password.encode()).hexdigest()
        token = signer.sign(f"{user.id}:{pwd_fingerprint}")
        return uidb64, token

    @classmethod
    def verify_password_reset_token(cls, uidb64: str, token: str, max_age_hours: int = 24) -> Optional[User]:
        """Validates a password reset token and ensures the user's password hasn't changed since."""
        import hashlib
        try:
            user_id = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=user_id)
            signer = TimestampSigner(salt=cls.SIGNER_SALT_PASSWORD_RESET)
            original_value = signer.unsign(token, max_age=max_age_hours * 3600)
            pwd_fingerprint = hashlib.sha256(user.password.encode()).hexdigest()
            expected_value = f"{user.id}:{pwd_fingerprint}"
            if original_value != expected_value:
                return None
            return user
        except (BadSignature, SignatureExpired, User.DoesNotExist, ValueError):
            return None


class LockoutService:
    """
    Manages account lockout enforcement, threshold monitoring, and administrative unlock workflows.
    """

    @classmethod
    def is_locked(cls, user: User) -> bool:
        """Determines if a user is currently locked."""
        return user.is_locked

    @classmethod
    def record_failure_and_check_lockout(
        cls, user: User, ip_address: Optional[str] = None, user_agent: str = ""
    ) -> bool:
        """
        Increments failed login attempts and locks account if threshold exceeded.
        Returns True if account is now locked.
        """
        user.record_login_failure(ip_address=ip_address, user_agent=user_agent)
        return user.is_locked

    @classmethod
    def unlock_user(
        cls, user: User, unlocked_by: Optional[User] = None, reason: str = "Administrative manual unlock"
    ):
        """Unlocks an account and logs the administrative intervention."""
        user.unlock_account(unlocked_by=unlocked_by, reason=reason)


class AuthenticationService:
    """
    Coordinates enterprise authentication, credential verification, lockout policies, and session establishment.
    """

    @classmethod
    def authenticate_and_login(
        cls,
        request: HttpRequest,
        email: str,
        password: str,
        remember_me: bool = False,
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        Executes complete authentication flow:
        - Case-insensitive user lookup
        - Lockout validation
        - Active status validation
        - Credential check
        - Login history logging
        - Session configuration
        Returns (User, None) on success or (None, error_message) on failure.
        """
        email = email.strip().lower() if email else ""
        ip_address = getattr(request, "client_ip", "127.0.0.1")
        user_agent = getattr(request, "client_user_agent", "")

        user = User.objects.filter(email__iexact=email).first()

        if not user:
            LoginHistory.objects.create(
                user=None,
                email_attempted=email,
                status=LoginStatus.FAILED_INVALID_CREDENTIALS,
                ip_address=ip_address,
                user_agent=user_agent,
                failure_reason="User account not found",
            )
            return None, "Invalid email address or password."

        # Check account lockout
        if user.is_locked:
            remaining_mins = max(1, int((user.locked_until - timezone.now()).total_seconds() // 60))
            LoginHistory.objects.create(
                user=user,
                email_attempted=email,
                status=LoginStatus.FAILED_ACCOUNT_LOCKED,
                ip_address=ip_address,
                user_agent=user_agent,
                failure_reason=f"Account locked. {remaining_mins} minutes remaining.",
            )
            cls._record_security_audit(user, success=False, event="ACCOUNT_LOCKED", request=request)
            return None, f"This account is temporarily locked due to security policy. Try again in {remaining_mins} minutes."

        # Check if account is active
        if not user.is_active or user.account_status in (AccountStatus.SUSPENDED, AccountStatus.DEACTIVATED):
            LoginHistory.objects.create(
                user=user,
                email_attempted=email,
                status=LoginStatus.FAILED_ACCOUNT_INACTIVE,
                ip_address=ip_address,
                user_agent=user_agent,
                failure_reason="Account suspended or deactivated",
            )
            cls._record_security_audit(user, success=False, event="ACCOUNT_INACTIVE", request=request)
            return None, "Your account is not active. Please contact your system administrator."

        # Verify password
        if not user.check_password(password):
            is_now_locked = LockoutService.record_failure_and_check_lockout(
                user=user, ip_address=ip_address, user_agent=user_agent
            )
            cls._record_security_audit(user, success=False, event="LOGIN_FAILURE", request=request)
            if is_now_locked:
                lockout_duration = getattr(settings, "AUTH_LOCKOUT_DURATION_MINUTES", 15)
                return None, f"Maximum failed login attempts exceeded. Account is locked for {lockout_duration} minutes."
            remaining = getattr(settings, "AUTH_MAX_LOGIN_ATTEMPTS", 5) - user.failed_login_attempts
            return None, f"Invalid email address or password. ({remaining} attempts remaining before lockout)"

        # Successful authentication
        user.record_login_success(ip_address=ip_address, user_agent=user_agent)
        login(request, user, backend="apps.accounts.backends.EmailAuthBackend")
        cls._record_security_audit(user, success=True, event="LOGIN_SUCCESS", request=request)

        # Remember me configuration
        if remember_me:
            request.session.set_expiry(1209600)  # 2 weeks
        else:
            request.session.set_expiry(getattr(settings, "SESSION_COOKIE_AGE", 86400))

        return user, None

    @classmethod
    def _record_security_audit(cls, user: Optional[User], success: bool, event: str, request: Optional[HttpRequest] = None):
        """Helper to invoke Phase 14 Security & Auditing and Phase 16 Monitoring."""
        try:
            from apps.security.services import AuditService, SecurityEventService
            if user:
                AuditService.login(user, success, request=request, reason=event)
                SecurityEventService.emit(
                    event_type="LOGIN_SUCCESS" if success else "LOGIN_FAILURE",
                    user=user,
                    severity="INFO" if success else "LOW",
                    outcome="SUCCESS" if success else "FAILURE",
                    action="login",
                    request=request,
                    metadata={"event": event},
                )
        except Exception:
            pass

        try:
            from apps.monitoring.models import MetricDefinition, MetricSample
            metric_code = "auth.login.success" if success else "auth.login.failure"
            metric = MetricDefinition.objects.filter(code=metric_code).first()
            if metric:
                MetricSample.objects.create(
                    metric=metric,
                    value=1.0,
                    labels={"status": "success" if success else "failure"},
                )
        except Exception:
            pass

    @classmethod
    def register_user(
        cls,
        email: str,
        password: str,
        first_name: str = "",
        last_name: str = "",
        phone: str = "",
        job_title: str = "",
        role: str = "CUSTOMER",
        role_code: Optional[str] = None,
        request: Optional[HttpRequest] = None,
    ) -> User:
        """
        Creates a new user, assigns initial role, creates profile, and triggers activation.
        """
        if role not in ["ADMIN", "EMPLOYEE", "CUSTOMER"]:
            role = "CUSTOMER"

        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            job_title=job_title,
            role=role,
            account_status=AccountStatus.ACTIVE,
            is_active=True,
            is_verified=False,
        )

        effective_role_code = role_code or (
            SystemRole.CUSTOMER if role == "CUSTOMER" else (
                SystemRole.ADMIN if role == "ADMIN" else SystemRole.EMPLOYEE
            )
        )
        role_obj = Role.objects.filter(code=effective_role_code).first()
        if role_obj:
            UserRole.objects.get_or_create(user=user, role=role_obj)

        # Send activation email
        cls.send_activation_email(user, request)
        return user

    @classmethod
    def send_activation_email(cls, user: User, request: Optional[HttpRequest] = None):
        """Sends account activation link via email."""
        uidb64, token = TokenService.generate_activation_token(user)
        base_url = (
            request.build_absolute_uri("/").rstrip("/")
            if request
            else "http://localhost:8000"
        )
        activation_url = f"{base_url}/accounts/activate/{uidb64}/{token}/"

        subject = f"Activate your {getattr(settings, 'PLATFORM_NAME', 'EnterpriseOne')} Account"
        message = (
            f"Hello {user.get_full_name()},\n\n"
            f"Welcome to EnterpriseOne! Please activate your account by clicking the link below:\n\n"
            f"{activation_url}\n\n"
            f"This link will expire in 48 hours.\n\n"
            "If you did not create this account, please ignore this email.\n\n"
            "— The EnterpriseOne Security Team"
        )
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
        except Exception:
            pass


class RBACService:
    """
    Domain service for role assignment, role revocation, and permission management.
    """

    @classmethod
    def assign_role_to_user(cls, user: User, role: Role, assigned_by: Optional[User] = None) -> UserRole:
        """Assigns a role to a user and audits who granted the assignment."""
        assignment, _ = UserRole.objects.get_or_create(
            user=user,
            role=role,
            defaults={"assigned_by": assigned_by},
        )
        return assignment

    @classmethod
    def revoke_role_from_user(cls, user: User, role: Role) -> bool:
        """Revokes a specific role assignment from a user."""
        deleted_count, _ = UserRole.objects.filter(user=user, role=role).delete()
        return deleted_count > 0

    @classmethod
    def grant_permission_to_role(cls, role: Role, permission: Permission) -> RolePermission:
        """Maps a permission to a role."""
        mapping, _ = RolePermission.objects.get_or_create(role=role, permission=permission)
        return mapping

    @classmethod
    def revoke_permission_from_role(cls, role: Role, permission: Permission) -> bool:
        """Removes a permission mapping from a role."""
        deleted_count, _ = RolePermission.objects.filter(role=role, permission=permission).delete()
        return deleted_count > 0
