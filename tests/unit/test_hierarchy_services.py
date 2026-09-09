"""
Unit Tests for Hierarchy and Reporting Line Domain Services.
"""
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.accounts.models import User
from apps.organizations.models import Organization, Department, OrganizationMember
from apps.organizations.services import HierarchyService


class HierarchyServiceTestCase(TestCase):
    """
    Validates circular reporting detection, subordinate subtree queries, and department tree building.
    """

    def setUp(self):
        self.org = Organization.objects.create(name="Apex Enterprises", code="APEX", slug="apex-ent")

        # Create hierarchy of users: CEO (Alice) -> Director (Bob) -> Manager (Charlie) -> Lead (Diana)
        self.alice = User.objects.create_user(email="alice@apex.internal", password="Password123!", first_name="Alice")
        self.bob = User.objects.create_user(email="bob@apex.internal", password="Password123!", first_name="Bob")
        self.charlie = User.objects.create_user(email="charlie@apex.internal", password="Password123!", first_name="Charlie")
        self.diana = User.objects.create_user(email="diana@apex.internal", password="Password123!", first_name="Diana")

        # Memberships
        self.mem_alice = OrganizationMember.objects.create(organization=self.org, user=self.alice, reports_to=None)
        self.mem_bob = OrganizationMember.objects.create(organization=self.org, user=self.bob, reports_to=self.alice)
        self.mem_charlie = OrganizationMember.objects.create(organization=self.org, user=self.charlie, reports_to=self.bob)
        self.mem_diana = OrganizationMember.objects.create(organization=self.org, user=self.diana, reports_to=self.charlie)

    def test_self_reporting_raises_validation_error(self):
        with self.assertRaises(ValidationError) as ctx:
            HierarchyService.validate_reporting_chain(self.mem_bob, self.bob)
        self.assertIn("cannot report to themselves", str(ctx.exception))

    def test_valid_reporting_chain_passes(self):
        # Assign Diana to report directly to Alice
        try:
            HierarchyService.validate_reporting_chain(self.mem_diana, self.alice)
        except ValidationError:
            self.fail("Valid reporting assignment should not raise ValidationError.")

    def test_direct_reporting_cycle_raises_error(self):
        # Alice reporting to Bob (when Bob already reports to Alice)
        with self.assertRaises(ValidationError) as ctx:
            HierarchyService.validate_reporting_chain(self.mem_alice, self.bob)
        self.assertIn("Circular hierarchy detected", str(ctx.exception))

    def test_indirect_reporting_cycle_raises_error(self):
        # Alice reporting to Diana (Alice -> Bob -> Charlie -> Diana)
        with self.assertRaises(ValidationError) as ctx:
            HierarchyService.validate_reporting_chain(self.mem_alice, self.diana)
        self.assertIn("Circular hierarchy detected", str(ctx.exception))

    def test_get_direct_and_indirect_reports(self):
        # Alice's subordinates should be Bob, Charlie, Diana
        reports = HierarchyService.get_direct_and_indirect_reports(self.org, self.alice)
        report_ids = [u.id for u in reports]
        self.assertEqual(len(report_ids), 3)
        self.assertIn(self.bob.id, report_ids)
        self.assertIn(self.charlie.id, report_ids)
        self.assertIn(self.diana.id, report_ids)

        # Bob's subordinates should be Charlie, Diana
        bob_reports = HierarchyService.get_direct_and_indirect_reports(self.org, self.bob)
        self.assertEqual(len(bob_reports), 2)

    def test_build_department_tree(self):
        d1 = Department.objects.create(organization=self.org, name="Engineering", code="ENG")
        d2 = Department.objects.create(organization=self.org, name="Backend", code="ENG-BE", parent_department=d1)
        d3 = Department.objects.create(organization=self.org, name="Frontend", code="ENG-FE", parent_department=d1)
        d4 = Department.objects.create(organization=self.org, name="Marketing", code="MKT")

        tree = HierarchyService.build_department_tree(self.org)
        # Root departments: Engineering and Marketing (2 root nodes)
        self.assertEqual(len(tree), 2)
        eng_node = next(n for n in tree if n["dept"].code == "ENG")
        self.assertEqual(len(eng_node["children"]), 2)
