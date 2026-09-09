"""
Unit Tests for Vendor Bill and 3-Way Matching Domain Models (Milestone 6.4).
Tests bill calculations, line totals, variances, and tolerance checking.
"""
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from apps.organizations.models import Organization
from apps.sales.models import Product, ProductCategory, UnitOfMeasure
from apps.procurement.models import (
    Supplier,
    SupplierType,
    POStatus,
    BillStatus,
    MatchStatus,
    PurchaseOrder,
    PurchaseOrderLine,
    VendorBill,
    VendorBillLine,
    ThreeWayMatch,
)


class MatchingAndBillModelTests(TestCase):
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
        self.supplier = Supplier.objects.create(
            organization=self.org,
            name="Titanium Precision Mills Inc.",
            code="SUPP-TI-01",
            supplier_type=SupplierType.MANUFACTURER,
        )
        self.po = PurchaseOrder.objects.create(
            organization=self.org,
            po_number="PO-2026-00001",
            supplier=self.supplier,
            status=POStatus.APPROVED,
            order_date=timezone.now().date(),
            total_amount=Decimal("1000.00"),
        )

    def test_vendor_bill_and_lines_calculation(self):
        bill = VendorBill.objects.create(
            organization=self.org,
            supplier=self.supplier,
            purchase_order=self.po,
            bill_number="INV-9901",
            due_date=timezone.now().date(),
        )
        line = VendorBillLine.objects.create(
            bill=bill,
            product=self.product,
            billed_quantity=Decimal("10.00"),
            unit_price=Decimal("100.00"),
            tax_rate=Decimal("10.00"),
        )
        self.assertEqual(line.line_subtotal, Decimal("1000.00"))
        self.assertEqual(line.line_tax, Decimal("100.00"))
        self.assertEqual(line.line_total, Decimal("1100.00"))

        bill.recalculate_totals()
        self.assertEqual(bill.subtotal, Decimal("1000.00"))
        self.assertEqual(bill.tax_amount, Decimal("100.00"))
        self.assertEqual(bill.total_amount, Decimal("1100.00"))
        self.assertIn("INV-9901", str(bill))

    def test_three_way_match_model_structure(self):
        bill = VendorBill.objects.create(
            organization=self.org,
            supplier=self.supplier,
            purchase_order=self.po,
            bill_number="INV-9902",
            due_date=timezone.now().date(),
            total_amount=Decimal("1000.00"),
        )
        match_obj = ThreeWayMatch.objects.create(
            organization=self.org,
            purchase_order=self.po,
            vendor_bill=bill,
            status=MatchStatus.MATCHED,
            po_total_ordered=Decimal("10.00"),
            warehouse_received=Decimal("10.00"),
            invoice_billed=Decimal("10.00"),
            quantity_variance=Decimal("0.00"),
            po_amount=Decimal("1000.00"),
            billed_amount=Decimal("1000.00"),
            price_variance_amount=Decimal("0.00"),
            is_within_tolerance=True,
        )
        self.assertEqual(match_obj.status, MatchStatus.MATCHED)
        self.assertTrue(match_obj.is_within_tolerance)
        self.assertIn("PO-2026-00001", str(match_obj))
