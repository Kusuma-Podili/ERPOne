"""
Unit Tests for Organization, Location, Branch, Department, Team, and Member Models.
"""
import uuid
from django.db import IntegrityError
from django.test import TestCase

from apps.accounts.models import User
from apps.organizations.models import (
    Organization,
    Location,
    Branch,
    Department,
    Team,
    OrganizationMember,
    TeamMembership,
    OrganizationConfiguration,
)


class OrganizationModelsTestCase(TestCase):
    """
    Validates model constraints, relationships, and property helpers for organizations app.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            email="founder@enterpriseone.internal",
            password="StrongPassword123!",
            first_name="Alice",
            last_name="Founder",
        )
        self.org = Organization.objects.create(
            name="Apex Global Enterprises",
            code="APEX",
            slug="apex-global",
            currency="USD",
        )
        self.location = Location.objects.create(
            organization=self.org,
            name="Apex HQ Tower",
            code="HQ-01",
            address_line1="1 Enterprise Plaza",
            city="New York",
            country="United States",
            is_headquarters=True,
        )

    def test_organization_creation_attributes(self):
        self.assertIsInstance(self.org.id, uuid.UUID)
        self.assertEqual(self.org.name, "Apex Global Enterprises")
        self.assertEqual(self.org.code, "APEX")
        self.assertTrue(self.org.is_active)
        self.assertEqual(str(self.org), "Apex Global Enterprises (APEX)")

    def test_unique_code_and_slug_constraints(self):
        from django.db import transaction
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Organization.objects.create(
                    name="Duplicate Code Org",
                    code="APEX",  # Duplicate code
                    slug="duplicate-code",
                )

        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Organization.objects.create(
                    name="Duplicate Slug Org",
                    code="APEX2",
                    slug="apex-global",  # Duplicate slug
                )

    def test_location_and_branch_relationships(self):
        branch = Branch.objects.create(
            organization=self.org,
            name="Manhattan Core",
            code="BR-NY-01",
            location=self.location,
            manager=self.user,
        )
        self.assertEqual(branch.organization, self.org)
        self.assertEqual(branch.location, self.location)
        self.assertEqual(branch.manager, self.user)
        self.assertEqual(self.org.branches.count(), 1)

    def test_department_hierarchical_path(self):
        parent_dept = Department.objects.create(
            organization=self.org,
            name="Operations & Logistics",
            code="OPS",
        )
        sub_dept = Department.objects.create(
            organization=self.org,
            name="Warehouse Management",
            code="WMS",
            parent_department=parent_dept,
        )
        sub_sub_dept = Department.objects.create(
            organization=self.org,
            name="Inventory Auditing",
            code="INV-AUD",
            parent_department=sub_dept,
        )

        self.assertEqual(parent_dept.full_department_path, "Operations & Logistics")
        self.assertEqual(sub_dept.full_department_path, "Operations & Logistics > Warehouse Management")
        self.assertEqual(
            sub_sub_dept.full_department_path,
            "Operations & Logistics > Warehouse Management > Inventory Auditing",
        )

    def test_team_and_membership(self):
        dept = Department.objects.create(
            organization=self.org,
            name="Product Engineering",
            code="ENG",
        )
        team = Team.objects.create(
            department=dept,
            name="Core Platform Squad",
            code="SQUAD-CORE",
            team_lead=self.user,
        )
        member = OrganizationMember.objects.create(
            organization=self.org,
            user=self.user,
            department=dept,
            job_title="Lead Architect",
        )
        membership = TeamMembership.objects.create(
            team=team,
            member=member,
            role_in_team="TECH_LEAD",
        )
        self.assertEqual(team.memberships.count(), 1)
        self.assertEqual(membership.member.user, self.user)
        self.assertEqual(membership.role_in_team, "TECH_LEAD")
