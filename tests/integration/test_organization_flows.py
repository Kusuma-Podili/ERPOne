"""
Integration Tests for Organization Management and Multi-Tenancy Flows.
"""
from django.test import TestCase, Client
from django.urls import reverse

from apps.accounts.models import User, Role
from apps.organizations.models import Organization, Department, Branch, OrganizationMember
from apps.organizations.services import OrganizationService
from enterpriseone.configuration.roles import SystemRole


class OrganizationFlowsTestCase(TestCase):
    """
    Validates end-to-end multi-tenant provisioning, context resolution, and organizational admin operations.
    """

    def setUp(self):
        self.client = Client()
        Role.objects.create(code=SystemRole.SUPER_ADMIN, name="Super Admin", priority=100, is_system_role=True)
        Role.objects.create(code=SystemRole.ORG_ADMIN, name="Org Admin", priority=90, is_system_role=True)
        Role.objects.create(code=SystemRole.EMPLOYEE, name="Employee", priority=10, is_system_role=True)

        self.user = User.objects.create_user(
            email="ceo@apex.internal",
            password="EnterprisePassword123!",
            first_name="Victoria",
            last_name="CEO",
        )

        # Provision organization via service
        self.org = OrganizationService.create_organization(
            name="Apex International Corp",
            code="APEX",
            slug="apex-intl",
            creator=self.user,
        )

    def test_organization_provisioning_baseline(self):
        # 1. Organization & Configuration created
        self.assertEqual(self.org.name, "Apex International Corp")
        self.assertTrue(hasattr(self.org, "configuration"))

        # 2. HQ Location & Main Branch created
        self.assertEqual(self.org.locations.count(), 1)
        self.assertTrue(self.org.locations.first().is_headquarters)
        self.assertEqual(self.org.branches.count(), 1)

        # 3. Standard departments created
        self.assertEqual(self.org.departments.count(), 5)
        dept_codes = list(self.org.departments.values_list("code", flat=True))
        self.assertIn("EXEC", dept_codes)
        self.assertIn("FIN", dept_codes)
        self.assertIn("HR", dept_codes)

        # 4. Creator assigned as Org Admin with role
        self.assertEqual(self.org.members.count(), 1)
        membership = self.org.members.first()
        self.assertEqual(membership.user, self.user)
        self.assertTrue(membership.is_org_admin)
        self.assertTrue(self.user.has_role(SystemRole.ORG_ADMIN))

    def test_organization_dashboard_renders_stats(self):
        self.client.login(username="ceo@apex.internal", password="EnterprisePassword123!")
        response = self.client.get(reverse("organizations:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Apex International Corp")
        self.assertContains(response, "Total Members")
        self.assertContains(response, "Departments")

    def test_tenant_switch_flow(self):
        # Create second organization
        second_org = OrganizationService.create_organization(
            name="Beacon Technologies",
            code="BEACON",
            slug="beacon-tech",
            creator=self.user,
        )

        self.client.login(username="ceo@apex.internal", password="EnterprisePassword123!")

        # Switch to Beacon
        switch_url = reverse("organizations:switch", kwargs={"org_id": second_org.id})
        response = self.client.post(switch_url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.session.get("active_organization_id"), str(second_org.id))

    def test_branch_creation_flow(self):
        self.client.login(username="ceo@apex.internal", password="EnterprisePassword123!")
        response = self.client.post(
            reverse("organizations:branch_create"),
            {
                "name": "London International Branch",
                "code": "BR-LON",
                "location": str(self.org.locations.first().id),
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Branch.objects.filter(organization=self.org, code="BR-LON").exists())

    def test_department_creation_flow(self):
        self.client.login(username="ceo@apex.internal", password="EnterprisePassword123!")
        response = self.client.post(
            reverse("organizations:department_create"),
            {
                "name": "Artificial Intelligence Lab",
                "code": "AI-LAB",
                "branch": str(self.org.branches.first().id),
                "budget_code": "RND-2026-AI",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Department.objects.filter(organization=self.org, code="AI-LAB").exists())
