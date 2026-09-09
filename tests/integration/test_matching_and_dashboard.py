"""
Integration Tests for 3-Way Matching Engine and Procurement Dashboard (Milestone 6.4).
Tests ThreeWayMatchService automated reconciliation, variance detection, dispute resolution,
and HTTP views.
"""
from datetime import timedelta
from decimal import Decimal
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
    BillStatus,
    MatchStatus,
    PurchaseOrder,
    PurchaseOrderLine,
    VendorBill,
    VendorBillLine,
    ThreeWayMatch,
)
from apps.procurement.services import ThreeWayMatchService, PurchaseOrderService


class ThreeWayMatchingServiceTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Apex Dynamics",
            code="APEX-DYN",
            slug="apex-dyn",
        )
        self.user = User.objects.create_user(
            email="finance.lead@apexdyn.com",
            password="StrongPassword123!",
            first_name="Diana",
            last_name="Prince",
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
        self.po = PurchaseOrderService.create_po(
            organization=self.org,
            supplier=self.supplier,
            order_date=timezone.now().date(),
            payment_terms=PaymentTerms.NET30,
            lines_data=[
                {
                    "product": self.product,
                    "ordered_quantity": Decimal("100.00"),
                    "uom": self.uom,
                    "unit_price": Decimal("10.00"),
                }
            ],
            created_by=self.user,
        )
        self.po.status = POStatus.ISSUED
        self.po.save()

    def test_exact_match(self):
        # Create bill exactly matching PO
        bill = ThreeWayMatchService.create_vendor_bill(
            organization=self.org,
            supplier=self.supplier,
            bill_number="BILL-EXACT-01",
            bill_date=timezone.now().date(),
            due_date=timezone.now().date() + timedelta(days=30),
            purchase_order=self.po,
            lines_data=[
                {
                    "product": self.product,
                    "billed_quantity": Decimal("100.00"),
                    "unit_price": Decimal("10.00"),
                }
            ],
        )
        match_record = ThreeWayMatchService.execute_three_way_match(self.po, bill)
        self.assertEqual(match_record.status, MatchStatus.MATCHED)
        self.assertEqual(bill.status, BillStatus.MATCHED)
        self.assertTrue(match_record.is_within_tolerance)

    def test_price_variance_exceeding_tolerance(self):
        # Create bill with $12 unit price (+$200 variance > $50 tolerance)
        bill = ThreeWayMatchService.create_vendor_bill(
            organization=self.org,
            supplier=self.supplier,
            bill_number="BILL-EXP-01",
            bill_date=timezone.now().date(),
            due_date=timezone.now().date() + timedelta(days=30),
            purchase_order=self.po,
            lines_data=[
                {
                    "product": self.product,
                    "billed_quantity": Decimal("100.00"),
                    "unit_price": Decimal("12.00"),
                }
            ],
        )
        match_record = ThreeWayMatchService.execute_three_way_match(self.po, bill)
        self.assertEqual(match_record.status, MatchStatus.PRICE_VARIANCE)
        self.assertEqual(bill.status, BillStatus.DISPUTED)
        self.assertFalse(match_record.is_within_tolerance)

        # Resolve dispute
        ThreeWayMatchService.resolve_match_dispute(
            match_record,
            user=self.user,
            resolution_notes="Price increase approved per raw material surcharge agreement.",
        )
        match_record.refresh_from_db()
        bill.refresh_from_db()
        self.assertEqual(match_record.status, MatchStatus.RESOLVED)
        self.assertEqual(bill.status, BillStatus.MATCHED)

    def test_procurement_dashboard_metrics(self):
        metrics = ThreeWayMatchService.get_procurement_dashboard_metrics(self.org)
        self.assertIn("total_suppliers", metrics)
        self.assertIn("open_rfqs", metrics)
        self.assertIn("total_active_pos", metrics)
        self.assertIn("total_committed_spend", metrics)
        self.assertIn("match_accuracy", metrics)


class ProcurementDashboardViewTests(TestCase):
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
        self.bill = VendorBill.objects.create(
            organization=self.org,
            supplier=self.supplier,
            bill_number="INV-2026-001",
            bill_date=timezone.now().date(),
            due_date=timezone.now().date() + timedelta(days=30),
            total_amount=Decimal("500.00"),
        )

    def test_dashboard_view(self):
        url = reverse("procurement:dashboard")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Procurement & Sourcing Operations")
        self.assertContains(res, "Committed PO Spend")

    def test_bill_list_view(self):
        url = reverse("procurement:bill_list")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "INV-2026-001")
        self.assertContains(res, "Precision Fasteners Inc.")

    def test_bill_detail_view(self):
        url = reverse("procurement:bill_detail", kwargs={"pk": self.bill.pk})
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "INV-2026-001")
