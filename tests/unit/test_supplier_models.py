"""
Unit Tests for Procurement Domain Models (Milestone 6.1).
Tests Supplier, SupplierContact, and SupplierProduct offering integrity, ratings, and constraints.
"""
from decimal import Decimal
from django.test import TestCase
from django.db import IntegrityError, transaction
from django.core.exceptions import ValidationError
from apps.organizations.models import Organization
from apps.sales.models import Product, ProductCategory, UnitOfMeasure
from apps.procurement.models import (
    Supplier,
    SupplierType,
    PaymentTerms,
    SupplierStatus,
    SupplierContact,
    SupplierProduct,
)


class SupplierModelTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Apex Manufacturing",
            code="APEX-MFG",
            slug="apex-mfg",
        )
        self.other_org = Organization.objects.create(
            name="Global Logistics",
            code="GLOBAL-LOG",
            slug="global-log",
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

    def test_supplier_creation_and_defaults(self):
        supplier = Supplier.objects.create(
            organization=self.org,
            name="Titanium Precision Mills Inc.",
            code="SUPP-TI-01",
            supplier_type=SupplierType.MANUFACTURER,
            payment_terms=PaymentTerms.NET45,
            currency="USD",
            lead_time_rating=Decimal("4.5"),
            quality_rating=Decimal("4.9"),
        )
        self.assertEqual(str(supplier), "Titanium Precision Mills Inc. (SUPP-TI-01)")
        self.assertEqual(supplier.status, SupplierStatus.ACTIVE)
        self.assertEqual(supplier.overall_rating, Decimal("4.7"))
        self.assertEqual(supplier.total_products_count, 0)
        self.assertTrue(supplier.is_active)

    def test_supplier_unique_code_per_organization(self):
        Supplier.objects.create(
            organization=self.org,
            name="Vendor A",
            code="VEND-001",
        )
        # Same code in different org is allowed
        diff_org_supplier = Supplier.objects.create(
            organization=self.other_org,
            name="Vendor B",
            code="VEND-001",
        )
        self.assertEqual(diff_org_supplier.code, "VEND-001")

        # Same code in same org must raise IntegrityError
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Supplier.objects.create(
                    organization=self.org,
                    name="Vendor Duplicate",
                    code="VEND-001",
                )

    def test_supplier_contact_creation_and_ordering(self):
        supplier = Supplier.objects.create(
            organization=self.org,
            name="Fastener Express",
            code="SUPP-FAST-01",
        )
        c1 = SupplierContact.objects.create(
            supplier=supplier,
            name="John Smith",
            email="jsmith@fastenerexpress.com",
            title="Sales Rep",
            is_primary=False,
        )
        c2 = SupplierContact.objects.create(
            supplier=supplier,
            name="Sarah Jenkins",
            email="sjenkins@fastenerexpress.com",
            title="VP Commercial",
            is_primary=True,
        )
        self.assertIn("Sarah Jenkins", str(c2))
        contacts = list(supplier.contacts.all())
        # Ordered by -is_primary, name
        self.assertEqual(contacts[0].name, "Sarah Jenkins")
        self.assertEqual(contacts[1].name, "John Smith")

    def test_supplier_product_validation(self):
        supplier = Supplier.objects.create(
            organization=self.org,
            name="Raw Metals LLC",
            code="SUPP-MET-01",
        )
        offering = SupplierProduct(
            organization=self.org,
            supplier=supplier,
            product=self.product,
            unit_price=Decimal("-10.00"),
            minimum_order_quantity=Decimal("5.00"),
        )
        with self.assertRaises(ValidationError):
            offering.clean()

        offering.unit_price = Decimal("75.00")
        offering.minimum_order_quantity = Decimal("0.00")
        with self.assertRaises(ValidationError):
            offering.clean()

        offering.minimum_order_quantity = Decimal("10.00")
        offering.clean()  # Should succeed
        offering.save()
        self.assertEqual(supplier.total_products_count, 1)
        self.assertIn("SUPP-MET-01", str(offering))
