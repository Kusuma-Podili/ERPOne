"""
Integration Tests for Authentication and User Lifecycle Flows.
"""
from django.core import mail
from django.test import TestCase, Client
from django.urls import reverse

from apps.accounts.models import User, Role, AppRole
from apps.accounts.services import TokenService
from enterpriseone.configuration.roles import SystemRole


class AuthFlowsTestCase(TestCase):
    """
    Tests end-to-end HTTP request/response flows for registration, activation, login, logout, and password resets.
    """

    def setUp(self):
        self.client = Client()
        Role.objects.create(code=SystemRole.EMPLOYEE, name="Employee", priority=10, is_system_role=True)
        Role.objects.create(code=SystemRole.SUPER_ADMIN, name="Super Admin", priority=100, is_system_role=True)

        self.user = User.objects.create_user(
            email="testuser@enterpriseone.internal",
            password="EnterpriseSecure123#",
            first_name="Test",
            last_name="User",
            role=AppRole.ADMIN,
        )

    def test_registration_flow_success(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "email": "newemployee@enterpriseone.internal",
                "first_name": "Alice",
                "last_name": "Smith",
                "phone": "+15559876543",
                "job_title": "Logistics Coordinator",
                "password": "CompliantPassword123!",
                "password_confirm": "CompliantPassword123!",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(email="newemployee@enterpriseone.internal").exists())
        new_user = User.objects.get(email="newemployee@enterpriseone.internal")
        self.assertFalse(new_user.is_verified)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Activate your EnterpriseOne Account", mail.outbox[0].subject)

    def test_activation_flow_success(self):
        uidb64, token = TokenService.generate_activation_token(self.user)
        response = self.client.get(
            reverse("accounts:activate", kwargs={"uidb64": uidb64, "token": token}),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_verified)

    def test_login_flow_success_and_logout(self):
        # 1. Login
        response = self.client.post(
            reverse("accounts:login"),
            {
                "email": "testuser@enterpriseone.internal",
                "password": "EnterpriseSecure123#",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["user"].is_authenticated)

        # 2. Access dashboard
        dash_response = self.client.get(reverse("accounts:dashboard"))
        self.assertEqual(dash_response.status_code, 200)
        self.assertContains(dash_response, "Enterprise Dashboard")

        # 3. Logout
        logout_response = self.client.get(reverse("accounts:logout"), follow=True)
        self.assertEqual(logout_response.status_code, 200)
        self.assertFalse(logout_response.context["user"].is_authenticated)

    def test_login_invalid_password_shows_error(self):
        response = self.client.post(
            reverse("accounts:login"),
            {
                "email": "testuser@enterpriseone.internal",
                "password": "WrongPassword999!",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid email address or password")
        self.user.refresh_from_db()
        self.assertEqual(self.user.failed_login_attempts, 1)

    def test_password_change_flow(self):
        # Login first
        self.client.login(username="testuser@enterpriseone.internal", password="EnterpriseSecure123#")

        response = self.client.post(
            reverse("accounts:password_change"),
            {
                "current_password": "EnterpriseSecure123#",
                "new_password": "UpdatedPassword456!",
                "confirm_password": "UpdatedPassword456!",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("UpdatedPassword456!"))

    def test_password_reset_flow(self):
        # 1. Request reset
        response = self.client.post(
            reverse("accounts:password_reset"),
            {"email": "testuser@enterpriseone.internal"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

        # 2. Generate and verify token
        uidb64, token = TokenService.generate_password_reset_token(self.user)
        confirm_url = reverse("accounts:password_reset_confirm", kwargs={"uidb64": uidb64, "token": token})

        # 3. Set new password
        confirm_response = self.client.post(
            confirm_url,
            {
                "new_password": "ResetPassword2026!",
                "confirm_password": "ResetPassword2026!",
            },
            follow=True,
        )
        self.assertEqual(confirm_response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("ResetPassword2026!"))
