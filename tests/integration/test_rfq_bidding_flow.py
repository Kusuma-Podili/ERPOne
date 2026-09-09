"""
Integration Tests for RFQ Services and Competitive Bidding Views (Milestone 6.2).
Tests RFQService workflows (create, invite, publish, submit bid, compare, award) and HTTP views.
"""
from datetime import timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from apps.accounts.models import User
from apps.organizations.models import Organization, OrganizationMember
from apps.sales.models import Product, ProductCategory, UnitOfMeasure
from apps.procurement.models import (
    Supplier,
    SupplierType,
    PaymentTerms,
    SupplierStatus,
    RFQStatus,
    RequestForQuotation,
    RFQLine,
    VendorBid,
    VendorBidLine,
)
from apps.procurement.services import RFQService


class RFQServiceTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Apex Dynamics",
            code="APEX-DYN",
            slug="apex-dyn",
        )
        self.user = User.objects.create_user(
            email="sourcing.lead@apexdyn.com",
            password="StrongPassword123!",
            first_name="Arthur",
            last_name="Curry",
        )
        self.category = ProductCategory.objects.create(
            organization=self.org,
            name="Electronics",
            code="ELEC",
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
            name="Microcontroller IC",
            sku="IC-MCU-32",
            cost_price=Decimal("8.00"),
            list_price=Decimal("15.00"),
        )
        self.supplier1 = Supplier.objects.create(
            organization=self.org,
            name="Silicon Components Ltd.",
            code="SILICON-01",
            supplier_type=SupplierType.MANUFACTURER,
            lead_time_rating=Decimal("4.8"),
            quality_rating=Decimal("4.9"),
        )
        self.supplier2 = Supplier.objects.create(
            organization=self.org,
            name="Delta Chips Distribution",
            code="DELTA-01",
            supplier_type=SupplierType.DISTRIBUTOR,
            lead_time_rating=Decimal("4.5"),
            quality_rating=Decimal("4.6"),
        )

    def test_complete_rfq_bidding_and_award_lifecycle(self):
        deadline = timezone.now() + timedelta(days=14)
        lines_data = [
            {
                "product": self.product,
                "target_quantity": Decimal("1000.00"),
                "uom": self.uom,
                "specifications": "Automotive Grade AEC-Q100",
            }
        ]

        # 1. Create RFQ
        rfq = RFQService.create_rfq(
            organization=self.org,
            title="Q4 Microcontroller Sourcing",
            submission_deadline=deadline,
            created_by=self.user,
            lines_data=lines_data,
        )
        self.assertEqual(rfq.status, RFQStatus.DRAFT)
        self.assertEqual(rfq.lines.count(), 1)

        # 2. Invite Vendors
        invitations = RFQService.invite_vendors(
            rfq=rfq,
            suppliers=[self.supplier1, self.supplier2],
            invited_by=self.user,
        )
        self.assertEqual(len(invitations), 2)

        # 3. Publish RFQ
        rfq = RFQService.publish_rfq(rfq)
        self.assertEqual(rfq.status, RFQStatus.PUBLISHED)
        self.assertTrue(rfq.can_submit_bids)

        # 4. Submit Vendor Bids
        rfq_line = rfq.lines.first()
        bid1 = RFQService.submit_vendor_bid(
            rfq=rfq,
            supplier=self.supplier1,
            bid_reference="QUOTE-SILICON-100",
            valid_until=(timezone.now() + timedelta(days=30)).date(),
            payment_terms=PaymentTerms.NET30,
            lead_time_days=14,
            shipping_cost=Decimal("200.00"),
            lines_data=[
                {
                    "rfq_line": rfq_line,
                    "offered_unit_price": Decimal("7.20"),
                    "offered_quantity": Decimal("1000.00"),
                }
            ],
        )
        self.assertEqual(bid1.total_amount, Decimal("7400.00"))  # 7.20 * 1000 + 200

        bid2 = RFQService.submit_vendor_bid(
            rfq=rfq,
            supplier=self.supplier2,
            bid_reference="QUOTE-DELTA-554",
            valid_until=(timezone.now() + timedelta(days=30)).date(),
            payment_terms=PaymentTerms.NET45,
            lead_time_days=7,
            shipping_cost=Decimal("100.00"),
            lines_data=[
                {
                    "rfq_line": rfq_line,
                    "offered_unit_price": Decimal("6.80"),
                    "offered_quantity": Decimal("1000.00"),
                }
            ],
        )
        self.assertEqual(bid2.total_amount, Decimal("6900.00"))  # 6.80 * 1000 + 100

        # 5. Compare Bids
        matrix = RFQService.compare_bids(rfq)
        self.assertEqual(len(matrix["bids"]), 2)
        self.assertEqual(len(matrix["summary"]), 2)
        # Summary sorted by lowest total amount (bid2 is cheapest at 6900)
        self.assertEqual(matrix["summary"][0]["bid"], bid2)
        self.assertEqual(matrix["lines"][0]["lowest_bidder"], self.supplier2)
        self.assertEqual(matrix["lines"][0]["lowest_price"], Decimal("6.80"))

        # 6. Award Winning Bid
        awarded = RFQService.award_bid(
            rfq=rfq,
            winning_bid=bid2,
            award_reason="Lowest price and fastest lead time.",
            user=self.user,
        )
        self.assertTrue(awarded.is_winning_bid)
        rfq.refresh_from_db()
        self.assertEqual(rfq.status, RFQStatus.AWARDED)
        self.assertEqual(rfq.winning_bid, bid2)


class RFQViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.org = Organization.objects.create(
            name="Starlight Aerospace",
            code="STAR-AERO",
            slug="starlight-aero",
        )
        self.user = User.objects.create_user(
            email="procure@starlight.com",
            password="StrongPassword123!",
            first_name="Diana",
            last_name="Prince",
        )
        OrganizationMember.objects.create(
            organization=self.org,
            user=self.user,
            is_org_admin=True,
            status="ACTIVE",
        )
        self.client.force_login(self.user)
        session = self.client.session
        session["active_organization_id"] = str(self.org.id)
        session.save()

        self.category = ProductCategory.objects.create(
            organization=self.org,
            name="Hardware",
            code="HDW",
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
            name="Titanium Bolt 10mm",
            sku="BOLT-TI-10",
            cost_price=Decimal("2.10"),
            list_price=Decimal("4.50"),
        )
        self.supplier = Supplier.objects.create(
            organization=self.org,
            name="Precision Fasteners Inc.",
            code="PREC-001",
            supplier_type=SupplierType.MANUFACTURER,
        )
        self.rfq = RequestForQuotation.objects.create(
            organization=self.org,
            rfq_number="RFQ-2026-00010",
            title="Fastener Annual Tender",
            status=RFQStatus.PUBLISHED,
            submission_deadline=timezone.now() + timedelta(days=14),
            created_by=self.user,
        )
        self.rfq_line = RFQLine.objects.create(
            rfq=self.rfq,
            line_number=1,
            product=self.product,
            target_quantity=Decimal("5000.00"),
            uom=self.uom,
        )

    def test_rfq_list_view(self):
        url = reverse("procurement:rfq_list")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "RFQ-2026-00010")
        self.assertContains(res, "Fastener Annual Tender")

    def test_rfq_detail_view(self):
        url = reverse("procurement:rfq_detail", kwargs={"pk": self.rfq.pk})
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "RFQ-2026-00010")
        self.assertContains(res, "BOLT-TI-10")

    def test_vendor_bid_create_view(self):
        url = reverse("procurement:vendor_bid_create", kwargs={"rfq_pk": self.rfq.pk})
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)

        post_data = {
            "supplier": str(self.supplier.pk),
            "bid_reference": "PF-PROP-2026",
            "valid_until": (timezone.now() + timedelta(days=30)).date().isoformat(),
            "payment_terms": PaymentTerms.NET30,
            "lead_time_days": 10,
            "shipping_cost": "50.00",
            "currency": "USD",
            f"price_{self.rfq_line.id}": "1.75",
            f"qty_{self.rfq_line.id}": "5000.00",
            f"lead_{self.rfq_line.id}": "10",
        }
        res_post = self.client.post(url, post_data)
        bid = self.rfq.bids.filter(supplier=self.supplier).first()
        self.assertIsNotNone(bid)
        self.assertEqual(bid.total_amount, Decimal("8800.00"))  # 1.75 * 5000 + 50
        self.assertRedirects(res_post, reverse("procurement:rfq_detail", kwargs={"pk": self.rfq.pk}))

    def test_rfq_comparison_view(self):
        # Create a bid first
        bid = VendorBid.objects.create(
            rfq=self.rfq,
            supplier=self.supplier,
            bid_reference="PF-PROP-1",
            valid_until=(timezone.now() + timedelta(days=30)).date(),
            payment_terms=PaymentTerms.NET30,
            lead_time_days=10,
            shipping_cost=Decimal("50.00"),
        )
        VendorBidLine.objects.create(
            bid=bid,
            rfq_line=self.rfq_line,
            offered_unit_price=Decimal("1.75"),
            offered_quantity=Decimal("5000.00"),
        )
        url = reverse("procurement:rfq_comparison", kwargs={"pk": self.rfq.pk})
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Precision Fasteners Inc.")
        self.assertContains(res, "Competitive Bid Evaluation Matrix")

    def test_rfq_print_view(self):
        url = reverse("procurement:rfq_print", kwargs={"pk": self.rfq.pk})
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "REQUEST FOR QUOTATION")
        self.assertContains(res, "RFQ-2026-00010")
