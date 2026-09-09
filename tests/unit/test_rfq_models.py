"""
Unit Tests for Request for Quotation (RFQ) and Vendor Bidding Domain Models (Milestone 6.2).
Tests RFQ sequential numbering, status lifecycles, lines, invitations, bids, and line total math.
"""
from datetime import timedelta
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from apps.organizations.models import Organization
from apps.sales.models import Product, ProductCategory, UnitOfMeasure
from apps.procurement.models import (
    Supplier,
    SupplierType,
    PaymentTerms,
    SupplierStatus,
    RFQStatus,
    RequestForQuotation,
    RFQLine,
    RFQVendorInvitation,
    VendorBid,
    VendorBidLine,
)


class RFQModelTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Apex Manufacturing",
            code="APEX-MFG",
            slug="apex-mfg",
        )
        self.category = ProductCategory.objects.create(
            organization=self.org,
            name="Raw Materials",
            code="RAW-MAT",
        )
        self.uom = UnitOfMeasure.objects.create(
            organization=self.org,
            name="Unit",
            code="EA",
            category="unit",
            is_base_unit=True,
            ratio_to_base=Decimal("1.0000"),
        )
        self.product = Product.objects.create(
            organization=self.org,
            category=self.category,
            uom=self.uom,
            name="Titanium Alloy Rod",
            sku="MAT-TI-001",
            cost_price=Decimal("80.00"),
            list_price=Decimal("120.00"),
        )
        self.supplier1 = Supplier.objects.create(
            organization=self.org,
            name="Titanium Precision Mills Inc.",
            code="SUPP-TI-01",
            supplier_type=SupplierType.MANUFACTURER,
        )
        self.supplier2 = Supplier.objects.create(
            organization=self.org,
            name="Global Metals Distribution",
            code="SUPP-MET-02",
            supplier_type=SupplierType.DISTRIBUTOR,
        )

    def test_rfq_number_generation_and_properties(self):
        rfq_num = RequestForQuotation.generate_rfq_number(self.org)
        current_year = timezone.now().year
        self.assertTrue(rfq_num.startswith(f"RFQ-{current_year}-"))

        rfq = RequestForQuotation.objects.create(
            organization=self.org,
            rfq_number=rfq_num,
            title="Q4 Titanium Rod Sourcing",
            status=RFQStatus.DRAFT,
            submission_deadline=timezone.now() + timedelta(days=14),
        )
        self.assertFalse(rfq.is_expired)
        self.assertFalse(rfq.can_submit_bids)  # Draft cannot accept bids

        # Next number should increment
        next_num = RequestForQuotation.generate_rfq_number(self.org)
        self.assertEqual(next_num, f"RFQ-{current_year}-00002")

    def test_rfq_lines_and_invitations(self):
        rfq = RequestForQuotation.objects.create(
            organization=self.org,
            rfq_number="RFQ-2026-00001",
            title="Fastener Sourcing",
            status=RFQStatus.PUBLISHED,
            submission_deadline=timezone.now() + timedelta(days=7),
        )
        line1 = RFQLine.objects.create(
            rfq=rfq,
            line_number=1,
            product=self.product,
            target_quantity=Decimal("500.00"),
            uom=self.uom,
        )
        self.assertEqual(rfq.total_lines_count, 1)
        self.assertIn("500.00", str(line1))

        invitation = RFQVendorInvitation.objects.create(
            rfq=rfq,
            supplier=self.supplier1,
        )
        self.assertIsNotNone(invitation.invitation_token)
        self.assertEqual(str(invitation), f"{self.supplier1.name} invited to RFQ-2026-00001")

    def test_vendor_bid_and_bid_line_math(self):
        rfq = RequestForQuotation.objects.create(
            organization=self.org,
            rfq_number="RFQ-2026-00005",
            title="Alloy Rod Procurement",
            status=RFQStatus.PUBLISHED,
            submission_deadline=timezone.now() + timedelta(days=10),
        )
        line = RFQLine.objects.create(
            rfq=rfq,
            line_number=1,
            product=self.product,
            target_quantity=Decimal("100.00"),
            uom=self.uom,
        )

        bid = VendorBid.objects.create(
            rfq=rfq,
            supplier=self.supplier1,
            bid_reference="QUOTE-9942",
            valid_until=(timezone.now() + timedelta(days=30)).date(),
            payment_terms=PaymentTerms.NET30,
            lead_time_days=10,
            shipping_cost=Decimal("150.00"),
        )
        bid_line = VendorBidLine.objects.create(
            bid=bid,
            rfq_line=line,
            offered_unit_price=Decimal("75.00"),
            offered_quantity=Decimal("100.00"),
            lead_time_days=10,
        )

        self.assertEqual(bid_line.line_total, Decimal("7500.00"))
        self.assertEqual(bid.lines_subtotal, Decimal("7500.00"))
        self.assertEqual(bid.total_amount, Decimal("7650.00"))  # 7500 + 150 shipping
        self.assertFalse(bid.is_winning_bid)
