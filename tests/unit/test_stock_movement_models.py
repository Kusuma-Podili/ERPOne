"""
EnterpriseOne Unit Tests — Stock Movement Domain Models (Milestone 5.2).
Tests StockMovement, StockMovementLine, StockMovementType, and StockMovementStatus models,
validating routing constraints, location-warehouse integrity, unique identifiers, and valuation aggregations.
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
    WarehouseType,
    StorageZone,
    StorageZoneType,
    StorageLocation,
    StockItem,
    StockMovement,
    StockMovementType,
    StockMovementStatus,
    StockMovementLine,
)


class StockMovementModelsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="stock.controller@enterpriseone.com",
            password="StrongPassword123!",
            first_name="Stock",
            last_name="Controller",
        )
        self.org = Organization.objects.create(
            name="Apex Distribution Systems",
            code="APX-DIST",
            slug="apex-distribution",
            currency="USD",
        )
        self.other_org = Organization.objects.create(
            name="Vanguard Supply",
            code="VNG-SUPP",
            slug="vanguard-supp",
            currency="USD",
        )
        self.category = ProductCategory.objects.create(
            organization=self.org,
            name="Bearings & Bushings",
            code="BRG-BSH",
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
            name="Heavy-Duty Roller Bearing",
            sku="BRG-HD-100",
            cost_price=Decimal("12.50"),
            list_price=Decimal("25.00"),
        )

        self.wh_main = Warehouse.objects.create(
            organization=self.org,
            name="Main DC",
            code="WH-MAIN",
            is_primary=True,
        )
        self.wh_secondary = Warehouse.objects.create(
            organization=self.org,
            name="Secondary Depot",
            code="WH-SEC",
        )

        self.zone_main = StorageZone.objects.create(
            organization=self.org,
            warehouse=self.wh_main,
            name="Zone A",
            code="Z-A",
        )
        self.loc_main = StorageLocation.objects.create(
            organization=self.org,
            warehouse=self.wh_main,
            zone=self.zone_main,
            aisle="01",
            rack="01",
            shelf="01",
            bin="01",
        )

        self.zone_sec = StorageZone.objects.create(
            organization=self.org,
            warehouse=self.wh_secondary,
            name="Zone B",
            code="Z-B",
        )
        self.loc_sec = StorageLocation.objects.create(
            organization=self.org,
            warehouse=self.wh_secondary,
            zone=self.zone_sec,
            aisle="01",
            rack="01",
            shelf="01",
            bin="01",
        )

    def test_stock_movement_number_generation_and_properties(self):
        movement = StockMovement.objects.create(
            organization=self.org,
            movement_type=StockMovementType.RECEIPT,
            destination_warehouse=self.wh_main,
            created_by=self.user,
        )
        year = timezone.now().year
        self.assertTrue(movement.movement_number.startswith(f"SM-{year}-"))
        self.assertEqual(movement.status, StockMovementStatus.DRAFT)
        self.assertTrue(movement.can_post)
        self.assertTrue(movement.can_cancel)
        self.assertEqual(movement.total_lines_count, 0)
        self.assertEqual(movement.total_quantity, Decimal("0.00"))
        self.assertEqual(movement.total_value, Decimal("0.00"))

    def test_movement_transfer_validation(self):
        # Transfer without source or destination warehouse must fail validation
        m1 = StockMovement(
            organization=self.org,
            movement_type=StockMovementType.TRANSFER,
            source_warehouse=self.wh_main,
            destination_warehouse=None,
        )
        with self.assertRaises(ValidationError) as ctx:
            m1.full_clean()
        self.assertIn("destination_warehouse", ctx.exception.message_dict)

        # Transfer with identical source and destination must fail validation
        m2 = StockMovement(
            organization=self.org,
            movement_type=StockMovementType.TRANSFER,
            source_warehouse=self.wh_main,
            destination_warehouse=self.wh_main,
        )
        with self.assertRaises(ValidationError) as ctx:
            m2.full_clean()
        self.assertIn("destination_warehouse", ctx.exception.message_dict)

        # Valid transfer
        m3 = StockMovement(
            organization=self.org,
            movement_type=StockMovementType.TRANSFER,
            source_warehouse=self.wh_main,
            destination_warehouse=self.wh_secondary,
        )
        m3.full_clean()
        m3.save()
        self.assertIsNotNone(m3.pk)

    def test_movement_receipt_and_scrap_validation(self):
        # Receipt without destination warehouse must fail
        rec = StockMovement(
            organization=self.org,
            movement_type=StockMovementType.RECEIPT,
            destination_warehouse=None,
        )
        with self.assertRaises(ValidationError) as ctx:
            rec.full_clean()
        self.assertIn("destination_warehouse", ctx.exception.message_dict)

        # Scrap without source warehouse must fail
        scrap = StockMovement(
            organization=self.org,
            movement_type=StockMovementType.SCRAP,
            source_warehouse=None,
        )
        with self.assertRaises(ValidationError) as ctx:
            scrap.full_clean()
        self.assertIn("source_warehouse", ctx.exception.message_dict)

    def test_movement_line_computations_and_validations(self):
        movement = StockMovement.objects.create(
            organization=self.org,
            movement_type=StockMovementType.RECEIPT,
            destination_warehouse=self.wh_main,
            created_by=self.user,
        )
        line = StockMovementLine.objects.create(
            movement=movement,
            product=self.product,
            destination_location=self.loc_main,
            quantity=Decimal("50.00"),
            unit_cost=Decimal("12.50"),
            batch_number="LOT-2026-A",
            serial_number="SN-001",
        )
        self.assertEqual(line.total_value, Decimal("625.00"))
        self.assertEqual(movement.total_lines_count, 1)
        self.assertEqual(movement.total_quantity, Decimal("50.00"))
        self.assertEqual(movement.total_value, Decimal("625.00"))

        # Zero or negative quantity must fail validation
        bad_line = StockMovementLine(
            movement=movement,
            product=self.product,
            quantity=Decimal("-10.00"),
        )
        with self.assertRaises(ValidationError) as ctx:
            bad_line.full_clean()
        self.assertIn("quantity", ctx.exception.message_dict)

    def test_movement_line_location_warehouse_mismatch(self):
        transfer = StockMovement.objects.create(
            organization=self.org,
            movement_type=StockMovementType.TRANSFER,
            source_warehouse=self.wh_main,
            destination_warehouse=self.wh_secondary,
        )
        # Attempt to set source location to a bin belonging to wh_secondary
        mismatched_line = StockMovementLine(
            movement=transfer,
            product=self.product,
            source_location=self.loc_sec,  # belongs to wh_secondary, but movement source is wh_main
            destination_location=self.loc_sec,
            quantity=Decimal("10.00"),
        )
        with self.assertRaises(ValidationError) as ctx:
            mismatched_line.full_clean()
        self.assertIn("source_location", ctx.exception.message_dict)
