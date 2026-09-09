"""
EnterpriseOne Unit Tests — Reorder Rules & Purchase Requisitions Domain Models (Milestone 5.4).
Tests ReorderRule, PurchaseRequisition, and PurchaseRequisitionLine models,
validating restocking thresholds, economic order quantities, demand calculations, and approval permissions.
"""
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone
from apps.accounts.models import User
from apps.organizations.models import Organization
from apps.sales.models import Product, ProductCategory, UnitOfMeasure
from apps.inventory.models import (
    Warehouse,
    ReorderRule,
    RequisitionStatus,
    RequisitionPriority,
    PurchaseRequisition,
    PurchaseRequisitionLine,
)


class ReorderAndRequisitionModelsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="procurement.officer@enterpriseone.com",
            password="StrongPassword123!",
            first_name="Penny",
            last_name="Procurement",
        )
        self.org = Organization.objects.create(
            name="Apex Manufacturing Logistics",
            code="APX-MFG",
            slug="apex-mfg",
            currency="USD",
        )
        self.category = ProductCategory.objects.create(
            organization=self.org,
            name="Hydraulics & Seals",
            code="HYD-SEAL",
        )
        self.uom = UnitOfMeasure.objects.create(
            organization=self.org,
            name="Piece",
            code="PC",
            category="unit",
            is_base_unit=True,
            ratio_to_base=Decimal("1.0000"),
        )
        self.product = Product.objects.create(
            organization=self.org,
            category=self.category,
            uom=self.uom,
            name="High-Pressure Hydraulic Seal 45mm",
            sku="SEAL-HP-045",
            cost_price=Decimal("18.00"),
            list_price=Decimal("36.00"),
        )
        self.warehouse = Warehouse.objects.create(
            organization=self.org,
            name="Plant 1 Storage",
            code="PLANT-01",
            is_primary=True,
        )

    def test_reorder_rule_creation_and_properties(self):
        rule = ReorderRule.objects.create(
            organization=self.org,
            warehouse=self.warehouse,
            product=self.product,
            min_quantity=Decimal("20.00"),
            max_quantity=Decimal("150.00"),
            reorder_quantity=Decimal("80.00"),
            lead_time_days=14,
            preferred_vendor_name="Continental Hydraulics Ltd",
        )
        self.assertEqual(rule.lead_time_days, 14)
        self.assertTrue(rule.auto_reorder_enabled)
        self.assertTrue(rule.is_active)
        self.assertIn("SEAL-HP-045", str(rule))

    def test_reorder_rule_validations(self):
        # Min quantity cannot be negative
        r_neg = ReorderRule(
            organization=self.org,
            warehouse=self.warehouse,
            product=self.product,
            min_quantity=Decimal("-5.00"),
            max_quantity=Decimal("50.00"),
        )
        with self.assertRaises(ValidationError) as ctx:
            r_neg.full_clean()
        self.assertIn("min_quantity", ctx.exception.message_dict)

        # Max quantity cannot be lower than min quantity
        r_inv = ReorderRule(
            organization=self.org,
            warehouse=self.warehouse,
            product=self.product,
            min_quantity=Decimal("50.00"),
            max_quantity=Decimal("20.00"),
        )
        with self.assertRaises(ValidationError) as ctx:
            r_inv.full_clean()
        self.assertIn("max_quantity", ctx.exception.message_dict)

    def test_purchase_requisition_lifecycle_and_calculations(self):
        req = PurchaseRequisition.objects.create(
            organization=self.org,
            warehouse=self.warehouse,
            priority=RequisitionPriority.HIGH,
            requested_by=self.user,
            justification="Stockout threat on production assembly line",
        )
        year = timezone.now().year
        self.assertTrue(req.requisition_number.startswith(f"PR-{year}-"))
        self.assertEqual(req.status, RequisitionStatus.DRAFT)
        self.assertTrue(req.can_approve)
        self.assertTrue(req.can_cancel)

        # Attach requisition line
        line = PurchaseRequisitionLine.objects.create(
            requisition=req,
            product=self.product,
            quantity_requested=Decimal("100.00"),
            estimated_unit_cost=Decimal("18.00"),
            notes="Expedited delivery requested",
        )
        self.assertEqual(line.estimated_extended_cost, Decimal("1800.00"))
        self.assertEqual(req.total_items_count, 1)
        self.assertEqual(req.total_estimated_cost, Decimal("1800.00"))

    def test_requisition_line_validation(self):
        req = PurchaseRequisition.objects.create(
            organization=self.org,
            warehouse=self.warehouse,
        )
        bad_line = PurchaseRequisitionLine(
            requisition=req,
            product=self.product,
            quantity_requested=Decimal("-10.00"),
        )
        with self.assertRaises(ValidationError) as ctx:
            bad_line.full_clean()
        self.assertIn("quantity_requested", ctx.exception.message_dict)
