"""
EnterpriseOne Unit Tests — Inventory & Warehouse Domain Models (Milestone 5.1).
Tests Warehouse, StorageZone, StorageLocation, and StockItem models,
enforcing spatial constraints, unique codes, primary warehouse singletons, and inventory balance invariants.
"""
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import IntegrityError
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
)


class InventoryModelsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="warehouse.admin@enterpriseone.com",
            password="StrongPassword123!",
            first_name="Warehouse",
            last_name="Manager",
        )
        self.org = Organization.objects.create(
            name="Apex Logistics Inc",
            code="APX-LOG",
            slug="apex-logistics",
            currency="USD",
        )
        self.other_org = Organization.objects.create(
            name="Vanguard Supply Co",
            code="VNG-SUP",
            slug="vanguard-supply",
            currency="USD",
        )
        self.category = ProductCategory.objects.create(
            organization=self.org,
            name="Industrial Fasteners",
            code="IND-FAST",
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
            name="Grade 8 Hex Bolt 1/2-13",
            sku="BOLT-G8-050",
            cost_price=Decimal("1.25"),
            list_price=Decimal("2.50"),
        )

    def test_warehouse_creation_and_properties(self):
        warehouse = Warehouse.objects.create(
            organization=self.org,
            name="Central Distribution Center",
            code="CDC-01",
            warehouse_type=WarehouseType.DISTRIBUTION_CENTER,
            manager=self.user,
            city="Chicago",
            state_province="IL",
            is_primary=True,
            total_capacity_cbm=Decimal("50000.00"),
        )
        self.assertEqual(str(warehouse), "Central Distribution Center (CDC-01)")
        self.assertEqual(warehouse.total_zones_count, 0)
        self.assertEqual(warehouse.total_locations_count, 0)
        self.assertEqual(warehouse.total_stock_items_count, 0)
        self.assertTrue(warehouse.is_primary)

    def test_warehouse_unique_code_per_org(self):
        Warehouse.objects.create(
            organization=self.org,
            name="Warehouse A",
            code="WH-01",
        )
        from django.db import transaction
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Warehouse.objects.create(
                    organization=self.org,
                    name="Warehouse Duplicate Code",
                    code="WH-01",
                )
        # Same code in different organization must be permitted
        wh_other = Warehouse.objects.create(
            organization=self.other_org,
            name="Warehouse Other Org",
            code="WH-01",
        )
        self.assertIsNotNone(wh_other.pk)

    def test_primary_warehouse_singleton_validation(self):
        wh1 = Warehouse.objects.create(
            organization=self.org,
            name="Primary Facility",
            code="WH-PRI",
            is_primary=True,
        )
        wh1.full_clean()

        wh2 = Warehouse(
            organization=self.org,
            name="Secondary Facility",
            code="WH-SEC",
            is_primary=True,
        )
        with self.assertRaises(ValidationError) as ctx:
            wh2.full_clean()
        self.assertIn("is_primary", ctx.exception.message_dict)

    def test_storage_zone_creation_and_hierarchy(self):
        warehouse = Warehouse.objects.create(
            organization=self.org,
            name="Regional Hub",
            code="HUB-01",
        )
        zone = StorageZone.objects.create(
            organization=self.org,
            warehouse=warehouse,
            name="Refrigerated Section",
            code="Z-COLD",
            zone_type=StorageZoneType.COLD_STORAGE,
            temperature_controlled=True,
            target_temp_celsius=Decimal("4.00"),
        )
        self.assertEqual(str(zone), "HUB-01 / Refrigerated Section (Z-COLD)")
        self.assertEqual(warehouse.total_zones_count, 1)
        self.assertEqual(zone.total_locations_count, 0)

        from django.db import transaction
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                StorageZone.objects.create(
                    organization=self.org,
                    warehouse=warehouse,
                    name="Duplicate Zone Code",
                    code="Z-COLD",
                )

    def test_storage_location_code_and_barcode_auto_generation(self):
        warehouse = Warehouse.objects.create(
            organization=self.org,
            name="Main Facility",
            code="MF-01",
        )
        zone = StorageZone.objects.create(
            organization=self.org,
            warehouse=warehouse,
            name="General Storage",
            code="Z-GEN",
        )
        location = StorageLocation(
            organization=self.org,
            warehouse=warehouse,
            zone=zone,
            aisle="03",
            rack="02",
            shelf="01",
            bin="04",
        )
        location.save()

        expected_code = "Z-GEN-A03-R02-S01-B04"
        expected_barcode = f"LOC-MF-01-{expected_code}"
        self.assertEqual(location.code, expected_code)
        self.assertEqual(location.barcode, expected_barcode)
        self.assertEqual(str(location), f"MF-01 - {expected_code}")
        self.assertEqual(warehouse.total_locations_count, 1)
        self.assertEqual(zone.total_locations_count, 1)

    def test_storage_location_zone_mismatch_clean_validation(self):
        wh1 = Warehouse.objects.create(organization=self.org, name="WH 1", code="WH-1")
        wh2 = Warehouse.objects.create(organization=self.org, name="WH 2", code="WH-2")
        zone_in_wh1 = StorageZone.objects.create(
            organization=self.org,
            warehouse=wh1,
            name="Zone WH1",
            code="Z-WH1",
        )
        mismatched_loc = StorageLocation(
            organization=self.org,
            warehouse=wh2,
            zone=zone_in_wh1,
            aisle="01",
            rack="01",
            shelf="01",
            bin="01",
        )
        with self.assertRaises(ValidationError) as ctx:
            mismatched_loc.full_clean()
        self.assertIn("zone", ctx.exception.message_dict)

    def test_stock_item_computations_and_invariants(self):
        warehouse = Warehouse.objects.create(
            organization=self.org,
            name="Fulfilment Hub",
            code="FUL-01",
        )
        zone = StorageZone.objects.create(
            organization=self.org,
            warehouse=warehouse,
            name="Standard Storage",
            code="Z-STD",
        )
        location = StorageLocation.objects.create(
            organization=self.org,
            warehouse=warehouse,
            zone=zone,
            aisle="01",
            rack="01",
            shelf="01",
            bin="01",
        )
        stock_item = StockItem.objects.create(
            organization=self.org,
            product=self.product,
            warehouse=warehouse,
            location=location,
            quantity_on_hand=Decimal("100.00"),
            quantity_reserved=Decimal("30.00"),
            safety_stock=Decimal("20.00"),
            reorder_point=Decimal("50.00"),
            reorder_quantity=Decimal("100.00"),
        )
        # Check computed property
        self.assertEqual(stock_item.quantity_available, Decimal("70.00"))
        self.assertFalse(stock_item.needs_reorder)
        self.assertFalse(stock_item.is_below_safety)

        # Trigger reorder threshold
        stock_item.quantity_on_hand = Decimal("45.00")
        self.assertTrue(stock_item.needs_reorder)
        self.assertFalse(stock_item.is_below_safety)

        # Trigger safety stock breach
        stock_item.quantity_on_hand = Decimal("15.00")
        self.assertTrue(stock_item.needs_reorder)
        self.assertTrue(stock_item.is_below_safety)

    def test_stock_item_validation_errors(self):
        warehouse = Warehouse.objects.create(
            organization=self.org,
            name="West Hub",
            code="WH-WEST",
        )
        # Negative on hand
        item_neg_on_hand = StockItem(
            organization=self.org,
            product=self.product,
            warehouse=warehouse,
            quantity_on_hand=Decimal("-5.00"),
            quantity_reserved=Decimal("0.00"),
        )
        with self.assertRaises(ValidationError) as ctx:
            item_neg_on_hand.full_clean()
        self.assertIn("quantity_on_hand", ctx.exception.message_dict)

        # Negative reserved
        item_neg_reserved = StockItem(
            organization=self.org,
            product=self.product,
            warehouse=warehouse,
            quantity_on_hand=Decimal("10.00"),
            quantity_reserved=Decimal("-2.00"),
        )
        with self.assertRaises(ValidationError) as ctx:
            item_neg_reserved.full_clean()
        self.assertIn("quantity_reserved", ctx.exception.message_dict)

        # Reserved exceeding on hand
        item_over_reserved = StockItem(
            organization=self.org,
            product=self.product,
            warehouse=warehouse,
            quantity_on_hand=Decimal("10.00"),
            quantity_reserved=Decimal("15.00"),
        )
        with self.assertRaises(ValidationError) as ctx:
            item_over_reserved.full_clean()
        self.assertIn("quantity_reserved", ctx.exception.message_dict)
