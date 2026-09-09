"""
Unit Tests for Algorithmic Lead Scoring Service.
Tests multi-factor weighted score calculation, completeness heuristics, and persistence.
"""
from decimal import Decimal
from django.test import TestCase

from apps.accounts.models import User
from apps.organizations.models import Organization
from apps.crm.models import (
    Lead,
    LeadSource,
    LeadStatus,
    LeadPriority,
    IndustryChoice,
)
from apps.crm.services import LeadScoringService


class LeadScoringServiceTestCase(TestCase):
    """
    Validates mathematical scoring behavior, threshold triggers, and factor breakdowns.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            email="leadmanager@enterprise.internal",
            password="StrongPassword123!",
        )
        self.org = Organization.objects.create(
            name="Vanguard Global Systems",
            code="VANGUARD",
            slug="vanguard-global",
        )

    def test_high_value_enterprise_lead_scoring(self):
        """A senior decision-maker with corporate email, large scale, and referral achieves high score."""
        lead = Lead.objects.create(
            organization=self.org,
            first_name="Alexander",
            last_name="Pierce",
            company_name="World Security Council",
            job_title="Chief Technology Officer",
            email="apierce@wsc.int",
            phone="+1-202-555-0143",
            website="https://wsc.int",
            lead_source=LeadSource.REFERRAL,
            status=LeadStatus.QUALIFIED,
            priority=LeadPriority.URGENT,
            employee_count=1200,
            annual_revenue=Decimal("25000000.00"),
            city="Washington",
            country="United States",
            owner=self.user,
        )

        score, breakdown = LeadScoringService.calculate_score(lead)

        self.assertGreaterEqual(score, 85)
        self.assertLessEqual(score, 100)
        self.assertEqual(breakdown["demographic"]["points"], 20)  # Max demographic points
        self.assertGreaterEqual(breakdown["completeness"]["points"], 20)
        self.assertEqual(breakdown["source"]["points"], 20)  # Referral max points
        self.assertEqual(breakdown["priority_status"]["points"], 15)  # Urgent + Qualified max
        self.assertEqual(breakdown["domain_reputation"]["points"], 20)  # Corporate domain + website

    def test_minimal_cold_inquiry_scoring(self):
        """A minimal lead with public freemail and cold outreach receives low score."""
        lead = Lead.objects.create(
            organization=self.org,
            first_name="John",
            last_name="Doe",
            company_name="Unknown Entity",
            email="johndoe123@gmail.com",
            lead_source=LeadSource.COLD_CALL,
            status=LeadStatus.NEW,
            priority=LeadPriority.LOW,
        )

        score, breakdown = LeadScoringService.calculate_score(lead)

        self.assertLessEqual(score, 30)
        self.assertEqual(breakdown["demographic"]["points"], 0)
        self.assertEqual(breakdown["source"]["points"], 6)  # Cold call points
        self.assertEqual(breakdown["domain_reputation"]["points"], 3)  # Public email points, no website

    def test_score_and_save_persists_to_database(self):
        """score_and_save persists the calculated score and breakdown dictionary."""
        lead = Lead.objects.create(
            organization=self.org,
            first_name="Diana",
            last_name="Prince",
            company_name="Themyscira Global",
            job_title="Vice President of Strategy",
            email="diana@themyscira.com",
            website="https://themyscira.com",
            lead_source=LeadSource.WEBSITE,
            priority=LeadPriority.HIGH,
            employee_count=150,
        )
        self.assertEqual(lead.lead_score, 0)

        saved_lead = LeadScoringService.score_and_save(lead)

        self.assertGreater(saved_lead.lead_score, 50)
        self.assertIn("demographic", saved_lead.score_breakdown)
        self.assertIn("domain_reputation", saved_lead.score_breakdown)

        lead.refresh_from_db()
        self.assertEqual(lead.lead_score, saved_lead.lead_score)
