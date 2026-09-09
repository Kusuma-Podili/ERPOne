"""
Integration Tests for Sales Pipeline, Deals, and Stage Transitions.
Validates stage automation, audit tracking, and weighted pipeline forecasting.
"""
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.organizations.models import Organization
from apps.crm.models import (
    Account,
    Deal,
    PipelineStage,
    DealStageTransition,
)
from apps.crm.services import PipelineService


class PipelineAndDealsTestCase(TestCase):
    """
    Validates stage transitions, automated audit history, and forecast intelligence.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            email="closer@enterprise.internal",
            password="StrongPassword123!",
            first_name="Jordan",
            last_name="Belfort",
        )
        self.org = Organization.objects.create(
            name="Stratton Oakmont Tech",
            code="STRATTON",
            slug="stratton-tech",
        )
        self.stages = PipelineService.initialize_default_stages(self.org)
        self.account = Account.objects.create(
            organization=self.org,
            name="Initech Software",
        )

    def test_default_pipeline_stages_initialization(self):
        """Standard 7 enterprise pipeline stages are initialized and idempotent."""
        stages_count = PipelineStage.objects.filter(organization=self.org).count()
        self.assertEqual(stages_count, 7)

        won_stage = PipelineStage.objects.get(organization=self.org, code="CLOSED_WON")
        self.assertTrue(won_stage.is_won_stage)
        self.assertEqual(won_stage.default_probability, 100)

        lost_stage = PipelineStage.objects.get(organization=self.org, code="CLOSED_LOST")
        self.assertTrue(lost_stage.is_lost_stage)
        self.assertEqual(lost_stage.default_probability, 0)

        # Idempotency check
        stages_again = PipelineService.initialize_default_stages(self.org)
        self.assertEqual(len(stages_again), 7)
        self.assertEqual(PipelineStage.objects.filter(organization=self.org).count(), 7)

    def test_stage_transition_and_audit_log(self):
        """Moving a deal to a new stage creates a DealStageTransition audit entry."""
        stage1 = self.stages[0]  # Prospecting (10%)
        stage2 = self.stages[2]  # Proposal (45%)

        deal = Deal.objects.create(
            organization=self.org,
            account=self.account,
            name="ERP Modernization 2026",
            stage=stage1,
            amount=Decimal("120000.00"),
            owner=self.user,
        )
        self.assertEqual(deal.probability, 10)

        transition = PipelineService.transition_stage(
            deal=deal,
            to_stage=stage2,
            changed_by=self.user,
            transition_notes="Proposal submitted to committee.",
        )

        deal.refresh_from_db()
        self.assertEqual(deal.stage, stage2)
        self.assertEqual(deal.probability, 45)
        self.assertFalse(deal.is_closed)

        self.assertEqual(transition.deal, deal)
        self.assertEqual(transition.from_stage, stage1)
        self.assertEqual(transition.to_stage, stage2)
        self.assertEqual(transition.changed_by, self.user)
        self.assertIn("Proposal submitted", transition.transition_notes)

    def test_closed_won_and_lost_automations(self):
        """Transitioning to Closed Won or Closed Lost updates deal status and close date."""
        won_stage = PipelineStage.objects.get(organization=self.org, code="CLOSED_WON")
        lost_stage = PipelineStage.objects.get(organization=self.org, code="CLOSED_LOST")

        deal_won = Deal.objects.create(
            organization=self.org,
            account=self.account,
            name="Contract Alpha",
            stage=self.stages[0],
            amount=Decimal("80000.00"),
        )

        PipelineService.transition_stage(
            deal=deal_won,
            to_stage=won_stage,
            changed_by=self.user,
            transition_notes="Contract signed and executed.",
        )

        deal_won.refresh_from_db()
        self.assertTrue(deal_won.is_closed)
        self.assertTrue(deal_won.is_won)
        self.assertEqual(deal_won.probability, 100)
        self.assertIsNotNone(deal_won.actual_close_date)

        # Test Closed Lost
        deal_lost = Deal.objects.create(
            organization=self.org,
            account=self.account,
            name="Contract Beta",
            stage=self.stages[0],
            amount=Decimal("40000.00"),
        )

        PipelineService.transition_stage(
            deal=deal_lost,
            to_stage=lost_stage,
            changed_by=self.user,
            lost_reason="Budget freeze in client division.",
        )

        deal_lost.refresh_from_db()
        self.assertTrue(deal_lost.is_closed)
        self.assertFalse(deal_lost.is_won)
        self.assertEqual(deal_lost.probability, 0)
        self.assertEqual(deal_lost.lost_reason, "Budget freeze in client division.")

    def test_calculate_pipeline_forecast(self):
        """Forecast correctly aggregates open values, weighted probability, and win rate."""
        # Open deal 1: $100,000 at 25% (Qualification) -> weighted $25,000
        Deal.objects.create(
            organization=self.org,
            account=self.account,
            name="Deal 1",
            stage=self.stages[1],  # 25%
            amount=Decimal("100000.00"),
            probability=25,
        )

        # Open deal 2: $200,000 at 70% (Negotiation) -> weighted $140,000
        Deal.objects.create(
            organization=self.org,
            account=self.account,
            name="Deal 2",
            stage=self.stages[3],  # 70%
            amount=Decimal("200000.00"),
            probability=70,
        )

        # Closed Won: $150,000
        won_stage = PipelineStage.objects.get(organization=self.org, code="CLOSED_WON")
        Deal.objects.create(
            organization=self.org,
            account=self.account,
            name="Deal Won",
            stage=won_stage,
            amount=Decimal("150000.00"),
            is_closed=True,
            is_won=True,
        )

        # Closed Lost: $50,000
        lost_stage = PipelineStage.objects.get(organization=self.org, code="CLOSED_LOST")
        Deal.objects.create(
            organization=self.org,
            account=self.account,
            name="Deal Lost",
            stage=lost_stage,
            amount=Decimal("50000.00"),
            is_closed=True,
            is_won=False,
        )

        forecast = PipelineService.calculate_pipeline_forecast(self.org)

        self.assertEqual(forecast["total_pipeline_value"], Decimal("300000.00"))
        self.assertEqual(forecast["weighted_forecast_value"], Decimal("165000.00"))
        self.assertEqual(forecast["won_revenue"], Decimal("150000.00"))
        self.assertEqual(forecast["open_deals_count"], 2)
        self.assertEqual(forecast["won_deals_count"], 1)
        self.assertEqual(forecast["lost_deals_count"], 1)
        self.assertEqual(forecast["win_rate_percentage"], 50.0)
