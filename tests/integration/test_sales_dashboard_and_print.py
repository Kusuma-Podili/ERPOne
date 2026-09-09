"""
EnterpriseOne Integration Tests - Sales Operations Dashboard and Print-Ready Layouts (Milestone 4.4).
Validates dashboard executive KPI aggregation, quotation/order print rendering, and multi-tenant security.
"""
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from apps.accounts.models import User
from apps.organizations.models import Organization, OrganizationMember
from apps.crm.models import Account, AccountType
from apps.sales.models import (
    Product,
    ProductCategory,
    UnitOfMeasure,
    Quote,
    QuoteStatus,
    SalesOrder,
    OrderStatus,
)
from apps.sales.services import QuoteCalculationService


class SalesDashboardAndPrintTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="salesdirector@enterpriseone.com",
            password="StrongPassword123!",
            first_name="Diana",
            last_name="Director",
        )
        self.org = Organization.objects.create(
            name="Apex Dynamics Corp",
            code="APEXDYN",
            slug="apex-dynamics",
            currency="USD",
        )
        OrganizationMember.objects.create(
            organization=self.org,
            user=self.user,
            is_org_admin=True,
            status="ACTIVE",
        )

        # Other org for tenant isolation tests
        self.other_org = Organization.objects.create(
            name="Other Global Inc",
            code="OTHERGLB",
            slug="other-global",
            currency="USD",
        )

        self.account = Account.objects.create(
            organization=self.org,
            name="Apex Horizon Systems",
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
        self.category = ProductCategory.objects.create(
            organization=self.org,
            name="Advanced Hardware",
            code="ADV-HW",
        )
        self.product = Product.objects.create(
            organization=self.org,
            category=self.category,
            name="Quantum Server Blade",
            sku="QSB-9000",
            uom=self.uom,
            cost_price=Decimal("4000.00"),
            list_price=Decimal("8000.00"),
        )

    def test_anonymous_access_redirects_to_login(self):
        url = reverse("sales:dashboard")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("login", resp.url)

    def test_sales_dashboard_metrics_aggregation(self):
        self.client.login(email="salesdirector@enterpriseone.com", password="StrongPassword123!")
        session = self.client.session
        session["active_organization_id"] = str(self.org.id)
        session.save()

        # Create 1 converted quote and 1 draft quote
        q1 = Quote.objects.create(
            organization=self.org,
            title="Strategic Data Center",
            account=self.account,
            status=QuoteStatus.CONVERTED,
            created_by=self.user,
        )
        QuoteCalculationService.add_line_item(
            quote=q1, product=self.product, quantity=2, unit_price=Decimal("8000.00")
        )

        q2 = Quote.objects.create(
            organization=self.org,
            title="Secondary Expansion",
            account=self.account,
            status=QuoteStatus.DRAFT,
            created_by=self.user,
        )
        QuoteCalculationService.add_line_item(
            quote=q2, product=self.product, quantity=1, unit_price=Decimal("8000.00")
        )

        # Create 1 confirmed order and 1 fulfilled order
        o1 = SalesOrder.objects.create(
            organization=self.org,
            account=self.account,
            status=OrderStatus.CONFIRMED,
            created_by=self.user,
            subtotal_amount=Decimal("16000.00"),
            grand_total=Decimal("16000.00"),
        )
        o2 = SalesOrder.objects.create(
            organization=self.org,
            account=self.account,
            status=OrderStatus.FULFILLED,
            created_by=self.user,
            subtotal_amount=Decimal("8000.00"),
            grand_total=Decimal("8000.00"),
        )

        url = reverse("sales:dashboard")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "sales/dashboard.html")

        ctx = resp.context
        self.assertEqual(ctx["total_quotes"], 2)
        self.assertEqual(ctx["quotes_converted"], 1)
        self.assertEqual(ctx["quotes_draft"], 1)
        self.assertEqual(ctx["conversion_rate"], 50.0)

        self.assertEqual(ctx["total_orders"], 2)
        self.assertEqual(ctx["orders_confirmed"], 1)
        self.assertEqual(ctx["orders_fulfilled"], 1)
        self.assertEqual(ctx["pending_fulfillment_count"], 1)
        self.assertEqual(ctx["total_sales_revenue"], Decimal("24000.00"))
        self.assertEqual(ctx["fulfilled_revenue"], Decimal("8000.00"))
        self.assertEqual(ctx["active_products_count"], 1)

    def test_quote_print_view(self):
        self.client.login(email="salesdirector@enterpriseone.com", password="StrongPassword123!")
        session = self.client.session
        session["active_organization_id"] = str(self.org.id)
        session.save()

        quote = Quote.objects.create(
            organization=self.org,
            title="Enterprise Cloud Migration",
            account=self.account,
            status=QuoteStatus.PRESENTED,
            created_by=self.user,
            payment_terms="Net 45",
        )
        QuoteCalculationService.add_line_item(
            quote=quote, product=self.product, quantity=5, unit_price=Decimal("8000.00")
        )

        url = reverse("sales:quote_print", kwargs={"pk": quote.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "sales/quote_print.html")
        content = resp.content.decode("utf-8")
        self.assertIn(quote.quote_number, content)
        self.assertIn("Apex Horizon Systems", content)
        self.assertIn("QSB-9000", content)
        self.assertIn("Net 45", content)
        self.assertIn("Print / Export PDF", content)

    def test_order_print_view(self):
        self.client.login(email="salesdirector@enterpriseone.com", password="StrongPassword123!")
        session = self.client.session
        session["active_organization_id"] = str(self.org.id)
        session.save()

        order = SalesOrder.objects.create(
            organization=self.org,
            account=self.account,
            status=OrderStatus.PROCESSING,
            created_by=self.user,
            shipping_address="742 Evergreen Terrace, Sector 7G",
        )
        order.line_items.create(
            organization=self.org,
            product=self.product,
            line_number=1,
            quantity_ordered=4,
            quantity_fulfilled=2,
            unit_price=Decimal("8000.00"),
        )
        order.recalculate_totals()

        url = reverse("sales:order_print", kwargs={"pk": order.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "sales/order_print.html")
        content = resp.content.decode("utf-8")
        self.assertIn(order.order_number, content)
        self.assertIn("742 Evergreen Terrace", content)
        self.assertIn("QSB-9000", content)
        self.assertIn("Warehouse Dispatch / Operations", content)

    def test_multi_tenant_isolation_on_print_views(self):
        self.client.login(email="salesdirector@enterpriseone.com", password="StrongPassword123!")
        session = self.client.session
        session["active_organization_id"] = str(self.org.id)
        session.save()

        other_account = Account.objects.create(
            organization=self.other_org,
            name="Confidential Rival Corp",
            account_type=AccountType.CUSTOMER,
        )
        other_quote = Quote.objects.create(
            organization=self.other_org,
            title="Classified Project",
            account=other_account,
        )
        other_order = SalesOrder.objects.create(
            organization=self.other_org,
            account=other_account,
        )

        quote_resp = self.client.get(reverse("sales:quote_print", kwargs={"pk": other_quote.pk}))
        self.assertEqual(quote_resp.status_code, 404)

        order_resp = self.client.get(reverse("sales:order_print", kwargs={"pk": other_order.pk}))
        self.assertEqual(order_resp.status_code, 404)
