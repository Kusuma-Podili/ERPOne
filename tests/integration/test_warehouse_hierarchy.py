"""
EnterpriseOne Integration Tests — Warehouse Hierarchy, Stock Services & Views (Milestone 5.1).
Tests WarehouseHierarchyService provisioning, location locking, StockLevelService reservation lifecycle,
aggregate balance computations, reorder threshold alerts, and multi-tenant authenticated inventory views.
"""
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.test import TestCase, Client
from django.urls import reverse
from apps.accounts.models import User
from apps.organizations.models import Organization, OrganizationMember
from apps.sales.models import Product, ProductCategory, UnitOfMeasure
from apps.inventory.models import (
    Warehouse,
    WarehouseType,
    StorageZone,
    StorageZoneType,
    StorageLocation,
    StockItem,
)
from apps.inventory.services import WarehouseHierarchyService, StockLevelService


class WarehouseHierarchyAndStockServicesTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="logistics.director@enterpriseone.com",
            password="StrongPassword123!",
            first_name="Marcus",
            last_name="Vance",
        )
        self.org = Organization.objects.create(
            name="OmniLogistics Group",
            code="OMNI-LOG",
            slug="omni-logistics",
            currency="USD",
        )
        OrganizationMember.objects.create(
            organization=self.org,
            user=self.user,
            is_org_admin=True,
            status="ACTIVE",
        )

        # Other organization for multi-tenant isolation
        self.other_org = Organization.objects.create(
            name="Rival Freight Corp",
            code="RIV-FRT",
            slug="rival-freight",
            currency="USD",
        )

        self.category = ProductCategory.objects.create(
            organization=self.org,
            name="Electronics & Sensors",
            code="ELEC-SENS",
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
            name="IoT Gateway Sensor Hub",
            sku="SENS-IOT-001",
            cost_price=Decimal("45.00"),
            list_price=Decimal("89.99"),
        )

    def test_provision_standard_warehouse_hierarchy(self):
        provision_res = WarehouseHierarchyService.provision_standard_warehouse(
            organization=self.org,
            name="Dallas Central DC",
            code="DAL-DC1",
            warehouse_type=WarehouseType.DISTRIBUTION_CENTER,
            city="Dallas",
            state_province="TX",
            is_primary=True,
            manager=self.user,
        )
        warehouse = provision_res["warehouse"]
        zones = provision_res["zones"]
        locations = provision_res["locations"]

        self.assertEqual(warehouse.code, "DAL-DC1")
        self.assertTrue(warehouse.is_primary)
        self.assertEqual(len(zones), 5)
        # Verify all 5 functional zone codes
        zone_codes = {z.code for z in zones}
        self.assertEqual(zone_codes, {"Z-REC", "Z-GEN", "Z-PICK", "Z-SHIP", "Z-QUAR"})

        # Verify initial provisioned storage bins (2 shelves * 4 bins = 8 locations)
        self.assertEqual(len(locations), 8)
        loc_codes = [loc.code for loc in locations]
        self.assertIn("Z-GEN-A01-R01-S01-B01", loc_codes)
        self.assertIn("Z-GEN-A01-R01-S02-B04", loc_codes)

        # Warehouse model properties reflect hierarchy counts
        self.assertEqual(warehouse.total_zones_count, 5)
        self.assertEqual(warehouse.total_locations_count, 8)

    def test_create_and_lock_unlock_storage_location(self):
        prov = WarehouseHierarchyService.provision_standard_warehouse(
            organization=self.org,
            name="Austin Hub",
            code="ATX-01",
        )
        warehouse = prov["warehouse"]
        pick_zone = next(z for z in prov["zones"] if z.code == "Z-PICK")

        new_loc = WarehouseHierarchyService.create_location(
            warehouse=warehouse,
            zone=pick_zone,
            aisle="02",
            rack="05",
            shelf="03",
            bin="01",
            max_weight_kg=Decimal("500.00"),
            max_volume_cbm=Decimal("1.500"),
        )
        self.assertEqual(new_loc.code, "Z-PICK-A02-R05-S03-B01")
        self.assertFalse(new_loc.is_locked)

        # Lock location
        locked_loc = WarehouseHierarchyService.lock_location(
            location=new_loc,
            reason="Scheduled Annual Physical Audit",
        )
        self.assertTrue(locked_loc.is_locked)
        self.assertEqual(locked_loc.lock_reason, "Scheduled Annual Physical Audit")

        # Unlock location
        unlocked_loc = WarehouseHierarchyService.unlock_location(locked_loc)
        self.assertFalse(unlocked_loc.is_locked)
        self.assertEqual(unlocked_loc.lock_reason, "")

    def test_stock_level_service_reservation_and_release(self):
        prov = WarehouseHierarchyService.provision_standard_warehouse(
            organization=self.org,
            name="Denver Hub",
            code="DEN-01",
        )
        warehouse = prov["warehouse"]
        loc = prov["locations"][0]

        # Initialize physical on-hand stock
        stock = StockLevelService.adjust_physical_stock(
            product=self.product,
            warehouse=warehouse,
            location=loc,
            delta_quantity=Decimal("100.00"),
        )
        self.assertEqual(stock.quantity_on_hand, Decimal("100.00"))
        self.assertEqual(stock.quantity_reserved, Decimal("0.00"))
        self.assertEqual(stock.quantity_available, Decimal("100.00"))

        # Reserve 40 units
        stock = StockLevelService.reserve_stock(
            product=self.product,
            warehouse=warehouse,
            quantity=Decimal("40.00"),
            location=loc,
        )
        self.assertEqual(stock.quantity_on_hand, Decimal("100.00"))
        self.assertEqual(stock.quantity_reserved, Decimal("40.00"))
        self.assertEqual(stock.quantity_available, Decimal("60.00"))

        # Attempt to reserve more than available (60 available, requesting 70)
        with self.assertRaises(ValidationError):
            StockLevelService.reserve_stock(
                product=self.product,
                warehouse=warehouse,
                quantity=Decimal("70.00"),
                location=loc,
            )

        # Release 15 reserved units
        stock = StockLevelService.release_reserved_stock(
            product=self.product,
            warehouse=warehouse,
            quantity=Decimal("15.00"),
            location=loc,
        )
        self.assertEqual(stock.quantity_reserved, Decimal("25.00"))
        self.assertEqual(stock.quantity_available, Decimal("75.00"))

    def test_stock_level_service_adjustments_and_invariants(self):
        prov = WarehouseHierarchyService.provision_standard_warehouse(
            organization=self.org,
            name="Phoenix Hub",
            code="PHX-01",
        )
        warehouse = prov["warehouse"]
        loc = prov["locations"][0]

        # Initial add
        stock = StockLevelService.adjust_physical_stock(
            product=self.product,
            warehouse=warehouse,
            location=loc,
            delta_quantity=Decimal("50.00"),
        )
        self.assertEqual(stock.quantity_on_hand, Decimal("50.00"))

        # Reserve 30 units
        StockLevelService.reserve_stock(
            product=self.product,
            warehouse=warehouse,
            quantity=Decimal("30.00"),
            location=loc,
        )

        # Attempt to reduce on-hand below reserved quantity (e.g. reduce by 25 leaves 25 on hand < 30 reserved)
        with self.assertRaises(ValidationError):
            StockLevelService.adjust_physical_stock(
                product=self.product,
                warehouse=warehouse,
                location=loc,
                delta_quantity=Decimal("-25.00"),
            )

        # Valid reduction (reduce by 15 leaves 35 on hand >= 30 reserved)
        stock = StockLevelService.adjust_physical_stock(
            product=self.product,
            warehouse=warehouse,
            location=loc,
            delta_quantity=Decimal("-15.00"),
        )
        self.assertEqual(stock.quantity_on_hand, Decimal("35.00"))
        self.assertEqual(stock.quantity_reserved, Decimal("30.00"))
        self.assertEqual(stock.quantity_available, Decimal("5.00"))

    def test_total_available_stock_and_reorder_alerts(self):
        prov1 = WarehouseHierarchyService.provision_standard_warehouse(
            organization=self.org,
            name="WH North",
            code="WH-N",
        )
        prov2 = WarehouseHierarchyService.provision_standard_warehouse(
            organization=self.org,
            name="WH South",
            code="WH-S",
        )
        wh1 = prov1["warehouse"]
        wh2 = prov2["warehouse"]

        # Stock in WH 1: 50 on-hand, 10 reserved = 40 available
        StockLevelService.adjust_physical_stock(
            product=self.product, warehouse=wh1, location=prov1["locations"][0], delta_quantity=Decimal("50.00")
        )
        StockLevelService.reserve_stock(
            product=self.product, warehouse=wh1, quantity=Decimal("10.00"), location=prov1["locations"][0]
        )

        # Stock in WH 2: 30 on-hand, 5 reserved = 25 available
        StockLevelService.adjust_physical_stock(
            product=self.product, warehouse=wh2, location=prov2["locations"][0], delta_quantity=Decimal("30.00")
        )
        StockLevelService.reserve_stock(
            product=self.product, warehouse=wh2, quantity=Decimal("5.00"), location=prov2["locations"][0]
        )

        # Aggregate across all warehouses: 40 + 25 = 65
        total_all = StockLevelService.get_total_available_stock(product=self.product)
        self.assertEqual(total_all, Decimal("65.00"))

        # Warehouse-specific available
        self.assertEqual(StockLevelService.get_total_available_stock(product=self.product, warehouse=wh1), Decimal("40.00"))
        self.assertEqual(StockLevelService.get_total_available_stock(product=self.product, warehouse=wh2), Decimal("25.00"))

        # Reorder alert checks
        # reorder_point default is 25.00.
        # WH-N has 50 on-hand (no alert)
        # WH-S has 30 on-hand (no alert)
        alerts_initial = StockLevelService.get_reorder_alerts(organization=self.org)
        self.assertEqual(len(alerts_initial), 0)

        # Reduce WH-S stock to 20 on-hand (<= 25.00 reorder point)
        StockLevelService.release_reserved_stock(self.product, wh2, Decimal("5.00"), prov2["locations"][0])
        StockLevelService.adjust_physical_stock(
            product=self.product, warehouse=wh2, location=prov2["locations"][0], delta_quantity=Decimal("-10.00")
        )
        alerts_after = StockLevelService.get_reorder_alerts(organization=self.org)
        self.assertEqual(len(alerts_after), 1)
        self.assertEqual(alerts_after[0].warehouse, wh2)

    def test_inventory_views_and_tenant_isolation(self):
        self.client.force_login(self.user)
        prov = WarehouseHierarchyService.provision_standard_warehouse(
            organization=self.org,
            name="Atlanta Logistics Center",
            code="ATL-01",
        )
        warehouse = prov["warehouse"]

        # Other organization warehouse
        other_prov = WarehouseHierarchyService.provision_standard_warehouse(
            organization=self.other_org,
            name="Rival Depot",
            code="RIV-01",
        )
        other_warehouse = other_prov["warehouse"]

        # List warehouses: user must see Atlanta and NOT Rival Depot
        res_list = self.client.get(reverse("inventory:warehouse_list"))
        self.assertEqual(res_list.status_code, 200)
        self.assertContains(res_list, "Atlanta Logistics Center")
        self.assertContains(res_list, "ATL-01")
        self.assertNotContains(res_list, "Rival Depot")

        # Detail warehouse: user can see own warehouse
        res_detail = self.client.get(reverse("inventory:warehouse_detail", kwargs={"pk": warehouse.pk}))
        self.assertEqual(res_detail.status_code, 200)
        self.assertContains(res_detail, "Atlanta Logistics Center")
        self.assertContains(res_detail, "Z-REC")

        # Detail warehouse: 404 when accessing other organization warehouse
        res_other_detail = self.client.get(reverse("inventory:warehouse_detail", kwargs={"pk": other_warehouse.pk}))
        self.assertEqual(res_other_detail.status_code, 404)

        # Stock list view: authenticated user can access inventory levels
        res_stock_list = self.client.get(reverse("inventory:stock_list"))
        self.assertEqual(res_stock_list.status_code, 200)
