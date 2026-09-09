"""
EnterpriseOne Unit Tests — Lot/Batch & Serial Number Domain Models (Milestone 5.3).
Tests LotBatch, SerialNumber, QCStatus, and SerialStatus models,
enforcing shelf-life date ordering, warranty validity, unique batch/serial constraints, and usability status.
"""
from datetime import timedelta
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
    StorageZone,
    StorageLocation,
    QCStatus,
    SerialStatus,
    LotBatch,
    SerialNumber,
)


class LotSerialModelsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="qc.lead@enterpriseone.com",
            password="StrongPassword123!",
            first_name="Quinn",
            last_name="Quality",
        )
        self.org = Organization.objects.create(
            name="AeroPrecision Technologies",
            code="AERO-TECH",
            slug="aero-tech",
            currency="USD",
        )
        self.other_org = Organization.objects.create(
            name="Vanguard Supply Group",
            code="VNG-SUPPLY",
            slug="vanguard-supply-group",
            currency="USD",
        )
        self.category = ProductCategory.objects.create(
            organization=self.org,
            name="Avionics & Flight Hardware",
            code="AV-HW",
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
            name="Altitude Telemetry Transceiver",
            sku="TRANS-ALT-900",
            cost_price=Decimal("450.00"),
            list_price=Decimal("899.00"),
        )

        self.warehouse = Warehouse.objects.create(
            organization=self.org,
            name="Hangar Logistics Hub",
            code="HGR-01",
            is_primary=True,
        )

    def test_lot_batch_creation_and_properties(self):
        today = timezone.now().date()
        future_date = today + timedelta(days=90)
        past_mfg = today - timedelta(days=30)

        lot = LotBatch.objects.create(
            organization=self.org,
            product=self.product,
            batch_number="LOT-2026-AV01",
            supplier_lot_number="SUP-LOT-882",
            manufacturing_date=past_mfg,
            expiration_date=future_date,
            initial_quantity=Decimal("50.00"),
            current_quantity=Decimal("50.00"),
            qc_status=QCStatus.APPROVED,
            certificate_of_analysis="COA-2026-0044.PDF",
        )

        self.assertEqual(str(lot), f"TRANS-ALT-900 - Lot LOT-2026-AV01 (Exp: {future_date})")
        self.assertFalse(lot.is_expired)
        self.assertEqual(lot.days_until_expiration, 90)
        self.assertTrue(lot.is_usable)

    def test_lot_batch_expired_and_quarantine_usability(self):
        today = timezone.now().date()
        expired_date = today - timedelta(days=5)

        # Expired lot is not usable even if approved
        expired_lot = LotBatch.objects.create(
            organization=self.org,
            product=self.product,
            batch_number="LOT-OLD-001",
            expiration_date=expired_date,
            qc_status=QCStatus.APPROVED,
        )
        self.assertTrue(expired_lot.is_expired)
        self.assertFalse(expired_lot.is_usable)

        # Quarantined lot is not usable even if unexpired
        quarantine_lot = LotBatch.objects.create(
            organization=self.org,
            product=self.product,
            batch_number="LOT-QUAR-001",
            expiration_date=today + timedelta(days=60),
            qc_status=QCStatus.QUARANTINED,
        )
        self.assertFalse(quarantine_lot.is_expired)
        self.assertFalse(quarantine_lot.is_usable)

    def test_lot_batch_date_validation(self):
        today = timezone.now().date()
        # Expiration date earlier than manufacturing date must raise ValidationError
        invalid_lot = LotBatch(
            organization=self.org,
            product=self.product,
            batch_number="LOT-INVALID-DATES",
            manufacturing_date=today,
            expiration_date=today - timedelta(days=1),
        )
        with self.assertRaises(ValidationError) as ctx:
            invalid_lot.full_clean()
        self.assertIn("expiration_date", ctx.exception.message_dict)

    def test_lot_batch_unique_constraint(self):
        LotBatch.objects.create(
            organization=self.org,
            product=self.product,
            batch_number="LOT-UNIQUE-01",
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                LotBatch.objects.create(
                    organization=self.org,
                    product=self.product,
                    batch_number="LOT-UNIQUE-01",
                )

    def test_serial_number_creation_and_warranty(self):
        today = timezone.now().date()
        warranty_end = today + timedelta(days=365)

        serial = SerialNumber.objects.create(
            organization=self.org,
            product=self.product,
            serial_number="SN-AERO-0001",
            warehouse=self.warehouse,
            status=SerialStatus.IN_STOCK,
            warranty_start_date=today,
            warranty_end_date=warranty_end,
        )

        self.assertEqual(str(serial), "Altitude Telemetry Transceiver [SN: SN-AERO-0001]")
        self.assertTrue(serial.is_under_warranty)

        # Expired warranty test
        expired_serial = SerialNumber.objects.create(
            organization=self.org,
            product=self.product,
            serial_number="SN-AERO-0002",
            warranty_end_date=today - timedelta(days=10),
        )
        self.assertFalse(expired_serial.is_under_warranty)

    def test_serial_number_unique_constraint(self):
        SerialNumber.objects.create(
            organization=self.org,
            product=self.product,
            serial_number="SN-DUP-01",
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                SerialNumber.objects.create(
                    organization=self.org,
                    product=self.product,
                    serial_number="SN-DUP-01",
                )
