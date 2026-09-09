"""
EnterpriseOne Integration Tests — Stock Movement Ledger, Goods Receipt, Transfers & Auditing (Milestone 5.2).
Validates atomic goods receipt posting, inter-facility transfer balancing, intra-warehouse bin relocation,
scrap write-offs, negative stock protection, cancellation lifecycle, and multi-tenant authenticated views.
"""
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from apps.accounts.models import User
from apps.organizations.models import Organization, OrganizationMember
from apps.sales.models import Product, ProductCategory, UnitOfMeasure
from apps.inventory.models import (
    Warehouse,
    WarehouseType,
    StorageZone,
    StorageLocation,
    StockItem,
    StockMovement,
    StockMovementType,
    StockMovementStatus,
    StockMovementLine,
)
from apps.inventory.services import (
    WarehouseHierarchyService,
    StockLevelService,
    StockMovementService,
)


class StockMovementLedgerIntegrationTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="logistics.lead@enterpriseone.com",
            password="StrongPassword123!",
            first_name="Logan",
            last_name="Logistics",
        )
        self.org = Organization.objects.create(
            name="Apex Supply Chain Logistics",
            code="APX-SCL",
            slug="apex-supply-chain",
            currency="USD",
        )
        OrganizationMember.objects.create(
            organization=self.org,
            user=self.user,
            is_org_admin=True,
            status="ACTIVE",
        )

        # Other organization for isolation
        self.other_org = Organization.objects.create(
            name="Vanguard Global Supply",
            code="VNG-GLB",
            slug="vanguard-global",
            currency="USD",
        )

        self.category = ProductCategory.objects.create(
            organization=self.org,
            name="Power Distribution Units",
            code="PWR-DIST",
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
            name="Smart Rack PDU 30A 208V",
            sku="PDU-SR-30A",
            cost_price=Decimal("150.00"),
            list_price=Decimal("299.00"),
        )

        # Provision warehouses
        prov1 = WarehouseHierarchyService.provision_standard_warehouse(
            organization=self.org,
            name="Primary Distribution Center",
            code="PDC-01",
            is_primary=True,
            manager=self.user,
        )
        self.wh_primary = prov1["warehouse"]
        self.loc_primary_gen1 = prov1["locations"][0]
        self.loc_primary_gen2 = prov1["locations"][1]

        prov2 = WarehouseHierarchyService.provision_standard_warehouse(
            organization=self.org,
            name="Secondary Assembly Hub",
            code="SAH-01",
            manager=self.user,
        )
        self.wh_secondary = prov2["warehouse"]
        self.loc_secondary_gen1 = prov2["locations"][0]

    def test_goods_receipt_posting(self):
        # Create goods receipt for 100 units
        receipt = StockMovementService.create_movement(
            organization=self.org,
            movement_type=StockMovementType.RECEIPT,
            destination_warehouse=self.wh_primary,
            reference_document="PO-2026-0089",
            created_by=self.user,
            lines_data=[
                {
                    "product": self.product,
                    "quantity": Decimal("100.00"),
                    "destination_location": self.loc_primary_gen1,
                    "unit_cost": Decimal("150.00"),
                    "batch_number": "LOT-2026-PDU-01",
                    "notes": "Initial shipment from manufacturer",
                }
            ],
        )
        self.assertEqual(receipt.status, StockMovementStatus.DRAFT)
        self.assertEqual(receipt.total_lines_count, 1)
        self.assertEqual(receipt.total_quantity, Decimal("100.00"))
        self.assertEqual(receipt.total_value, Decimal("15000.00"))

        # Post receipt
        posted = StockMovementService.post_movement(receipt, posted_by=self.user)
        self.assertEqual(posted.status, StockMovementStatus.COMPLETED)
        self.assertIsNotNone(posted.posted_at)
        self.assertEqual(posted.posted_by, self.user)

        # Verify stock item in warehouse PDC-01
        stock = StockItem.objects.get(
            warehouse=self.wh_primary,
            location=self.loc_primary_gen1,
            product=self.product,
        )
        self.assertEqual(stock.quantity_on_hand, Decimal("100.00"))
        self.assertEqual(stock.quantity_available, Decimal("100.00"))

    def test_inter_warehouse_transfer_posting(self):
        # Establish initial inventory of 80 units at PDC-01
        StockLevelService.adjust_physical_stock(
            product=self.product,
            warehouse=self.wh_primary,
            location=self.loc_primary_gen1,
            delta_quantity=Decimal("80.00"),
        )

        # Create transfer of 30 units from PDC-01 to SAH-01
        transfer = StockMovementService.create_movement(
            organization=self.org,
            movement_type=StockMovementType.TRANSFER,
            source_warehouse=self.wh_primary,
            destination_warehouse=self.wh_secondary,
            reference_document="TRF-2026-001",
            created_by=self.user,
            lines_data=[
                {
                    "product": self.product,
                    "quantity": Decimal("30.00"),
                    "source_location": self.loc_primary_gen1,
                    "destination_location": self.loc_secondary_gen1,
                    "unit_cost": Decimal("150.00"),
                }
            ],
        )

        # Execute post
        StockMovementService.post_movement(transfer, posted_by=self.user)

        # Check source inventory (80 - 30 = 50)
        source_stock = StockItem.objects.get(
            warehouse=self.wh_primary,
            location=self.loc_primary_gen1,
            product=self.product,
        )
        self.assertEqual(source_stock.quantity_on_hand, Decimal("50.00"))

        # Check destination inventory (0 + 30 = 30)
        dest_stock = StockItem.objects.get(
            warehouse=self.wh_secondary,
            location=self.loc_secondary_gen1,
            product=self.product,
        )
        self.assertEqual(dest_stock.quantity_on_hand, Decimal("30.00"))

    def test_intra_warehouse_location_transfer(self):
        # Establish initial stock in bin 1
        StockLevelService.adjust_physical_stock(
            product=self.product,
            warehouse=self.wh_primary,
            location=self.loc_primary_gen1,
            delta_quantity=Decimal("50.00"),
        )

        # Relocate 20 units from bin 1 to bin 2
        relocation = StockMovementService.create_movement(
            organization=self.org,
            movement_type=StockMovementType.LOCATION_TRANSFER,
            source_warehouse=self.wh_primary,
            destination_warehouse=self.wh_primary,
            reference_document="RELOC-001",
            created_by=self.user,
            lines_data=[
                {
                    "product": self.product,
                    "quantity": Decimal("20.00"),
                    "source_location": self.loc_primary_gen1,
                    "destination_location": self.loc_primary_gen2,
                    "unit_cost": Decimal("150.00"),
                }
            ],
        )
        StockMovementService.post_movement(relocation, posted_by=self.user)

        # Bin 1 should have 30 units
        stock_bin1 = StockItem.objects.get(
            warehouse=self.wh_primary,
            location=self.loc_primary_gen1,
            product=self.product,
        )
        self.assertEqual(stock_bin1.quantity_on_hand, Decimal("30.00"))

        # Bin 2 should have 20 units
        stock_bin2 = StockItem.objects.get(
            warehouse=self.wh_primary,
            location=self.loc_primary_gen2,
            product=self.product,
        )
        self.assertEqual(stock_bin2.quantity_on_hand, Decimal("20.00"))

    def test_scrap_and_insufficient_stock_rejection(self):
        # Establish 15 units in PDC-01
        StockLevelService.adjust_physical_stock(
            product=self.product,
            warehouse=self.wh_primary,
            location=self.loc_primary_gen1,
            delta_quantity=Decimal("15.00"),
        )

        # Valid scrap of 5 units
        scrap_valid = StockMovementService.create_movement(
            organization=self.org,
            movement_type=StockMovementType.SCRAP,
            source_warehouse=self.wh_primary,
            reference_document="SCRAP-DMG-01",
            created_by=self.user,
            lines_data=[
                {
                    "product": self.product,
                    "quantity": Decimal("5.00"),
                    "source_location": self.loc_primary_gen1,
                    "notes": "Forklift impact damage",
                }
            ],
        )
        StockMovementService.post_movement(scrap_valid, posted_by=self.user)
        stock_after_scrap = StockItem.objects.get(
            warehouse=self.wh_primary,
            location=self.loc_primary_gen1,
            product=self.product,
        )
        self.assertEqual(stock_after_scrap.quantity_on_hand, Decimal("10.00"))

        # Attempt to scrap 20 units (exceeds 10 on-hand)
        scrap_invalid = StockMovementService.create_movement(
            organization=self.org,
            movement_type=StockMovementType.SCRAP,
            source_warehouse=self.wh_primary,
            reference_document="SCRAP-OVER",
            created_by=self.user,
            lines_data=[
                {
                    "product": self.product,
                    "quantity": Decimal("20.00"),
                    "source_location": self.loc_primary_gen1,
                }
            ],
        )
        with self.assertRaises(ValidationError):
            StockMovementService.post_movement(scrap_invalid, posted_by=self.user)

        # Verify stock remains unchanged at 10.00
        stock_after_fail = StockItem.objects.get(
            warehouse=self.wh_primary,
            location=self.loc_primary_gen1,
            product=self.product,
        )
        self.assertEqual(stock_after_fail.quantity_on_hand, Decimal("10.00"))

    def test_cancellation_and_double_posting_guards(self):
        draft_movement = StockMovementService.create_movement(
            organization=self.org,
            movement_type=StockMovementType.RECEIPT,
            destination_warehouse=self.wh_primary,
            created_by=self.user,
            lines_data=[
                {
                    "product": self.product,
                    "quantity": Decimal("10.00"),
                    "destination_location": self.loc_primary_gen1,
                }
            ],
        )
        # Cancel draft
        cancelled = StockMovementService.cancel_movement(draft_movement, cancelled_by=self.user, reason="Duplicate PO")
        self.assertEqual(cancelled.status, StockMovementStatus.CANCELLED)
        self.assertIn("Duplicate PO", cancelled.notes)

        # Cannot post a cancelled movement
        with self.assertRaises(ValidationError):
            StockMovementService.post_movement(cancelled, posted_by=self.user)

        # Create and post another movement
        new_movement = StockMovementService.create_movement(
            organization=self.org,
            movement_type=StockMovementType.RECEIPT,
            destination_warehouse=self.wh_primary,
            created_by=self.user,
            lines_data=[
                {
                    "product": self.product,
                    "quantity": Decimal("10.00"),
                    "destination_location": self.loc_primary_gen1,
                }
            ],
        )
        posted = StockMovementService.post_movement(new_movement, posted_by=self.user)
        self.assertEqual(posted.status, StockMovementStatus.COMPLETED)

        # Cannot post again
        with self.assertRaises(ValidationError):
            StockMovementService.post_movement(posted, posted_by=self.user)

        # Cannot cancel a completed movement
        with self.assertRaises(ValidationError):
            StockMovementService.cancel_movement(posted, cancelled_by=self.user)

    def test_ledger_history_and_views(self):
        self.client.force_login(self.user)

        # Post receipt
        receipt = StockMovementService.create_movement(
            organization=self.org,
            movement_type=StockMovementType.RECEIPT,
            destination_warehouse=self.wh_primary,
            reference_document="PO-VIEW-TEST",
            created_by=self.user,
            lines_data=[
                {
                    "product": self.product,
                    "quantity": Decimal("25.00"),
                    "destination_location": self.loc_primary_gen1,
                    "unit_cost": Decimal("150.00"),
                }
            ],
        )
        StockMovementService.post_movement(receipt, posted_by=self.user)

        # Audit ledger query
        ledger = StockMovementService.get_ledger_history(
            organization=self.org,
            product=self.product,
        )
        self.assertEqual(ledger.count(), 1)
        self.assertEqual(ledger.first().quantity, Decimal("25.00"))

        # Movement List View
        res_list = self.client.get(reverse("inventory:movement_list"))
        self.assertEqual(res_list.status_code, 200)
        self.assertContains(res_list, receipt.movement_number)

        # Movement Detail View
        res_detail = self.client.get(reverse("inventory:movement_detail", kwargs={"pk": receipt.pk}))
        self.assertEqual(res_detail.status_code, 200)
        self.assertContains(res_detail, receipt.movement_number)
        self.assertContains(res_detail, "Smart Rack PDU 30A 208V")

        # Movement Print View
        res_print = self.client.get(reverse("inventory:movement_print", kwargs={"pk": receipt.pk}))
        self.assertEqual(res_print.status_code, 200)
        self.assertContains(res_print, receipt.movement_number)

        # Stock Ledger View
        res_ledger = self.client.get(reverse("inventory:stock_ledger"))
        self.assertEqual(res_ledger.status_code, 200)
        self.assertContains(res_ledger, receipt.movement_number)
