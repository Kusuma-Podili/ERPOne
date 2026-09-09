"""
Unit Tests for Domain Services (Authentication, Tokens, Lockout, RBAC).
"""
from django.test import TestCase

from apps.accounts.models import User, Role, Permission, UserRole, RolePermission
from apps.accounts.services import TokenService, LockoutService, RBACService
from enterpriseone.configuration.roles import SystemRole


class DomainServicesTestCase(TestCase):
    """
    Tests domain services for token generation/verification, lockout management, and RBAC operations.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            email="service_test@enterpriseone.internal",
            password="StrongPassword123!",
            first_name="Service",
            last_name="Tester",
        )
        self.role_manager = Role.objects.create(
            code=SystemRole.MANAGER,
            name="Manager",
            priority=70,
            is_system_role=True,
        )
        self.permission = Permission.objects.create(
            code="reports.view",
            name="View Reports",
            module="reports",
            action="view",
        )

    def test_activation_token_lifecycle(self):
        uidb64, token = TokenService.generate_activation_token(self.user)
        self.assertTrue(uidb64)
        self.assertTrue(token)

        # Verification succeeds with valid token
        verified_user = TokenService.verify_activation_token(uidb64, token)
        self.assertEqual(verified_user, self.user)

        # Verification fails with tampered token
        tampered_token = token + "corrupted"
        self.assertIsNone(TokenService.verify_activation_token(uidb64, tampered_token))

    def test_password_reset_token_invalidation_after_password_change(self):
        uidb64, token = TokenService.generate_password_reset_token(self.user)
        self.assertTrue(uidb64)
        self.assertTrue(token)

        # Valid before change
        self.assertEqual(TokenService.verify_password_reset_token(uidb64, token), self.user)

        # Change password
        self.user.set_password("NewStrongPassword123!")
        self.user.save()

        # Token should now be invalid because user password hash changed
        self.assertIsNone(TokenService.verify_password_reset_token(uidb64, token))

    def test_lockout_and_unlock_service(self):
        # Trigger 5 failures
        for i in range(5):
            is_locked = LockoutService.record_failure_and_check_lockout(
                self.user, ip_address="10.0.0.1", user_agent="PyTest"
            )

        self.assertTrue(is_locked)
        self.assertTrue(LockoutService.is_locked(self.user))
        self.assertEqual(self.user.failed_login_attempts, 5)

        # Unlock user via service
        admin_user = User.objects.create_superuser(
            email="admin_unlocker@enterpriseone.internal",
            password="AdminPassword123!",
        )
        LockoutService.unlock_user(self.user, unlocked_by=admin_user)
        self.assertFalse(self.user.is_locked)
        self.assertEqual(self.user.failed_login_attempts, 0)

    def test_rbac_service_operations(self):
        # Assign role
        assignment = RBACService.assign_role_to_user(self.user, self.role_manager)
        self.assertIsInstance(assignment, UserRole)
        self.assertTrue(self.user.has_role(SystemRole.MANAGER))

        # Revoke role
        revoked = RBACService.revoke_role_from_user(self.user, self.role_manager)
        self.assertTrue(revoked)
        self.assertFalse(self.user.has_role(SystemRole.MANAGER))

        # Grant permission to role
        mapping = RBACService.grant_permission_to_role(self.role_manager, self.permission)
        self.assertIsInstance(mapping, RolePermission)

        # Revoke permission from role
        perm_revoked = RBACService.revoke_permission_from_role(self.role_manager, self.permission)
        self.assertTrue(perm_revoked)
