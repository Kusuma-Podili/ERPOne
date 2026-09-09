"""
Integration Tests for Supplier Catalog Services and Procurement Views (Milestone 6.1).
Tests SupplierService business flows and multi-tenant HTTP views.
"""
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.organizations.models import Organization, OrganizationMember
from apps.sales.models import Product, ProductCategory, UnitOfMeasure
from apps.procurement.models import (
    Supplier,
    SupplierType,
    PaymentTerms,
    SupplierStatus,
    SupplierContact,
    SupplierProduct,
)
from apps.procurement.services import SupplierService

User = get_user_model()


class SupplierServiceTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Apex Dynamics",
            code="APEX-DYN",
            slug="apex-dyn",
        )
        self.category = ProductCategory.objects.create(
            organization=self.org,
            name="Electronics",
            code="ELEC",
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
            name="Microcontroller IC",
            sku="IC-MCU-32",
            cost_price=Decimal("8.00"),
            list_price=Decimal("15.00"),
        )

    def test_create_supplier_service(self):
        supplier = SupplierService.create_supplier(
            organization=self.org,
            name="Silicon Components Ltd.",
            code="silicon-01",
            supplier_type=SupplierType.MANUFACTURER,
            payment_terms=PaymentTerms.NET30,
            city="San Jose",
            country="USA",
            lead_time_rating=Decimal("4.8"),
            quality_rating=Decimal("4.9"),
        )
        self.assertEqual(supplier.code, "SILICON-01")  # upper-cased
        self.assertEqual(supplier.city, "San Jose")
        self.assertEqual(supplier.overall_rating, Decimal("4.85"))

    def test_add_contact_service_primary_toggle(self):
        supplier = SupplierService.create_supplier(
            organization=self.org,
            name="Delta Chips",
            code="DELTA-01",
        )
        c1 = SupplierService.add_contact(
            supplier=supplier,
            name="Alice Cooper",
            email="alice@deltachips.com",
            is_primary=True,
        )
        self.assertTrue(c1.is_primary)

        c2 = SupplierService.add_contact(
            supplier=supplier,
            name="Bob Martin",
            email="bob@deltachips.com",
            is_primary=True,
        )
        c1.refresh_from_db()
        self.assertFalse(c1.is_primary)
        self.assertTrue(c2.is_primary)

    def test_link_product_and_get_preferred_supplier_offering(self):
        sup1 = SupplierService.create_supplier(
            organization=self.org,
            name="Vendor Alpha",
            code="VEND-A",
        )
        sup2 = SupplierService.create_supplier(
            organization=self.org,
            name="Vendor Beta",
            code="VEND-B",
        )

        off1 = SupplierService.link_product(
            supplier=sup1,
            product=self.product,
            unit_price=Decimal("9.50"),
            is_preferred=False,
        )
        off2 = SupplierService.link_product(
            supplier=sup2,
            product=self.product,
            unit_price=Decimal("8.00"),
            is_preferred=False,
        )

        # Neither is preferred, resolves lowest unit price (sup2 at 8.00)
        best = SupplierService.get_preferred_supplier_offering(self.product)
        self.assertIsNotNone(best)
        self.assertEqual(best.supplier, sup2)

        # Mark sup1 as preferred
        off1 = SupplierService.link_product(
            supplier=sup1,
            product=self.product,
            unit_price=Decimal("9.50"),
            is_preferred=True,
        )
        best = SupplierService.get_preferred_supplier_offering(self.product)
        self.assertEqual(best.supplier, sup1)

        # Mark sup2 as preferred -> sup1 should be demoted from preferred
        off2 = SupplierService.link_product(
            supplier=sup2,
            product=self.product,
            unit_price=Decimal("8.00"),
            is_preferred=True,
        )
        off1.refresh_from_db()
        self.assertFalse(off1.is_preferred)
        self.assertTrue(off2.is_preferred)
        best = SupplierService.get_preferred_supplier_offering(self.product)
        self.assertEqual(best.supplier, sup2)


class ProcurementViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.org = Organization.objects.create(
            name="Starlight Aerospace",
            code="STAR-AERO",
            slug="starlight-aero",
        )
        self.other_org = Organization.objects.create(
            name="Other Orbit",
            code="OTHER-ORBIT",
            slug="other-orbit",
        )
        self.user = User.objects.create_user(
            email="procure@starlight.com",
            password="StrongPassword123!",
            first_name="Diana",
            last_name="Prince",
        )
        OrganizationMember.objects.create(
            organization=self.org,
            user=self.user,
            is_org_admin=True,
            status="ACTIVE",
        )
        self.client.force_login(self.user)
        session = self.client.session
        session["active_organization_id"] = str(self.org.id)
        session.save()

        self.category = ProductCategory.objects.create(
            organization=self.org,
            name="Hardware",
            code="HDW",
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
            name="Titanium Bolt 10mm",
            sku="BOLT-TI-10",
            cost_price=Decimal("2.10"),
            list_price=Decimal("4.50"),
        )
        self.supplier = Supplier.objects.create(
            organization=self.org,
            name="Precision Fasteners Inc.",
            code="PREC-001",
            supplier_type=SupplierType.MANUFACTURER,
            city="Seattle",
            country="USA",
        )
        # Foreign org supplier
        self.foreign_supplier = Supplier.objects.create(
            organization=self.other_org,
            name="Foreign Secret Vendor",
            code="SECRET-001",
        )

    def test_supplier_list_view(self):
        url = reverse("procurement:supplier_list")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Precision Fasteners Inc.")
        self.assertNotContains(res, "Foreign Secret Vendor")

    def test_supplier_detail_view(self):
        url = reverse("procurement:supplier_detail", kwargs={"pk": self.supplier.pk})
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Precision Fasteners Inc.")
        self.assertContains(res, "PREC-001")

        # Accessing foreign supplier should 404
        foreign_url = reverse("procurement:supplier_detail", kwargs={"pk": self.foreign_supplier.pk})
        res_foreign = self.client.get(foreign_url)
        self.assertEqual(res_foreign.status_code, 404)

    def test_supplier_create_view(self):
        url = reverse("procurement:supplier_create")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)

        post_data = {
            "name": "Global Hydraulic Systems",
            "code": "HYD-001",
            "supplier_type": SupplierType.DISTRIBUTOR,
            "status": SupplierStatus.ACTIVE,
            "payment_terms": PaymentTerms.NET30,
            "currency": "USD",
            "lead_time_rating": "5.0",
            "quality_rating": "5.0",
            "is_active": True,
        }
        res_post = self.client.post(url, post_data)
        created = Supplier.objects.filter(organization=self.org, code="HYD-001").first()
        self.assertIsNotNone(created)
        self.assertRedirects(res_post, reverse("procurement:supplier_detail", kwargs={"pk": created.pk}))

    def test_supplier_contact_create_view(self):
        url = reverse("procurement:supplier_contact_create", kwargs={"supplier_pk": self.supplier.pk})
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)

        post_data = {
            "name": "Jane Miller",
            "title": "Account Director",
            "email": "jmiller@precisionfasteners.com",
            "phone": "555-0199",
            "is_primary": True,
        }
        res_post = self.client.post(url, post_data)
        contact = self.supplier.contacts.filter(name="Jane Miller").first()
        self.assertIsNotNone(contact)
        self.assertTrue(contact.is_primary)
        self.assertRedirects(res_post, reverse("procurement:supplier_detail", kwargs={"pk": self.supplier.pk}))

    def test_supplier_product_create_view(self):
        url = reverse("procurement:supplier_product_create", kwargs={"supplier_pk": self.supplier.pk})
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)

        post_data = {
            "product": str(self.product.pk),
            "supplier_sku": "PF-TI-10",
            "unit_price": "1.95",
            "currency": "USD",
            "minimum_order_quantity": "50.00",
            "lead_time_days": 10,
            "is_preferred": True,
            "is_active": True,
        }
        res_post = self.client.post(url, post_data)
        offering = self.supplier.supplied_products.filter(product=self.product).first()
        self.assertIsNotNone(offering)
        self.assertEqual(offering.unit_price, Decimal("1.95"))
        self.assertTrue(offering.is_preferred)
        self.assertRedirects(res_post, reverse("procurement:supplier_detail", kwargs={"pk": self.supplier.pk}))
