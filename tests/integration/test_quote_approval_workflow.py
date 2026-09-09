"""
EnterpriseOne Integration Tests — Quote Approval & Lifecycle Workflow (Milestone 4.2).
Validates auto-approval, managerial threshold gating, approval/rejection actions, and customer acceptance.
"""
from decimal import Decimal
from django.test import TestCase
from apps.accounts.models import User
from apps.organizations.models import Organization
from apps.crm.models import Account, AccountType
from apps.sales.models import (
    Product,
    UnitOfMeasure,
    Quote,
    QuoteStatus,
)
from apps.sales.services import (
    QuoteCalculationService,
    QuoteApprovalService,
)


class QuoteApprovalWorkflowTestCase(TestCase):
    def setUp(self):
        self.sales_rep = User.objects.create_user(
            email="rep@enterpriseone.com",
            password="StrongPassword123!",
            first_name="Sam",
            last_name="Seller",
        )
        self.manager = User.objects.create_user(
            email="manager@enterpriseone.com",
            password="StrongPassword123!",
            first_name="Mary",
            last_name="Manager",
        )
        self.org = Organization.objects.create(
            name="Apex Dynamics Corp",
            code="APEXDYN",
            slug="apex-dynamics",
            currency="USD",
        )
        self.account = Account.objects.create(
            organization=self.org,
            name="Global Telecomm Corp",
            account_type=AccountType.CUSTOMER,
            owner=self.sales_rep,
        )
        self.uom = UnitOfMeasure.objects.create(
            organization=self.org,
            name="Unit",
            code="EA",
            category="unit",
            is_base_unit=True,
        )
        self.product = Product.objects.create(
            organization=self.org,
            name="Core Optical Transceiver",
            sku="OPT-TRX-100",
            uom=self.uom,
            cost_price=Decimal("100.00"),
            list_price=Decimal("250.00"),
        )

    def test_auto_approval_for_modest_discount(self):
        """Discounts at or below 15% are auto-approved upon submission."""
        quote = Quote.objects.create(
            organization=self.org,
            title="Standard Network Hardware",
            account=self.account,
            created_by=self.sales_rep,
        )
        QuoteCalculationService.add_line_item(
            quote=quote,
            product=self.product,
            quantity=5,
            discount_percent=Decimal("10.00"),  # <= 15%
            unit_price=Decimal("250.00"),
        )

        QuoteApprovalService.submit_for_approval(quote, self.sales_rep)
        quote.refresh_from_db()

        self.assertEqual(quote.status, QuoteStatus.APPROVED)
        self.assertFalse(quote.requires_approval)
        self.assertEqual(quote.approved_by, self.sales_rep)
        self.assertEqual(quote.approvals.count(), 0)

    def test_manager_approval_gate_for_high_discount(self):
        """Discounts exceeding 15% require formal managerial authorization."""
        quote = Quote.objects.create(
            organization=self.org,
            title="Aggressive Competitor Takeout",
            account=self.account,
            created_by=self.sales_rep,
        )
        QuoteCalculationService.add_line_item(
            quote=quote,
            product=self.product,
            quantity=10,
            discount_percent=Decimal("25.00"),  # > 15%
            unit_price=Decimal("250.00"),
        )

        QuoteApprovalService.submit_for_approval(quote, self.sales_rep)
        quote.refresh_from_db()

        self.assertEqual(quote.status, QuoteStatus.PENDING_APPROVAL)
        self.assertTrue(quote.requires_approval)
        self.assertEqual(quote.approvals.count(), 1)
        approval = quote.approvals.first()
        self.assertEqual(approval.status, "pending")
        self.assertEqual(approval.discount_threshold_exceeded, Decimal("25.00"))

        # Manager approves
        QuoteApprovalService.approve_quote(quote, self.manager, notes="Approved for strategic account takeover.")
        quote.refresh_from_db()
        self.assertEqual(quote.status, QuoteStatus.APPROVED)
        self.assertEqual(quote.approved_by, self.manager)

        approval.refresh_from_db()
        self.assertEqual(approval.status, "approved")
        self.assertEqual(approval.approver, self.manager)

    def test_manager_rejection_flow(self):
        """Manager can reject quotes exceeding margin tolerance."""
        quote = Quote.objects.create(
            organization=self.org,
            title="Unacceptable Discount Deal",
            account=self.account,
            created_by=self.sales_rep,
        )
        QuoteCalculationService.add_line_item(
            quote=quote,
            product=self.product,
            quantity=20,
            discount_percent=Decimal("40.00"),
            unit_price=Decimal("250.00"),
        )

        QuoteApprovalService.submit_for_approval(quote, self.sales_rep)
        quote.refresh_from_db()

        # Manager rejects
        QuoteApprovalService.reject_quote(quote, self.manager, reason="Margin too compressed. Max allowable is 15%.")
        quote.refresh_from_db()

        self.assertEqual(quote.status, QuoteStatus.REJECTED)
        self.assertIn("Margin too compressed", quote.rejection_reason)
        self.assertTrue(quote.can_edit)

    def test_customer_presentation_and_acceptance(self):
        """Validates presentation to customer and final acceptance."""
        quote = Quote.objects.create(
            organization=self.org,
            title="Data Center Infrastructure",
            account=self.account,
            created_by=self.sales_rep,
        )
        QuoteCalculationService.add_line_item(
            quote=quote,
            product=self.product,
            quantity=4,
            discount_percent=Decimal("5.00"),
            unit_price=Decimal("250.00"),
        )
        QuoteApprovalService.submit_for_approval(quote, self.sales_rep)

        # Present to customer
        QuoteApprovalService.present_quote(quote, self.sales_rep)
        quote.refresh_from_db()
        self.assertEqual(quote.status, QuoteStatus.PRESENTED)

        # Customer accepts
        QuoteApprovalService.accept_quote(quote, self.sales_rep)
        quote.refresh_from_db()
        self.assertEqual(quote.status, QuoteStatus.ACCEPTED)
        self.assertTrue(quote.can_convert)
