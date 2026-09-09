"""
Unit Tests for CRM Models: Account, Contact, Lead, PipelineStage, Deal, DealStageTransition, Activity, and Note.
"""
from decimal import Decimal
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.organizations.models import Organization
from apps.crm.models import (
    Account,
    Contact,
    Lead,
    PipelineStage,
    Deal,
    DealStageTransition,
    Activity,
    Note,
    AccountType,
    IndustryChoice,
    LifecycleStage,
    AccountStatus,
    LeadSource,
    LeadStatus,
    ActivityType,
    ActivityStatus,
)


class CRMModelsTestCase(TestCase):
    """
    Validates model constraints, field defaults, property helpers, and relationships.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            email="salesrep@enterprise.internal",
            password="StrongPassword123!",
            first_name="David",
            last_name="Seller",
        )
        self.org = Organization.objects.create(
            name="Apex Dynamics Corp",
            code="APEXDYN",
            slug="apex-dynamics",
            currency="USD",
        )

    def test_account_creation_and_auto_number(self):
        """Account auto-generates a unique account_number and has valid string representation."""
        account = Account.objects.create(
            organization=self.org,
            name="Acme Megacorp",
            account_type=AccountType.CUSTOMER,
            industry=IndustryChoice.TECHNOLOGY,
            annual_revenue=Decimal("5000000.00"),
            owner=self.user,
        )
        self.assertTrue(account.account_number.startswith("ACC-"))
        self.assertEqual(str(account), "Acme Megacorp")
        self.assertEqual(account.total_contacts_count, 0)
        self.assertEqual(account.active_deals_count, 0)
        self.assertEqual(account.total_pipeline_value, 0)

    def test_contact_creation_and_primary_contact_uniqueness(self):
        """Setting a new contact as primary contact unsets any previous primary contact on that account."""
        account = Account.objects.create(
            organization=self.org,
            name="Stark Industries",
        )
        contact1 = Contact.objects.create(
            organization=self.org,
            account=account,
            first_name="Tony",
            last_name="Stark",
            email="tony@stark.com",
            is_primary_contact=True,
        )
        self.assertEqual(contact1.full_name, "Tony Stark")
        self.assertEqual(account.primary_contact, contact1)

        # Create second contact as primary
        contact2 = Contact.objects.create(
            organization=self.org,
            account=account,
            first_name="Pepper",
            last_name="Potts",
            email="pepper@stark.com",
            is_primary_contact=True,
        )
        contact1.refresh_from_db()
        self.assertFalse(contact1.is_primary_contact)
        self.assertTrue(contact2.is_primary_contact)
        self.assertEqual(account.primary_contact, contact2)
        self.assertEqual(account.total_contacts_count, 2)

    def test_lead_creation_and_properties(self):
        """Lead creates with correct defaults and properties."""
        lead = Lead.objects.create(
            organization=self.org,
            first_name="Bruce",
            last_name="Wayne",
            company_name="Wayne Enterprises",
            email="bruce@waynecorp.com",
            estimated_value=Decimal("75000.00"),
            owner=self.user,
        )
        self.assertEqual(lead.full_name, "Bruce Wayne")
        self.assertEqual(str(lead), "Bruce Wayne (Wayne Enterprises)")
        self.assertFalse(lead.is_converted)
        self.assertEqual(lead.lead_score, 0)

    def test_pipeline_stage_unique_constraint(self):
        """Pipeline stages must have unique codes per organization."""
        PipelineStage.objects.create(
            organization=self.org,
            name="Discovery",
            code="DISCOVERY",
            order=1,
            default_probability=20,
        )
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                PipelineStage.objects.create(
                    organization=self.org,
                    name="Duplicate Discovery",
                    code="DISCOVERY",
                    order=2,
                    default_probability=30,
                )

    def test_deal_creation_auto_number_and_weighted_amount(self):
        """Deal auto-generates deal_number and accurately calculates probability-weighted value."""
        stage = PipelineStage.objects.create(
            organization=self.org,
            name="Negotiation",
            code="NEGOTIATION",
            order=4,
            default_probability=70,
        )
        account = Account.objects.create(
            organization=self.org,
            name="Cyberdyne Systems",
        )
        deal = Deal.objects.create(
            organization=self.org,
            account=account,
            name="Neural Net Infrastructure",
            stage=stage,
            amount=Decimal("100000.00"),
            probability=70,
        )
        self.assertTrue(deal.deal_number.startswith("DEAL-"))
        self.assertEqual(deal.weighted_amount, Decimal("70000.00"))
        self.assertEqual(account.active_deals_count, 1)
        self.assertEqual(account.total_pipeline_value, Decimal("100000.00"))

    def test_deal_stage_transition_logging(self):
        """DealStageTransition tracks movement from one stage to another."""
        stage1 = PipelineStage.objects.create(
            organization=self.org,
            name="Prospecting",
            code="PROSPECT",
            order=1,
            default_probability=10,
        )
        stage2 = PipelineStage.objects.create(
            organization=self.org,
            name="Proposal",
            code="PROPOSAL",
            order=2,
            default_probability=40,
        )
        account = Account.objects.create(
            organization=self.org,
            name="Wayne Tech",
        )
        deal = Deal.objects.create(
            organization=self.org,
            account=account,
            name="Batmobile Tech",
            stage=stage1,
            amount=Decimal("250000.00"),
        )
        transition = DealStageTransition.objects.create(
            organization=self.org,
            deal=deal,
            from_stage=stage1,
            to_stage=stage2,
            changed_by=self.user,
            transition_notes="Proposal presentation delivered.",
            duration_in_previous_stage_seconds=3600,
        )
        self.assertIn("Batmobile Tech", str(transition))
        self.assertEqual(deal.stage_transitions.count(), 1)

    def test_activity_and_note_models(self):
        """Activity and Note associate with accounts and record interactions."""
        account = Account.objects.create(
            organization=self.org,
            name="Oscorp Industries",
        )
        activity = Activity.objects.create(
            organization=self.org,
            account=account,
            activity_type=ActivityType.CALL,
            subject="Quarterly review call",
            status=ActivityStatus.PLANNED,
            assigned_to=self.user,
        )
        self.assertEqual(str(activity), "[Phone Call] Quarterly review call")
        self.assertEqual(account.activities.count(), 1)

        note = Note.objects.create(
            organization=self.org,
            account=account,
            title="Strategic Executive Alignment",
            content="Discussed cloud migration objectives for Q3.",
            created_by=self.user,
        )
        self.assertEqual(str(note), "Strategic Executive Alignment")
        self.assertEqual(account.notes_list.count(), 1)
