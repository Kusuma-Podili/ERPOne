"""
Integration Tests for Lead-to-Customer Conversion Flow.
Validates atomic conversion into Account, Contact, and Deal entities.
"""
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.accounts.models import User
from apps.organizations.models import Organization
from apps.crm.models import (
    Lead,
    Account,
    Contact,
    Deal,
    LeadSource,
    LeadStatus,
    LifecycleStage,
)
from apps.crm.services import LeadConversionService, PipelineService


class LeadConversionFlowTestCase(TestCase):
    """
    Tests end-to-end atomic conversion service guarantees.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            email="conversion@enterprise.internal",
            password="StrongPassword123!",
            first_name="Elena",
            last_name="Rostova",
        )
        self.org = Organization.objects.create(
            name="Omni Consumer Products",
            code="OCP",
            slug="ocp-corp",
        )
        PipelineService.initialize_default_stages(self.org)

        self.lead = Lead.objects.create(
            organization=self.org,
            first_name="Peter",
            last_name="Parker",
            company_name="Daily Bugle Media",
            job_title="Lead Photojournalist",
            email="peter.parker@bugle.com",
            phone="+1-212-555-0199",
            website="https://dailybugle.com",
            lead_source=LeadSource.WEBSITE,
            status=LeadStatus.QUALIFIED,
            estimated_value=Decimal("45000.00"),
            city="New York",
            country="United States",
            owner=self.user,
        )

    def test_atomic_conversion_to_new_account_and_contact(self):
        """Lead successfully converts into Account and Contact in a single atomic transaction."""
        result = LeadConversionService.convert_lead(
            lead=self.lead,
            create_account=True,
            create_contact=True,
            user=self.user,
        )

        account = result["account"]
        contact = result["contact"]

        self.assertIsNotNone(account)
        self.assertIsNotNone(contact)
        self.assertEqual(account.name, "Daily Bugle Media")
        self.assertEqual(contact.full_name, "Peter Parker")
        self.assertEqual(contact.account, account)
        self.assertTrue(contact.is_primary_contact)

        # Check lead is marked converted
        self.lead.refresh_from_db()
        self.assertTrue(self.lead.is_converted)
        self.assertEqual(self.lead.status, LeadStatus.CONVERTED)
        self.assertIsNotNone(self.lead.converted_at)
        self.assertEqual(self.lead.converted_account, account)
        self.assertEqual(self.lead.converted_contact, contact)

    def test_conversion_with_deal_creation(self):
        """Lead converts with an attached starting sales Deal in the pipeline."""
        result = LeadConversionService.convert_lead(
            lead=self.lead,
            create_account=True,
            create_contact=True,
            deal_name="Bugle Media Expansion Contract",
            deal_amount=Decimal("50000.00"),
            user=self.user,
        )

        deal = result["deal"]
        self.assertIsNotNone(deal)
        self.assertEqual(deal.name, "Bugle Media Expansion Contract")
        self.assertEqual(deal.amount, Decimal("50000.00"))
        self.assertEqual(deal.account, result["account"])
        self.assertEqual(deal.primary_contact, result["contact"])
        self.assertFalse(deal.is_closed)

    def test_conversion_into_existing_account(self):
        """Lead can be attached into an existing corporate account without creating a duplicate."""
        existing_account = Account.objects.create(
            organization=self.org,
            name="Existing Enterprise Account",
        )

        result = LeadConversionService.convert_lead(
            lead=self.lead,
            create_account=False,
            create_contact=True,
            account_id=str(existing_account.id),
            user=self.user,
        )

        self.assertEqual(result["account"], existing_account)
        self.assertEqual(result["contact"].account, existing_account)
        # Verify no duplicate account created
        self.assertEqual(Account.objects.filter(organization=self.org).count(), 1)

    def test_prevent_double_conversion(self):
        """Converting an already-converted lead raises a ValidationError."""
        LeadConversionService.convert_lead(
            lead=self.lead,
            create_account=True,
            create_contact=True,
            user=self.user,
        )

        with self.assertRaises(ValidationError):
            LeadConversionService.convert_lead(
                lead=self.lead,
                create_account=True,
                create_contact=True,
                user=self.user,
            )
