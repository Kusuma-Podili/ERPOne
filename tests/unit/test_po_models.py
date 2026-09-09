"""
Unit Tests for Purchase Order Domain Models (Milestone 6.3).
Tests PO numbering, lines calculation, tax computation, pending balances, and approval models.
"""
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from apps.organizations.models import Organization
from apps.sales.models import Product, ProductCategory, UnitOfMeasure
from apps.procurement.models import (
    Supplier,
    SupplierType,
    PaymentTerms,
    POStatus,
    ApprovalTier,
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseOrderApproval,
)


class PurchaseOrderModelTests(TestCase):
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

    def test_po_number_generation_and_properties(self):
        po_num = PurchaseOrder.generate_po_number(self.org)
        current_year = timezone.now().year
        self.assertTrue(po_num.startswith(f"PO-{current_year}-"))

        po = PurchaseOrder.objects.create(
            organization=self.org,
            po_number=po_num,
            supplier=self.supplier,
            status=POStatus.DRAFT,
            order_date=timezone.now().date(),
        )
        self.assertEqual(po.status, POStatus.DRAFT)
        self.assertFalse(po.can_submit_for_approval)  # No lines yet

        # Check line creation & recalculation
        line = PurchaseOrderLine.objects.create(
            purchase_order=po,
            line_number=1,
            product=self.product,
            ordered_quantity=Decimal("100.00"),
            uom=self.uom,
            unit_price=Decimal("75.00"),
            tax_rate=Decimal("10.00"),
        )
        self.assertEqual(line.line_subtotal, Decimal("7500.00"))
        self.assertEqual(line.line_tax, Decimal("750.00"))
        self.assertEqual(line.line_total, Decimal("8250.00"))
        self.assertEqual(line.pending_quantity, Decimal("100.00"))
        self.assertFalse(line.is_fully_received)

        po.recalculate_totals()
        self.assertEqual(po.subtotal, Decimal("7500.00"))
        self.assertEqual(po.tax_amount, Decimal("750.00"))
        self.assertEqual(po.total_amount, Decimal("8250.00"))
        self.assertTrue(po.can_submit_for_approval)

    def test_approval_gate_creation(self):
        po = PurchaseOrder.objects.create(
            organization=self.org,
            po_number="PO-2026-00001",
            supplier=self.supplier,
            status=POStatus.PENDING_APPROVAL,
            order_date=timezone.now().date(),
        )
        gate = PurchaseOrderApproval.objects.create(
            purchase_order=po,
            tier=ApprovalTier.TIER_1_MANAGER,
            threshold_amount=Decimal("10000.00"),
            status="pending",
        )
        self.assertEqual(gate.tier, ApprovalTier.TIER_1_MANAGER)
        self.assertIn("Tier 1", str(gate))
