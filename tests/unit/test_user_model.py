"""
Unit Tests for Custom User, Profile, and RBAC Models.
"""
import uuid
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

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
from enterpriseone.configuration.constants import AccountStatus, LoginStatus
from enterpriseone.configuration.roles import SystemRole


class UserModelTestCase(TestCase):
    """
    Validates custom User model attributes, manager behavior, and helper methods.
    """

    def setUp(self):
        self.role_employee = Role.objects.create(
            code=SystemRole.EMPLOYEE,
            name="Employee",
            priority=10,
            is_system_role=True,
        )
        self.role_admin = Role.objects.create(
            code=SystemRole.SUPER_ADMIN,
            name="Super Administrator",
            priority=100,
            is_system_role=True,
        )

    def test_create_user_successful(self):
        user = User.objects.create_user(
            email="developer@enterpriseone.internal",
            password="StrongPassword123!",
            first_name="Jane",
            last_name="Doe",
        )
        self.assertIsInstance(user.id, uuid.UUID)
        self.assertEqual(user.email, "developer@enterpriseone.internal")
        self.assertEqual(user.get_full_name(), "Jane Doe")
        self.assertEqual(user.get_short_name(), "Jane")
        self.assertTrue(user.check_password("StrongPassword123!"))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_locked)

    def test_email_normalization(self):
        user = User.objects.create_user(
            email="  JOHN.DOE@EnterpriseOne.INTERNAL  ",
            password="StrongPassword123!",
        )
        self.assertEqual(user.email, "john.doe@enterpriseone.internal")

    def test_create_user_missing_email_raises_error(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="StrongPassword123!")

    def test_create_superuser_successful(self):
        admin_user = User.objects.create_superuser(
            email="admin@enterpriseone.internal",
            password="AdminPassword123!",
            first_name="Admin",
            last_name="User",
        )
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
        self.assertTrue(admin_user.is_active)
        self.assertTrue(admin_user.is_verified)
        self.assertEqual(admin_user.display_role, "Super Administrator")

    def test_superuser_missing_flags_raises_error(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="badadmin@enterpriseone.internal",
                password="AdminPassword123!",
                is_staff=False,
            )

    def test_profile_auto_created_via_signals(self):
        user = User.objects.create_user(
            email="profile_test@enterpriseone.internal",
            password="StrongPassword123!",
        )
        self.assertTrue(hasattr(user, "profile"))
        self.assertIsInstance(user.profile, UserProfile)
        self.assertEqual(user.profile.language, "en")
        self.assertEqual(user.profile.timezone, "UTC")

    def test_account_lockout_property(self):
        user = User.objects.create_user(
            email="lockout_test@enterpriseone.internal",
            password="StrongPassword123!",
        )
        self.assertFalse(user.is_locked)

        # Set lock into the future
        user.locked_until = timezone.now() + timedelta(minutes=15)
        user.save()
        self.assertTrue(user.is_locked)

        # Set lock in the past
        user.locked_until = timezone.now() - timedelta(minutes=1)
        user.save()
        self.assertFalse(user.is_locked)

    def test_role_assignment_and_has_role(self):
        user = User.objects.create_user(
            email="role_user@enterpriseone.internal",
            password="StrongPassword123!",
        )
        # Verify employee role is assigned by default
        self.assertTrue(user.has_role(SystemRole.EMPLOYEE))
        self.assertFalse(user.has_role(SystemRole.SUPER_ADMIN))

        # Assign Super Admin role
        UserRole.objects.create(user=user, role=self.role_admin)
        self.assertTrue(user.has_role(SystemRole.SUPER_ADMIN))
        self.assertEqual(user.display_role, "Super Administrator")

    def test_permission_granularity(self):
        user = User.objects.create_user(
            email="perm_user@enterpriseone.internal",
            password="StrongPassword123!",
        )
        perm = Permission.objects.create(
            code="accounts.user.export",
            name="Export Users",
            module="accounts",
            action="export",
        )
        self.assertFalse(user.has_enterprise_perm("accounts.user.export"))

        # Grant permission to employee role
        RolePermission.objects.create(role=self.role_employee, permission=perm)
        self.assertTrue(user.has_enterprise_perm("accounts.user.export"))

    def test_login_success_and_failure_auditing(self):
        user = User.objects.create_user(
            email="audit_user@enterpriseone.internal",
            password="StrongPassword123!",
        )
        # Record failure
        user.record_login_failure(ip_address="192.168.1.10", user_agent="Mozilla/5.0", reason="Bad pass")
        self.assertEqual(user.failed_login_attempts, 1)
        self.assertEqual(user.login_history.count(), 1)
        self.assertEqual(user.login_history.first().status, LoginStatus.FAILED_INVALID_CREDENTIALS)

        # Record success
        user.record_login_success(ip_address="192.168.1.10", user_agent="Mozilla/5.0")
        self.assertEqual(user.failed_login_attempts, 0)
        self.assertIsNone(user.locked_until)
        self.assertEqual(user.login_history.count(), 2)
        self.assertEqual(user.login_history.first().status, LoginStatus.SUCCESS)
