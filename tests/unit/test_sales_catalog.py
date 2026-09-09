"""
EnterpriseOne Unit Tests — Sales Catalog & Pricing Engine (Milestone 4.1).
Tests Product, ProductCategory, UnitOfMeasure, PriceBook, PriceBookEntry,
TieredDiscount models, and PricingEngineService calculations.
"""
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from apps.accounts.models import User
from apps.organizations.models import Organization
from apps.sales.models import (
    Product,
    ProductCategory,
    UnitOfMeasure,
    PriceBook,
    PriceBookEntry,
    TieredDiscount,
)
from apps.sales.services import PricingEngineService


class SalesCatalogTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="sales.admin@enterpriseone.com",
            password="StrongPassword123!",
            first_name="Sales",
            last_name="Director",
        )
        self.org = Organization.objects.create(
            name="Global Enterprise Inc",
            code="GLB-ENT",
            slug="global-enterprise",
            currency="USD",
        )
        self.category = ProductCategory.objects.create(
            organization=self.org,
            name="Hardware Systems",
            code="HW-SYS",
        )
        self.sub_category = ProductCategory.objects.create(
            organization=self.org,
            name="Networking",
            code="NET",
            parent=self.category,
        )
        self.uom_unit = UnitOfMeasure.objects.create(
            organization=self.org,
            name="Unit",
            code="EA",
            category="unit",
            is_base_unit=True,
            ratio_to_base=Decimal("1.0000"),
        )
        self.uom_box = UnitOfMeasure.objects.create(
            organization=self.org,
            name="Box of 10",
            code="BOX10",
            category="unit",
            is_base_unit=False,
            ratio_to_base=Decimal("10.0000"),
        )

    def test_product_creation_and_margins(self):
        """Validates product margins and SKU constraints."""
        product = Product.objects.create(
            organization=self.org,
            name="Enterprise Core Router 9000",
            sku="RTR-9000",
            product_type="goods",
            category=self.sub_category,
            uom=self.uom_unit,
            cost_price=Decimal("400.00"),
            list_price=Decimal("1000.00"),
            created_by=self.user,
        )
        self.assertEqual(product.profit_margin, Decimal("600.00"))
        self.assertEqual(product.margin_percentage, Decimal("60.00"))
        self.assertEqual(str(product), "Enterprise Core Router 9000 [RTR-9000]")

        # Duplicate SKU within same organization must fail
        with self.assertRaises(Exception):
            Product.objects.create(
                organization=self.org,
                name="Duplicate Router",
                sku="RTR-9000",
                uom=self.uom_unit,
            )

    def test_category_hierarchy_and_cycle_prevention(self):
        """Validates category breadcrumbs and self-parent prevention."""
        leaf = ProductCategory.objects.create(
            organization=self.org,
            name="Core Switches",
            code="SW-CORE",
            parent=self.sub_category,
        )
        self.assertEqual(leaf.get_full_path(), "Hardware Systems > Networking > Core Switches")

        # Test self-parent validation
        leaf.parent = leaf
        with self.assertRaises(ValidationError):
            leaf.clean()

    def test_uom_unit_conversions(self):
        """Validates conversion logic between base and non-base UOMs."""
        self.assertEqual(self.uom_box.convert_to_base(Decimal("5")), Decimal("50.0000"))
        self.assertEqual(self.uom_box.convert_from_base(Decimal("30")), Decimal("3.0000"))

    def test_price_book_default_switch_and_validity(self):
        """Validates default price book switching and effective date rules."""
        pb1 = PriceBook.objects.create(
            organization=self.org,
            name="Standard Price Book",
            code="PB-STD",
            is_default=True,
            created_by=self.user,
        )
        self.assertTrue(pb1.is_default)
        self.assertTrue(pb1.is_effective())

        pb2 = PriceBook.objects.create(
            organization=self.org,
            name="Wholesale Price Book",
            code="PB-WHOLESALE",
            is_default=True,
            created_by=self.user,
        )
        pb1.refresh_from_db()
        self.assertFalse(pb1.is_default)
        self.assertTrue(pb2.is_default)

        # Date validity
        yesterday = timezone.now().date() - timezone.timedelta(days=1)
        pb2.valid_to = yesterday
        self.assertFalse(pb2.is_effective())

    def test_pricing_engine_resolution_and_volume_tiers(self):
        """Tests end-to-end pricing calculation with volume discount tiers."""
        product = Product.objects.create(
            organization=self.org,
            name="Enterprise Server Rack",
            sku="SRV-RCK",
            product_type="goods",
            category=self.category,
            uom=self.uom_unit,
            cost_price=Decimal("500.00"),
            list_price=Decimal("1200.00"),
            created_by=self.user,
        )

        # 1. Fallback to list price when no price book is active
        res_fallback = PricingEngineService.resolve_price(self.org, product, quantity=2)
        self.assertEqual(res_fallback.base_unit_price, Decimal("1200.00"))
        self.assertEqual(res_fallback.effective_unit_price, Decimal("1200.00"))
        self.assertEqual(res_fallback.net_total_amount, Decimal("2400.00"))
        self.assertFalse(res_fallback.tier_discount_applied)

        # 2. Add to Default Price Book
        default_pb = PriceBook.objects.create(
            organization=self.org,
            name="Standard Pricing",
            code="STD",
            is_default=True,
            created_by=self.user,
        )
        entry = PriceBookEntry.objects.create(
            organization=self.org,
            price_book=default_pb,
            product=product,
            unit_price=Decimal("1100.00"),
            minimum_quantity=1,
        )

        # Volume Tier: 5 to 19 units -> 10% off
        TieredDiscount.objects.create(
            organization=self.org,
            price_book_entry=entry,
            min_quantity=5,
            max_quantity=19,
            discount_type="percentage",
            discount_value=Decimal("10.00"),
        )
        # Volume Tier: 20+ units -> Fixed $900 unit price
        TieredDiscount.objects.create(
            organization=self.org,
            price_book_entry=entry,
            min_quantity=20,
            max_quantity=None,
            discount_type="fixed_price",
            discount_value=Decimal("900.00"),
        )

        # Query for 1 unit (standard book price $1100)
        res_single = PricingEngineService.resolve_price(self.org, product, quantity=1)
        self.assertEqual(res_single.base_unit_price, Decimal("1100.00"))
        self.assertEqual(res_single.effective_unit_price, Decimal("1100.00"))
        self.assertEqual(res_single.net_total_amount, Decimal("1100.00"))
        self.assertFalse(res_single.tier_discount_applied)

        # Query for 10 units (10% off $1100 = $990)
        res_tier1 = PricingEngineService.resolve_price(self.org, product, quantity=10)
        self.assertEqual(res_tier1.base_unit_price, Decimal("1100.00"))
        self.assertEqual(res_tier1.effective_unit_price, Decimal("990.00"))
        self.assertEqual(res_tier1.unit_discount, Decimal("110.00"))
        self.assertEqual(res_tier1.discount_amount, Decimal("1100.00"))
        self.assertEqual(res_tier1.net_total_amount, Decimal("9900.00"))
        self.assertTrue(res_tier1.tier_discount_applied)

        # Query for 25 units ($900 fixed unit price)
        res_tier2 = PricingEngineService.resolve_price(self.org, product, quantity=25)
        self.assertEqual(res_tier2.base_unit_price, Decimal("1100.00"))
        self.assertEqual(res_tier2.effective_unit_price, Decimal("900.00"))
        self.assertEqual(res_tier2.unit_discount, Decimal("200.00"))
        self.assertEqual(res_tier2.discount_amount, Decimal("5000.00"))
        self.assertEqual(res_tier2.net_total_amount, Decimal("22500.00"))
        self.assertTrue(res_tier2.tier_discount_applied)

    def test_catalog_initialization(self):
        """Validates idempotent seeding of standard UOMs and default price book."""
        res = PricingEngineService.initialize_default_catalog(self.org, created_by=self.user)
        self.assertIn("uoms", res)
        self.assertIn("default_price_book", res)
        self.assertEqual(res["default_price_book"].code, "STANDARD")

        # Running again should be idempotent without duplicate errors
        res2 = PricingEngineService.initialize_default_catalog(self.org, created_by=self.user)
        self.assertEqual(res["default_price_book"].pk, res2["default_price_book"].pk)
