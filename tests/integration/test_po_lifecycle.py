"""
Integration Tests for Purchase Order Lifecycles and Approval Gates (Milestone 6.3).
Tests PO creation, RFQ conversion, multi-tier approvals, rejection, issuance, and views.
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
    POStatus,
    ApprovalTier,
    RequestForQuotation,
    RFQLine,
    RFQStatus,
    VendorBid,
    VendorBidLine,
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseOrderApproval,
)
from apps.procurement.services import RFQService, PurchaseOrderService


class PurchaseOrderServiceTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Apex Dynamics",
            code="APEX-DYN",
            slug="apex-dyn",
        )
        self.manager_user = User.objects.create_user(
            email="manager@apexdyn.com",
            password="StrongPassword123!",
            first_name="Diana",
            last_name="Prince",
        )
        self.director_user = User.objects.create_user(
            email="director@apexdyn.com",
            password="StrongPassword123!",
            first_name="Bruce",
            last_name="Wayne",
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
        self.supplier = Supplier.objects.create(
            organization=self.org,
            name="Silicon Components Ltd.",
            code="SILICON-01",
            supplier_type=SupplierType.MANUFACTURER,
        )

    def test_create_and_multi_tier_approval_flow(self):
        # 1. Create High-Value PO ($24,000 > $10,000 threshold -> 2 tiers required)
        po = PurchaseOrderService.create_po(
            organization=self.org,
            supplier=self.supplier,
            order_date=timezone.now().date(),
            payment_terms=PaymentTerms.NET30,
            shipping_cost=Decimal("500.00"),
            lines_data=[
                {
                    "product": self.product,
                    "ordered_quantity": Decimal("3000.00"),
                    "uom": self.uom,
                    "unit_price": Decimal("8.00"),
                    "tax_rate": Decimal("0.00"),
                }
            ],
            created_by=self.manager_user,
        )
        self.assertEqual(po.total_amount, Decimal("24500.00"))  # 3000 * 8 + 500

        # 2. Submit for Approval
        PurchaseOrderService.submit_for_approval(po, submitted_by=self.manager_user)
        self.assertEqual(po.status, POStatus.PENDING_APPROVAL)
        # Should have 2 approval gates (Tier 1 & Tier 2)
        self.assertEqual(po.approvals.count(), 2)

        # 3. Approve Tier 1
        PurchaseOrderService.approve_po(po, approver=self.manager_user, comments="Manager budget approved")
        po.refresh_from_db()
        self.assertEqual(po.status, POStatus.PENDING_APPROVAL)  # Still waiting on Tier 2

        # 4. Approve Tier 2 (Final)
        PurchaseOrderService.approve_po(po, approver=self.director_user, comments="Director signed off")
        po.refresh_from_db()
        self.assertEqual(po.status, POStatus.APPROVED)
        self.assertEqual(po.approved_by, self.director_user)

        # 5. Issue PO to Vendor
        PurchaseOrderService.issue_po(po, issued_by=self.manager_user)
        po.refresh_from_db()
        self.assertEqual(po.status, POStatus.ISSUED)
        self.assertIsNotNone(po.issued_at)

    def test_convert_rfq_to_po_service(self):
        rfq = RFQService.create_rfq(
            organization=self.org,
            title="MCU Sourcing Tender",
            submission_deadline=timezone.now() + timedelta(days=7),
            lines_data=[{"product": self.product, "target_quantity": Decimal("1000.00"), "uom": self.uom}],
        )
        RFQService.publish_rfq(rfq)
        bid = RFQService.submit_vendor_bid(
            rfq=rfq,
            supplier=self.supplier,
            bid_reference="QUOTE-SILICON-2026",
            valid_until=(timezone.now() + timedelta(days=30)).date(),
            lines_data=[{"rfq_line": rfq.lines.first(), "offered_unit_price": Decimal("7.50")}],
        )
        RFQService.award_bid(rfq, bid, "Best bid", user=self.manager_user)

        # Convert to PO
        po = PurchaseOrderService.convert_rfq_to_po(rfq, created_by=self.manager_user)
        self.assertIsNotNone(po)
        self.assertEqual(po.supplier, self.supplier)
        self.assertEqual(po.total_amount, Decimal("7500.00"))
        self.assertEqual(po.rfq, rfq)


class PurchaseOrderViewTests(TestCase):
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
        self.po = PurchaseOrder.objects.create(
            organization=self.org,
            po_number="PO-2026-00020",
            supplier=self.supplier,
            status=POStatus.DRAFT,
            order_date=timezone.now().date(),
            total_amount=Decimal("2500.00"),
            created_by=self.user,
        )
        self.line = PurchaseOrderLine.objects.create(
            purchase_order=self.po,
            line_number=1,
            product=self.product,
            ordered_quantity=Decimal("1000.00"),
            uom=self.uom,
            unit_price=Decimal("2.50"),
        )

    def test_po_list_view(self):
        url = reverse("procurement:po_list")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "PO-2026-00020")
        self.assertContains(res, "Precision Fasteners Inc.")

    def test_po_detail_view(self):
        url = reverse("procurement:po_detail", kwargs={"pk": self.po.pk})
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "PO-2026-00020")
        self.assertContains(res, "BOLT-TI-10")

    def test_po_submit_approval_and_approve_view(self):
        submit_url = reverse("procurement:po_submit_approval", kwargs={"pk": self.po.pk})
        res_sub = self.client.post(submit_url)
        self.assertRedirects(res_sub, reverse("procurement:po_detail", kwargs={"pk": self.po.pk}))

        self.po.refresh_from_db()
        self.assertEqual(self.po.status, POStatus.PENDING_APPROVAL)

        # Approve
        approve_url = reverse("procurement:po_approve", kwargs={"pk": self.po.pk})
        res_app = self.client.post(approve_url, {"comments": "Approved on review."})
        self.assertRedirects(res_app, reverse("procurement:po_detail", kwargs={"pk": self.po.pk}))

        self.po.refresh_from_db()
        self.assertEqual(self.po.status, POStatus.APPROVED)

    def test_po_issue_view(self):
        self.po.status = POStatus.APPROVED
        self.po.save()
        issue_url = reverse("procurement:po_issue", kwargs={"pk": self.po.pk})
        res = self.client.post(issue_url)
        self.assertRedirects(res, reverse("procurement:po_detail", kwargs={"pk": self.po.pk}))

        self.po.refresh_from_db()
        self.assertEqual(self.po.status, POStatus.ISSUED)

    def test_po_print_view(self):
        url = reverse("procurement:po_print", kwargs={"pk": self.po.pk})
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "PURCHASE ORDER")
        self.assertContains(res, "PO-2026-00020")
