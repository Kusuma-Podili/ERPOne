"""
EnterpriseOne Integration Tests — Sales Order Lifecycle & Fulfillment (Milestone 4.3).
Validates quote conversion, state machine transition governance, line item fulfillment, and audit logging.
"""
from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from apps.accounts.models import User
from apps.organizations.models import Organization
from apps.crm.models import Account, AccountType
from apps.sales.models import (
    Product,
    UnitOfMeasure,
    Quote,
    QuoteStatus,
    SalesOrder,
    OrderStatus,
)
from apps.sales.services import (
    QuoteCalculationService,
    QuoteApprovalService,
    QuoteToOrderConversionService,
    OrderStateMachineService,
)


class OrderLifecycleTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="salesops@enterpriseone.com",
            password="StrongPassword123!",
            first_name="Olivia",
            last_name="Ops",
        )
        self.org = Organization.objects.create(
            name="Apex Dynamics Corp",
            code="APEXDYN",
            slug="apex-dynamics",
            currency="USD",
        )
        self.account = Account.objects.create(
            organization=self.org,
            name="Quantum Computing Lab",
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
        self.product1 = Product.objects.create(
            organization=self.org,
            name="Quantum Cryogenic Sensor",
            sku="QCS-001",
            uom=self.uom,
            cost_price=Decimal("1500.00"),
            list_price=Decimal("3000.00"),
        )
        self.product2 = Product.objects.create(
            organization=self.org,
            name="High-Purity Fiber Cable",
            sku="HPF-500",
            uom=self.uom,
            cost_price=Decimal("50.00"),
            list_price=Decimal("120.00"),
        )

    def test_quote_to_order_conversion(self):
        """Converts an accepted quote to a confirmed sales order atomically."""
        quote = Quote.objects.create(
            organization=self.org,
            title="Quantum Lab Equipment",
            account=self.account,
            created_by=self.user,
            shipping_amount=Decimal("150.00"),
        )
        QuoteCalculationService.add_line_item(
            quote=quote,
            product=self.product1,
            quantity=2,
            unit_price=Decimal("3000.00"),
            discount_percent=Decimal("5.00"),
        )
        QuoteCalculationService.add_line_item(
            quote=quote,
            product=self.product2,
            quantity=10,
            unit_price=Decimal("120.00"),
        )

        # Advance to accepted
        QuoteApprovalService.submit_for_approval(quote, self.user)
        QuoteApprovalService.present_quote(quote, self.user)
        QuoteApprovalService.accept_quote(quote, self.user)
        quote.refresh_from_db()
        self.assertEqual(quote.status, QuoteStatus.ACCEPTED)

        # Convert to order
        order = QuoteToOrderConversionService.convert_quote_to_order(
            quote=quote,
            user=self.user,
            shipping_address="100 Tech Parkway, Suite 400, Cambridge, MA",
            billing_address="100 Tech Parkway, Suite 400, Cambridge, MA",
        )

        # Verify quote state
        quote.refresh_from_db()
        self.assertEqual(quote.status, QuoteStatus.CONVERTED)

        # Verify sales order
        self.assertIsNotNone(order.order_number)
        self.assertTrue(order.order_number.startswith("SO-"))
        self.assertEqual(order.status, OrderStatus.CONFIRMED)
        self.assertEqual(order.quote, quote)
        self.assertEqual(order.account, self.account)
        self.assertEqual(order.subtotal_amount, quote.subtotal_amount)
        self.assertEqual(order.discount_amount, quote.discount_amount)
        self.assertEqual(order.shipping_amount, Decimal("150.00"))
        self.assertEqual(order.grand_total, quote.grand_total)

        # Verify line items
        self.assertEqual(order.line_items.count(), 2)
        line1 = order.line_items.get(product=self.product1)
        self.assertEqual(line1.quantity_ordered, 2)
        self.assertEqual(line1.quantity_fulfilled, 0)
        self.assertEqual(line1.unit_price, Decimal("3000.00"))

        line2 = order.line_items.get(product=self.product2)
        self.assertEqual(line2.quantity_ordered, 10)
        self.assertEqual(line2.quantity_fulfilled, 0)

        # Verify audit history
        self.assertEqual(order.status_history.count(), 1)
        history = order.status_history.first()
        self.assertEqual(history.to_status, OrderStatus.CONFIRMED)
        self.assertIn("quote conversion", history.notes)

    def test_unaccepted_quote_cannot_be_converted(self):
        """Draft or unapproved quotes cannot be converted to orders."""
        quote = Quote.objects.create(
            organization=self.org,
            title="Draft Lab Inquiry",
            account=self.account,
            created_by=self.user,
        )
        QuoteCalculationService.add_line_item(
            quote=quote,
            product=self.product1,
            quantity=1,
            unit_price=Decimal("3000.00"),
        )
        with self.assertRaises(ValidationError) as ctx:
            QuoteToOrderConversionService.convert_quote_to_order(quote, self.user)
        self.assertIn("cannot be converted", str(ctx.exception))

    def test_order_state_machine_transitions(self):
        """Order traverses valid state machine lifecycle with audit history."""
        order = SalesOrder.objects.create(
            organization=self.org,
            account=self.account,
            created_by=self.user,
            status=OrderStatus.DRAFT,
        )

        # DRAFT -> CONFIRMED
        OrderStateMachineService.transition_order(
            order, OrderStatus.CONFIRMED, self.user, notes="Customer purchase order received."
        )
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.CONFIRMED)

        # CONFIRMED -> PROCESSING
        OrderStateMachineService.transition_order(
            order, OrderStatus.PROCESSING, self.user, notes="Sent to warehouse for picking."
        )
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.PROCESSING)

        # Audit check
        histories = order.status_history.order_by("timestamp")
        self.assertEqual(histories.count(), 2)
        self.assertEqual(histories[0].from_status, OrderStatus.DRAFT)
        self.assertEqual(histories[0].to_status, OrderStatus.CONFIRMED)
        self.assertEqual(histories[1].from_status, OrderStatus.CONFIRMED)
        self.assertEqual(histories[1].to_status, OrderStatus.PROCESSING)

    def test_order_state_machine_invalid_transition(self):
        """Illegal jumps between states are rejected with ValidationError."""
        order = SalesOrder.objects.create(
            organization=self.org,
            account=self.account,
            created_by=self.user,
            status=OrderStatus.DRAFT,
        )

        # Cannot jump DRAFT -> FULFILLED directly
        with self.assertRaises(ValidationError) as ctx:
            OrderStateMachineService.transition_order(order, OrderStatus.FULFILLED, self.user)
        self.assertIn("Illegal state transition", str(ctx.exception))

    def test_line_fulfillment_lifecycle(self):
        """Line item fulfillment updates item quantities and triggers order status progression."""
        order = SalesOrder.objects.create(
            organization=self.org,
            account=self.account,
            created_by=self.user,
            status=OrderStatus.CONFIRMED,
        )
        line = order.line_items.create(
            organization=self.org,
            product=self.product1,
            line_number=1,
            quantity_ordered=10,
            quantity_fulfilled=0,
            unit_price=Decimal("3000.00"),
        )
        order.recalculate_totals()

        # Partial fulfillment: ship 4 out of 10
        OrderStateMachineService.fulfill_line_item(line, 4, self.user)
        line.refresh_from_db()
        order.refresh_from_db()

        self.assertEqual(line.quantity_fulfilled, 4)
        self.assertEqual(line.remaining_quantity, 6)
        self.assertFalse(line.is_fulfilled)
        self.assertEqual(order.fulfillment_percentage, 40)
        self.assertEqual(order.status, OrderStatus.PARTIALLY_FULFILLED)

        # Overfulfillment attempt should fail
        with self.assertRaises(ValidationError) as ctx:
            OrderStateMachineService.fulfill_line_item(line, 7, self.user)
        self.assertIn("exceeds remaining", str(ctx.exception))

        # Complete fulfillment: ship remaining 6
        OrderStateMachineService.fulfill_line_item(line, 6, self.user)
        line.refresh_from_db()
        order.refresh_from_db()

        self.assertEqual(line.quantity_fulfilled, 10)
        self.assertEqual(line.remaining_quantity, 0)
        self.assertTrue(line.is_fulfilled)
        self.assertEqual(order.fulfillment_percentage, 100)
        self.assertEqual(order.status, OrderStatus.FULFILLED)

    def test_cancellation_rules(self):
        """Orders can be cancelled before fulfillment, but not after completion."""
        order = SalesOrder.objects.create(
            organization=self.org,
            account=self.account,
            created_by=self.user,
            status=OrderStatus.CONFIRMED,
        )
        OrderStateMachineService.transition_order(
            order, OrderStatus.CANCELLED, self.user, notes="Customer withdrew PO."
        )
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.CANCELLED)

        # Completed orders cannot be cancelled
        fulfilled_order = SalesOrder.objects.create(
            organization=self.org,
            account=self.account,
            created_by=self.user,
            status=OrderStatus.FULFILLED,
        )
        with self.assertRaises(ValidationError):
            OrderStateMachineService.transition_order(
                fulfilled_order, OrderStatus.CANCELLED, self.user
            )

