"""
Integration Tests for Enterprise Security Controls, Lockout, RBAC & Middleware.
"""
from django.test import TestCase, Client
from django.urls import reverse

from apps.accounts.models import User, Role, UserRole
from enterpriseone.configuration.roles import SystemRole


class SecurityControlsTestCase(TestCase):
    """
    Validates enterprise security protections: brute force lockout, RBAC guards, and security headers.
    """

    def setUp(self):
        self.client = Client()
        self.role_employee = Role.objects.create(
            code=SystemRole.EMPLOYEE, name="Employee", priority=10, is_system_role=True
        )
        self.role_admin = Role.objects.create(
            code=SystemRole.SUPER_ADMIN, name="Super Admin", priority=100, is_system_role=True
        )

        self.user = User.objects.create_user(
            email="target@enterpriseone.internal",
            password="CorrectPassword123!",
            first_name="Target",
            last_name="Account",
        )

        self.admin = User.objects.create_superuser(
            email="admin_sec@enterpriseone.internal",
            password="AdminPassword123!",
            first_name="Sec",
            last_name="Admin",
        )

    def test_brute_force_lockout_after_five_failed_attempts(self):
        # 1. Execute 5 failed login attempts
        for i in range(5):
            response = self.client.post(
                reverse("accounts:login"),
                {"email": "target@enterpriseone.internal", "password": "WrongPassword999!"},
                follow=True,
            )
            self.assertEqual(response.status_code, 200)

        # 2. Check user record is now locked
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_locked)
        self.assertEqual(self.user.failed_login_attempts, 5)

        # 3. Attempt login with the CORRECT password while locked
        locked_response = self.client.post(
            reverse("accounts:login"),
            {"email": "target@enterpriseone.internal", "password": "CorrectPassword123!"},
            follow=True,
        )
        self.assertEqual(locked_response.status_code, 200)
        self.assertContains(locked_response, "account is temporarily locked")
        self.assertFalse(locked_response.context["user"].is_authenticated)

    def test_administrative_unlock_action(self):
        # 1. Lock user account
        for i in range(5):
            self.client.post(
                reverse("accounts:login"),
                {"email": "target@enterpriseone.internal", "password": "WrongPassword999!"},
            )
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_locked)

        # 2. Admin logs in and unlocks account
        self.client.login(username="admin_sec@enterpriseone.internal", password="AdminPassword123!")
        unlock_url = reverse("accounts:unlock_user", kwargs={"user_id": self.user.id})
        unlock_response = self.client.post(unlock_url, follow=True)
        self.assertEqual(unlock_response.status_code, 200)

        self.user.refresh_from_db()
        self.assertFalse(self.user.is_locked)
        self.assertEqual(self.user.failed_login_attempts, 0)

        # 3. User can now log in successfully
        self.client.logout()
        login_response = self.client.post(
            reverse("accounts:login"),
            {"email": "target@enterpriseone.internal", "password": "CorrectPassword123!"},
            follow=True,
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertTrue(login_response.context["user"].is_authenticated)

    def test_rbac_view_access_enforcement(self):
        # Regular employee logs in
        self.client.login(username="target@enterpriseone.internal", password="CorrectPassword123!")

        # Attempt to access admin user list
        response = self.client.get(reverse("accounts:user_list"), follow=True)
        self.assertEqual(response.status_code, 200)
        # Should be redirected back to dashboard with access denied message
        self.assertContains(response, "Access denied. You do not possess the required role permissions.")

        # Admin logs in
        self.client.logout()
        self.client.login(username="admin_sec@enterpriseone.internal", password="AdminPassword123!")
        admin_response = self.client.get(reverse("accounts:user_list"))
        self.assertEqual(admin_response.status_code, 200)
        self.assertContains(admin_response, "Enterprise Users & Directory")

    def test_enterprise_security_headers_middleware(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response["X-XSS-Protection"], "1; mode=block")
        self.assertEqual(response["Referrer-Policy"], "strict-origin-when-cross-origin")
        self.assertIn("geolocation=()", response["Permissions-Policy"])

    def test_session_security_middleware_deactivated_user(self):
        # Login user
        self.client.login(username="target@enterpriseone.internal", password="CorrectPassword123!")

        # Deactivate user in background
        self.user.is_active = False
        self.user.save()

        # Next request should terminate session and redirect to login
        response = self.client.get(reverse("accounts:dashboard"), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your account has been deactivated")
        self.assertFalse(response.context["user"].is_authenticated)
