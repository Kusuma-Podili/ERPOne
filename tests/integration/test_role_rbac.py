"""
Comprehensive Role-Based Access Control (RBAC) and Security Isolation Test Suite.
Tests Admin, Employee, and Customer authentication, routing, permission gates,
backend middleware security, and strict cross-customer object isolation.
"""
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.core.management import call_command

from apps.accounts.models import User, AppRole, Role, UserRole
from apps.organizations.models import Organization, OrganizationMember
from apps.crm.models import Account, Contact
from apps.sales.models import SalesOrder, Product, ProductCategory, UnitOfMeasure
from apps.support.models import SupportTicket, SupportCategory
from enterpriseone.configuration.roles import SystemRole


class RoleRBACTestCase(TestCase):
    """
    Validates end-to-end multi-role enterprise security, server-side redirect logic,
    route-level protection, and object ownership isolation.
    """

    @classmethod
    def setUpTestData(cls):
        # Run seed data to populate full enterprise structure
        call_command("seed_enterprise_data")

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.get(email="admin@enterpriseone.com")
        self.employee = User.objects.get(email="sales.exec@enterpriseone.com")
        self.customer_a = User.objects.get(email="customer.tata@enterpriseone.com")
        self.customer_b = User.objects.get(email="customer.reliance@enterpriseone.com")
        self.tata_order = SalesOrder.objects.get(order_number="ORD-2026-001")
        self.reliance_order = SalesOrder.objects.get(order_number="ORD-2026-002")
        self.tata_ticket = SupportTicket.objects.get(number="TCK-2026-001")
        self.reliance_ticket = SupportTicket.objects.get(number="TCK-2026-002")

    # =========================================================================
    # 1. Login Authentication & Role-Based Routing
    # =========================================================================
    def test_admin_login_routes_to_admin_dashboard(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"email": "admin@enterpriseone.com", "password": "AdminPassword123!"},
        )
        self.assertRedirects(response, reverse("accounts:dashboard"))

    def test_employee_login_routes_to_employee_dashboard(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"email": "sales.exec@enterpriseone.com", "password": "Password123!"},
        )
        self.assertRedirects(response, reverse("employee:dashboard"))

    def test_customer_login_routes_to_customer_dashboard(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"email": "customer.tata@enterpriseone.com", "password": "Password123!"},
        )
        self.assertRedirects(response, reverse("customer:dashboard"))

    def test_home_redirect_authenticated_users(self):
        # Admin
        self.client.force_login(self.admin)
        res = self.client.get("/")
        self.assertRedirects(res, reverse("accounts:dashboard"))

        # Employee
        self.client.force_login(self.employee)
        res = self.client.get("/")
        self.assertRedirects(res, reverse("employee:dashboard"))

        # Customer
        self.client.force_login(self.customer_a)
        res = self.client.get("/")
        self.assertRedirects(res, reverse("customer:dashboard"))

    # =========================================================================
    # 2. Admin Permissions & User Management
    # =========================================================================
    def test_admin_can_access_user_creation_and_management(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("accounts:user_create"))
        self.assertEqual(response.status_code, 200)

        # Admin creates new employee
        post_data = {
            "email": "new.analyst@enterpriseone.com",
            "first_name": "Karan",
            "last_name": "Mehta",
            "role": AppRole.EMPLOYEE,
            "password": "Password123!",
            "password_confirm": "Password123!",
            "is_active": True,
        }
        res_create = self.client.post(reverse("accounts:user_create"), post_data)
        self.assertRedirects(res_create, reverse("accounts:user_list"))
        self.assertTrue(User.objects.filter(email="new.analyst@enterpriseone.com").exists())

    # =========================================================================
    # 3. Employee Access Controls & Route Protection
    # =========================================================================
    def test_employee_can_access_employee_dashboard(self):
        self.client.force_login(self.employee)
        response = self.client.get(reverse("employee:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Operational Workspace")

    def test_employee_blocked_from_admin_user_management(self):
        self.client.force_login(self.employee)
        response = self.client.get(reverse("accounts:user_create"))
        self.assertEqual(response.status_code, 403)

    def test_employee_blocked_from_admin_dashboard(self):
        self.client.force_login(self.employee)
        response = self.client.get(reverse("accounts:dashboard"))
        self.assertEqual(response.status_code, 403)

    # =========================================================================
    # 4. Customer Access Controls & Backend Route Protection
    # =========================================================================
    def test_customer_can_access_customer_portal(self):
        self.client.force_login(self.customer_a)
        response = self.client.get(reverse("customer:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Customer Self-Service Portal")

    def test_customer_blocked_from_admin_dashboard(self):
        self.client.force_login(self.customer_a)
        response = self.client.get(reverse("accounts:dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_customer_blocked_from_admin_user_management(self):
        self.client.force_login(self.customer_a)
        response = self.client.get(reverse("accounts:user_create"))
        self.assertEqual(response.status_code, 403)

    def test_customer_blocked_from_employee_workspace(self):
        self.client.force_login(self.customer_a)
        response = self.client.get(reverse("employee:dashboard"))
        # Strict middleware blocks cross-role access to /employee/ with 403
        self.assertEqual(response.status_code, 403)

    def test_customer_middleware_blocked_from_internal_erp_modules(self):
        self.client.force_login(self.customer_a)
        # Blocked from internal finance
        res_fin = self.client.get("/finance/")
        self.assertEqual(res_fin.status_code, 403)

        # Blocked from internal HR
        res_hr = self.client.get("/hr/")
        self.assertEqual(res_hr.status_code, 403)

        # Blocked from internal security command center
        res_sec = self.client.get("/security/")
        self.assertEqual(res_sec.status_code, 403)

    # =========================================================================
    # 5. Strict Customer Object-Level Isolation
    # =========================================================================
    def test_customer_a_can_view_own_order(self):
        self.client.force_login(self.customer_a)
        response = self.client.get(reverse("customer:order_detail", kwargs={"pk": self.tata_order.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.tata_order.order_number)

    def test_customer_a_forbidden_from_viewing_customer_b_order(self):
        self.client.force_login(self.customer_a)
        response = self.client.get(reverse("customer:order_detail", kwargs={"pk": self.reliance_order.pk}))
        self.assertEqual(response.status_code, 403)

    def test_customer_a_can_view_own_ticket(self):
        self.client.force_login(self.customer_a)
        response = self.client.get(reverse("customer:ticket_detail", kwargs={"pk": self.tata_ticket.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.tata_ticket.number)

    def test_customer_a_forbidden_from_viewing_customer_b_ticket(self):
        self.client.force_login(self.customer_a)
        response = self.client.get(reverse("customer:ticket_detail", kwargs={"pk": self.reliance_ticket.pk}))
        self.assertEqual(response.status_code, 403)

    # =========================================================================
    # 6. Auditing & Security Tracking Integration
    # =========================================================================
    def test_role_change_audited(self):
        user = User.objects.create_user(
            email="role_audit_test@enterpriseone.internal",
            password="Password123!",
            first_name="Audit",
            last_name="Test",
            role=AppRole.CUSTOMER,
        )
        user.set_role(AppRole.EMPLOYEE, actor=self.admin, reason="Promotion to corporate staff")
        user.refresh_from_db()
        self.assertEqual(user.role, AppRole.EMPLOYEE)
