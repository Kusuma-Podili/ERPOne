"""
EnterpriseOne Unit Tests — Quote Calculations & Precision Accounting (Milestone 4.2).
Validates quote numbering, line item discounts, tax calculations, and header aggregation.
"""
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from apps.accounts.models import User
from apps.organizations.models import Organization
from apps.crm.models import Account, Contact, AccountType
from apps.sales.models import (
    Product,
    UnitOfMeasure,
    Quote,
    QuoteLineItem,
    QuoteStatus,
)
from apps.sales.services import QuoteCalculationService


class QuoteCalculationTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="salesrep@enterpriseone.com",
            password="StrongPassword123!",
            first_name="Quote",
            last_name="Specialist",
        )
        self.org = Organization.objects.create(
            name="Apex Commercial Enterprise",
            code="APEX-COM",
            slug="apex-commercial",
            currency="USD",
        )
        self.account = Account.objects.create(
            organization=self.org,
            name="MegaCorp Logistics",
            account_type=AccountType.CUSTOMER,
            owner=self.user,
        )
        self.uom = UnitOfMeasure.objects.create(
            organization=self.org,
            name="Unit",
            code="EA",
            category="unit",
            is_base_unit=True,
        )
        self.product_a = Product.objects.create(
            organization=self.org,
            name="Industrial Sensor Node",
            sku="IND-SNR-01",
            uom=self.uom,
            cost_price=Decimal("50.00"),
            list_price=Decimal("150.00"),
        )
        self.product_b = Product.objects.create(
            organization=self.org,
            name="Cloud Gateway Appliance",
            sku="GW-CLD-99",
            uom=self.uom,
            cost_price=Decimal("200.00"),
            list_price=Decimal("500.00"),
        )

    def test_quote_auto_numbering(self):
        """Verifies automatic sequential quote numbering."""
        quote1 = Quote.objects.create(
            organization=self.org,
            title="Q1 Facility Modernization",
            account=self.account,
            created_by=self.user,
        )
        self.assertTrue(quote1.quote_number.startswith(f"QT-{timezone.now().year}"))

        quote2 = Quote.objects.create(
            organization=self.org,
            title="Q2 Facility Expansion",
            account=self.account,
            created_by=self.user,
        )
        self.assertNotEqual(quote1.quote_number, quote2.quote_number)

    def test_quote_line_calculations(self):
        """Verifies line subtotal, discount, tax, and total pricing."""
        quote = Quote.objects.create(
            organization=self.org,
            title="Hardware Supply Quote",
            account=self.account,
            created_by=self.user,
        )
        # 10 units @ $150 = $1500. 10% discount = $150. Taxable = $1350. Tax 8.25% = $111.38. Total = $1461.38.
        line = QuoteLineItem.objects.create(
            organization=self.org,
            quote=quote,
            product=self.product_a,
            quantity=10,
            unit_price=Decimal("150.00"),
            discount_percent=Decimal("10.00"),
            tax_rate=Decimal("8.25"),
        )
        self.assertEqual(line.subtotal, Decimal("1500.00"))
        self.assertEqual(line.discount_amount, Decimal("150.00"))
        self.assertEqual(line.tax_amount, Decimal("111.38"))
        self.assertEqual(line.total_price, Decimal("1461.38"))

    def test_quote_recalculate_totals_with_shipping(self):
        """Verifies multi-line aggregation and shipping inclusion."""
        quote = Quote.objects.create(
            organization=self.org,
            title="Full Deployment Package",
            account=self.account,
            shipping_amount=Decimal("75.00"),
            created_by=self.user,
        )
        # Line 1: 5 x $150 = $750 (0% discount, 5% tax = $37.50)
        QuoteCalculationService.add_line_item(
            quote=quote,
            product=self.product_a,
            quantity=5,
            discount_percent=Decimal("0.00"),
            tax_rate=Decimal("5.00"),
            unit_price=Decimal("150.00"),
        )
        # Line 2: 2 x $500 = $1000 (10% discount = $100. Taxable $900 @ 10% tax = $90)
        QuoteCalculationService.add_line_item(
            quote=quote,
            product=self.product_b,
            quantity=2,
            discount_percent=Decimal("10.00"),
            tax_rate=Decimal("10.00"),
            unit_price=Decimal("500.00"),
        )

        quote.refresh_from_db()
        # Subtotal: 750 + 1000 = 1750.00
        self.assertEqual(quote.subtotal_amount, Decimal("1750.00"))
        # Discount: 0 + 100 = 100.00
        self.assertEqual(quote.discount_amount, Decimal("100.00"))
        # Tax: 37.50 + 90.00 = 127.50
        self.assertEqual(quote.tax_amount, Decimal("127.50"))
        # Grand Total: 1750 - 100 + 127.50 + 75.00 (shipping) = 1852.50
        self.assertEqual(quote.grand_total, Decimal("1852.50"))

    def test_quote_expiration_check(self):
        """Validates is_expired() method."""
        quote = Quote.objects.create(
            organization=self.org,
            title="Expiring Deal",
            account=self.account,
            valid_until=timezone.now().date() - timezone.timedelta(days=2),
            created_by=self.user,
        )
        self.assertTrue(quote.is_expired())

        quote.valid_until = timezone.now().date() + timezone.timedelta(days=10)
        self.assertFalse(quote.is_expired())
