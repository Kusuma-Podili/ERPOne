"""
EnterpriseOne Integration Tests — Lot/Batch, Serial Number & FEFO Inventory Services (Milestone 5.3).
Validates lot lifecycle, QC inspection transitions, bulk serialization, FEFO allocation algorithm,
expiry threshold auditing, and multi-tenant authenticated views.
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
from apps.inventory.models import (
    Warehouse,
    StorageZone,
    StorageLocation,
    QCStatus,
    SerialStatus,
    LotBatch,
    SerialNumber,
)
from apps.inventory.services import (
    WarehouseHierarchyService,
    LotSerialTrackingService,
)


class LotSerialTrackingIntegrationTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="qc.supervisor@enterpriseone.com",
            password="StrongPassword123!",
            first_name="Sierra",
            last_name="Quality",
        )
        self.org = Organization.objects.create(
            name="Apex Biosystems Ltd",
            code="APX-BIO",
            slug="apex-biosystems",
            currency="USD",
        )
        OrganizationMember.objects.create(
            organization=self.org,
            user=self.user,
            is_org_admin=True,
            status="ACTIVE",
        )

        self.other_org = Organization.objects.create(
            name="Rival Diagnostics Inc",
            code="RIV-DIAG",
            slug="rival-diagnostics",
            currency="USD",
        )

        self.category = ProductCategory.objects.create(
            organization=self.org,
            name="Clinical Reagents",
            code="CLN-REAG",
        )
        self.uom = UnitOfMeasure.objects.create(
            organization=self.org,
            name="Vial",
            code="VIAL",
            category="unit",
            is_base_unit=True,
            ratio_to_base=Decimal("1.0000"),
        )
        self.product = Product.objects.create(
            organization=self.org,
            category=self.category,
            uom=self.uom,
            name="DNA Polymerase Master Mix 500U",
            sku="BIO-DNA-500",
            cost_price=Decimal("60.00"),
            list_price=Decimal("120.00"),
        )

        prov = WarehouseHierarchyService.provision_standard_warehouse(
            organization=self.org,
            name="Biotech Cold Storage Hub",
            code="BIO-HUB",
            is_primary=True,
            manager=self.user,
        )
        self.warehouse = prov["warehouse"]
        self.location = prov["locations"][0]

    def test_register_lot_and_quantity_adjustments(self):
        today = timezone.now().date()
        lot = LotSerialTrackingService.register_lot(
            organization=self.org,
            product=self.product,
            batch_number="LOT-2026-DNA-01",
            manufacturing_date=today - timedelta(days=10),
            expiration_date=today + timedelta(days=180),
            initial_quantity=Decimal("100.00"),
            qc_status=QCStatus.APPROVED,
            certificate_of_analysis="COA-DNA-001.pdf",
        )
        self.assertEqual(lot.initial_quantity, Decimal("100.00"))
        self.assertEqual(lot.current_quantity, Decimal("100.00"))
        self.assertTrue(lot.is_usable)

        # Adjust quantity upwards (e.g. inventory count found extra)
        LotSerialTrackingService.adjust_lot_quantity(lot, Decimal("20.00"))
        self.assertEqual(lot.current_quantity, Decimal("120.00"))

        # Adjust quantity downwards
        LotSerialTrackingService.adjust_lot_quantity(lot, Decimal("-30.00"))
        self.assertEqual(lot.current_quantity, Decimal("90.00"))

        # Attempt to reduce below zero
        with self.assertRaises(ValidationError):
            LotSerialTrackingService.adjust_lot_quantity(lot, Decimal("-100.00"))

    def test_update_qc_status_lifecycle(self):
        today = timezone.now().date()
        lot = LotSerialTrackingService.register_lot(
            organization=self.org,
            product=self.product,
            batch_number="LOT-PENDING-QC",
            expiration_date=today + timedelta(days=90),
            initial_quantity=Decimal("40.00"),
            qc_status=QCStatus.QUARANTINED,
        )
        self.assertFalse(lot.is_usable)

        # Update to Approved with notes
        LotSerialTrackingService.update_qc_status(
            lot=lot,
            new_status=QCStatus.APPROVED,
            inspected_by=self.user,
            qc_notes="High purity spectrophotometry confirmed 99.4%.",
        )
        self.assertEqual(lot.qc_status, QCStatus.APPROVED)
        self.assertEqual(lot.qc_inspected_by, self.user)
        self.assertIsNotNone(lot.qc_inspected_at)
        self.assertIn("High purity spectrophotometry", lot.qc_notes)
        self.assertTrue(lot.is_usable)

    def test_bulk_register_serials_and_lifecycle(self):
        today = timezone.now().date()
        lot = LotSerialTrackingService.register_lot(
            organization=self.org,
            product=self.product,
            batch_number="LOT-SERIAL-TEST",
            expiration_date=today + timedelta(days=365),
            initial_quantity=Decimal("5.00"),
        )
        raw_serials = ["SN-DNA-001", "SN-DNA-002", "SN-DNA-003", "", "   "]
        created = LotSerialTrackingService.bulk_register_serials(
            organization=self.org,
            product=self.product,
            serial_numbers_list=raw_serials,
            lot=lot,
            warehouse=self.warehouse,
            location=self.location,
            warranty_start_date=today,
            warranty_end_date=today + timedelta(days=365),
        )
        # Empty rows ignored, 3 created
        self.assertEqual(len(created), 3)
        self.assertEqual(SerialNumber.objects.filter(lot=lot).count(), 3)

        # Update serial status
        sn1 = created[0]
        self.assertEqual(sn1.status, SerialStatus.IN_STOCK)
        LotSerialTrackingService.update_serial_status(
            serial=sn1,
            new_status=SerialStatus.DISPATCHED,
            notes="Dispatched on SO-2026-0044",
        )
        self.assertEqual(sn1.status, SerialStatus.DISPATCHED)
        self.assertIn("SO-2026-0044", sn1.notes)

    def test_fefo_allocation_algorithm(self):
        today = timezone.now().date()

        # Batch 1: Expiring in 10 days (20 units available)
        lot_exp_10d = LotSerialTrackingService.register_lot(
            organization=self.org,
            product=self.product,
            batch_number="LOT-EXP-10D",
            expiration_date=today + timedelta(days=10),
            initial_quantity=Decimal("20.00"),
            qc_status=QCStatus.APPROVED,
        )

        # Batch 2: Expiring in 45 days (30 units available)
        lot_exp_45d = LotSerialTrackingService.register_lot(
            organization=self.org,
            product=self.product,
            batch_number="LOT-EXP-45D",
            expiration_date=today + timedelta(days=45),
            initial_quantity=Decimal("30.00"),
            qc_status=QCStatus.APPROVED,
        )

        # Batch 3: Expiring in 180 days (50 units available)
        lot_exp_180d = LotSerialTrackingService.register_lot(
            organization=self.org,
            product=self.product,
            batch_number="LOT-EXP-180D",
            expiration_date=today + timedelta(days=180),
            initial_quantity=Decimal("50.00"),
            qc_status=QCStatus.APPROVED,
        )

        # Batch 4: Quarantined batch (should be skipped by FEFO)
        LotSerialTrackingService.register_lot(
            organization=self.org,
            product=self.product,
            batch_number="LOT-QUAR-SKIP",
            expiration_date=today + timedelta(days=5),
            initial_quantity=Decimal("10.00"),
            qc_status=QCStatus.QUARANTINED,
        )

        # Request 35 units under FEFO
        fefo_res = LotSerialTrackingService.get_fefo_allocation(
            organization=self.org,
            product=self.product,
            requested_quantity=Decimal("35.00"),
        )
        self.assertTrue(fefo_res["is_fully_allocated"])
        self.assertEqual(fefo_res["allocated_quantity"], Decimal("35.00"))
        self.assertEqual(fefo_res["unallocated_quantity"], Decimal("0.00"))

        allocs = fefo_res["allocations"]
        self.assertEqual(len(allocs), 2)
        # First allocation from 10-day expiry lot (20 units)
        self.assertEqual(allocs[0]["batch_number"], "LOT-EXP-10D")
        self.assertEqual(allocs[0]["allocated_quantity"], Decimal("20.00"))
        # Second allocation from 45-day expiry lot (remaining 15 units)
        self.assertEqual(allocs[1]["batch_number"], "LOT-EXP-45D")
        self.assertEqual(allocs[1]["allocated_quantity"], Decimal("15.00"))

    def test_expiring_batches_and_views(self):
        self.client.force_login(self.user)
        today = timezone.now().date()

        # Batch expiring in 15 days
        lot_urgent = LotSerialTrackingService.register_lot(
            organization=self.org,
            product=self.product,
            batch_number="LOT-URGENT",
            expiration_date=today + timedelta(days=15),
            initial_quantity=Decimal("25.00"),
        )

        # Batch in other organization
        other_product = Product.objects.create(
            organization=self.other_org,
            uom=self.uom,
            name="Rival Reagent",
            sku="RIV-01",
        )
        other_lot = LotSerialTrackingService.register_lot(
            organization=self.other_org,
            product=other_product,
            batch_number="RIVAL-LOT",
            expiration_date=today + timedelta(days=15),
        )

        # Service returns urgent lot
        expiring = LotSerialTrackingService.get_expiring_batches(
            organization=self.org,
            days_threshold=30,
        )
        self.assertEqual(expiring.count(), 1)
        self.assertEqual(expiring.first(), lot_urgent)

        # View: Lot List View
        res_list = self.client.get(reverse("inventory:lot_list"))
        self.assertEqual(res_list.status_code, 200)
        self.assertContains(res_list, "LOT-URGENT")
        self.assertNotContains(res_list, "RIVAL-LOT")

        # View: Lot Detail View
        res_detail = self.client.get(reverse("inventory:lot_detail", kwargs={"pk": lot_urgent.pk}))
        self.assertEqual(res_detail.status_code, 200)
        self.assertContains(res_detail, "LOT-URGENT")

        # View: Expiring Stock Report View
        res_exp = self.client.get(reverse("inventory:expiring_stock"))
        self.assertEqual(res_exp.status_code, 200)
        self.assertContains(res_exp, "LOT-URGENT")

        # View: Serial List View
        res_serials = self.client.get(reverse("inventory:serial_list"))
        self.assertEqual(res_serials.status_code, 200)
