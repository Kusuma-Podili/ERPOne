"""
EnterpriseOne Sales Services.
Provides PricingEngineService, product catalog initialization, and multi-tier price calculations.
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from django.utils import timezone
from .models import (
    Product,
    ProductCategory,
    UnitOfMeasure,
    PriceBook,
    PriceBookEntry,
    TieredDiscount,
    Quote,
    QuoteLineItem,
    QuoteApproval,
    QuoteStatus,
)


@dataclass
class PriceResolutionResult:
    """Detailed price calculation breakdown for a product and quantity."""
    product_id: str
    product_name: str
    sku: str
    quantity: int
    base_unit_price: Decimal
    effective_unit_price: Decimal
    unit_discount: Decimal
    subtotal_amount: Decimal
    discount_amount: Decimal
    net_total_amount: Decimal
    price_book_id: Optional[str]
    price_book_name: str
    tier_discount_applied: bool
    tier_description: Optional[str]


class PricingEngineService:
    """
    High-performance pricing engine resolving contract, catalog, and tiered volume discounts.
    """

    @classmethod
    def resolve_price(
        cls,
        organization,
        product: Product,
        quantity: int = 1,
        price_book: Optional[PriceBook] = None,
    ) -> PriceResolutionResult:
        """
        Computes the effective unit price, applied volume discounts, and line totals.
        """
        if quantity < 1:
            quantity = 1

        active_price_book = price_book
        # 1. If no price book provided or it is expired, find organization's default price book
        if not active_price_book or not active_price_book.is_effective():
            active_price_book = PriceBook.objects.filter(
                organization=organization,
                is_default=True,
                is_active=True,
            ).first()

        entry: Optional[PriceBookEntry] = None
        base_unit_price = product.list_price
        price_book_name = "Product Base List Price"
        price_book_id = None

        # 2. Look up product in active price book
        if active_price_book:
            entry = PriceBookEntry.objects.filter(
                organization=organization,
                price_book=active_price_book,
                product=product,
                is_active=True,
                minimum_quantity__lte=quantity,
            ).first()

            if entry:
                base_unit_price = entry.unit_price
                price_book_name = active_price_book.name
                price_book_id = str(active_price_book.id)
            else:
                # If custom price book has no entry, check default price book if different
                if not active_price_book.is_default:
                    default_pb = PriceBook.objects.filter(
                        organization=organization,
                        is_default=True,
                        is_active=True,
                    ).first()
                    if default_pb:
                        entry = PriceBookEntry.objects.filter(
                            organization=organization,
                            price_book=default_pb,
                            product=product,
                            is_active=True,
                            minimum_quantity__lte=quantity,
                        ).first()
                        if entry:
                            base_unit_price = entry.unit_price
                            price_book_name = default_pb.name
                            price_book_id = str(default_pb.id)

        effective_unit_price = base_unit_price
        tier_applied = False
        tier_description = None

        # 3. Check for volume tiered discounts on the matched price book entry
        if entry:
            # Match tiered discounts where min_quantity <= quantity and (max is null or max >= quantity)
            tiered_discounts = entry.tiered_discounts.filter(
                is_active=True,
                min_quantity__lte=quantity,
            ).order_by("-min_quantity")

            for tier in tiered_discounts:
                if tier.max_quantity is None or tier.max_quantity >= quantity:
                    effective_unit_price = tier.calculate_effective_unit_price(base_unit_price)
                    tier_applied = True
                    tier_description = str(tier)
                    break

        unit_discount = max(Decimal("0.00"), base_unit_price - effective_unit_price)
        subtotal_amount = (base_unit_price * Decimal(quantity)).quantize(Decimal("0.01"))
        discount_amount = (unit_discount * Decimal(quantity)).quantize(Decimal("0.01"))
        net_total_amount = (effective_unit_price * Decimal(quantity)).quantize(Decimal("0.01"))

        return PriceResolutionResult(
            product_id=str(product.id),
            product_name=product.name,
            sku=product.sku,
            quantity=quantity,
            base_unit_price=base_unit_price,
            effective_unit_price=effective_unit_price,
            unit_discount=unit_discount,
            subtotal_amount=subtotal_amount,
            discount_amount=discount_amount,
            net_total_amount=net_total_amount,
            price_book_id=price_book_id,
            price_book_name=price_book_name,
            tier_discount_applied=tier_applied,
            tier_description=tier_description,
        )

    @classmethod
    def initialize_default_catalog(cls, organization, created_by=None) -> dict:
        """
        Seeds standard units of measure and a standard default price book.
        Idempotent operation.
        """
        standard_uoms = [
            ("Each / Unit", "EA", "unit", True, Decimal("1.0000")),
            ("Hour", "HR", "time", True, Decimal("1.0000")),
            ("Kilogram", "KG", "weight", True, Decimal("1.0000")),
            ("Meter", "M", "length", True, Decimal("1.0000")),
            ("Box (10 Units)", "BOX10", "unit", False, Decimal("10.0000")),
            ("Pack (5 Units)", "PK5", "unit", False, Decimal("5.0000")),
            ("Day (8 Hours)", "DAY8", "time", False, Decimal("8.0000")),
        ]

        created_uoms = []
        for name, code, category, is_base, ratio in standard_uoms:
            uom, _ = UnitOfMeasure.objects.get_or_create(
                organization=organization,
                code=code,
                defaults={
                    "name": name,
                    "category": category,
                    "is_base_unit": is_base,
                    "ratio_to_base": ratio,
                    "is_active": True,
                },
            )
            created_uoms.append(uom)

        # Standard Default Price Book
        default_pb, _ = PriceBook.objects.get_or_create(
            organization=organization,
            code="STANDARD",
            defaults={
                "name": "Standard Commercial Price Book",
                "description": "Standard corporate list price schedule.",
                "currency": "USD",
                "is_default": True,
                "is_active": True,
                "created_by": created_by,
            },
        )

        return {
            "uoms": created_uoms,
            "default_price_book": default_pb,
        }


class QuoteCalculationService:
    """
    Precision financial calculation service for commercial quotations and line items.
    """

    @classmethod
    def recalculate_quote(cls, quote: Quote) -> Quote:
        """
        Recalculates all line items, applies line discounts and taxes, and sums up quote totals.
        """
        subtotal = Decimal("0.00")
        discount_total = Decimal("0.00")
        tax_total = Decimal("0.00")
        requires_approval = False

        for line in quote.line_items.all():
            line.calculate_amounts()
            line.save(update_fields=[
                "subtotal",
                "discount_amount",
                "tax_amount",
                "total_price",
                "updated_at",
            ])
            subtotal += line.subtotal
            discount_total += line.discount_amount
            tax_total += line.tax_amount
            if line.discount_percent > QuoteApprovalService.APPROVAL_THRESHOLD_PERCENT:
                requires_approval = True

        quote.subtotal_amount = subtotal.quantize(Decimal("0.01"))
        quote.discount_amount = discount_total.quantize(Decimal("0.01"))
        quote.tax_amount = tax_total.quantize(Decimal("0.01"))
        quote.grand_total = (
            subtotal - discount_total + tax_total + quote.shipping_amount
        ).quantize(Decimal("0.01"))
        quote.requires_approval = requires_approval
        quote.save(update_fields=[
            "subtotal_amount",
            "discount_amount",
            "tax_amount",
            "grand_total",
            "requires_approval",
            "updated_at",
        ])
        return quote

    @classmethod
    def add_line_item(
        cls,
        quote: Quote,
        product: Product,
        quantity: int = 1,
        discount_percent: Decimal = Decimal("0.00"),
        tax_rate: Decimal = Decimal("0.00"),
        unit_price: Optional[Decimal] = None,
        description: str = "",
    ) -> QuoteLineItem:
        """
        Adds a product line to the quote, resolving the active unit price if not supplied.
        """
        if unit_price is None:
            res = PricingEngineService.resolve_price(
                organization=quote.organization,
                product=product,
                quantity=quantity,
                price_book=quote.price_book,
            )
            unit_price = res.effective_unit_price

        next_line_num = quote.line_items.count() + 1
        line = QuoteLineItem(
            organization=quote.organization,
            quote=quote,
            product=product,
            line_number=next_line_num,
            description=description or product.name,
            quantity=quantity,
            unit_price=unit_price,
            discount_percent=discount_percent,
            tax_rate=tax_rate,
        )
        line.calculate_amounts()
        line.save()
        cls.recalculate_quote(quote)
        return line


class QuoteApprovalService:
    """
    Enforces corporate discount approval policies and quotation lifecycle transitions.
    """
    APPROVAL_THRESHOLD_PERCENT = Decimal("15.00")

    @classmethod
    def check_approval_required(cls, quote: Quote) -> tuple[bool, Decimal]:
        """
        Returns True and the highest discount if any line item exceeds the approval threshold.
        """
        max_discount = Decimal("0.00")
        for line in quote.line_items.all():
            if line.discount_percent > max_discount:
                max_discount = line.discount_percent
        requires_approval = max_discount > cls.APPROVAL_THRESHOLD_PERCENT
        return requires_approval, max_discount

    @classmethod
    def submit_for_approval(cls, quote: Quote, requested_by) -> Quote:
        """
        Submits quotation for executive authorization.
        """
        if quote.status not in [QuoteStatus.DRAFT, QuoteStatus.REJECTED]:
            raise ValueError(f"Cannot submit quote in status '{quote.status}'. Must be Draft or Rejected.")

        requires_approval, max_discount = cls.check_approval_required(quote)
        if requires_approval:
            quote.status = QuoteStatus.PENDING_APPROVAL
            quote.requires_approval = True
            quote.save(update_fields=["status", "requires_approval", "updated_at"])
            QuoteApproval.objects.create(
                organization=quote.organization,
                quote=quote,
                requested_by=requested_by,
                discount_threshold_exceeded=max_discount,
                status="pending",
            )
        else:
            # Auto-approved if within acceptable discount limits
            quote.status = QuoteStatus.APPROVED
            quote.approved_by = requested_by
            quote.approved_at = timezone.now()
            quote.requires_approval = False
            quote.save(update_fields=["status", "approved_by", "approved_at", "requires_approval", "updated_at"])
        return quote

    @classmethod
    def approve_quote(cls, quote: Quote, approver, notes: str = "") -> Quote:
        """
        Approves a quotation pending review.
        """
        if quote.status != QuoteStatus.PENDING_APPROVAL:
            raise ValueError(f"Quote '{quote.quote_number}' is not pending approval.")

        now = timezone.now()
        pending_approvals = quote.approvals.filter(status="pending")
        for app in pending_approvals:
            app.status = "approved"
            app.approver = approver
            app.decided_at = now
            app.decision_notes = notes
            app.save()

        quote.status = QuoteStatus.APPROVED
        quote.approved_by = approver
        quote.approved_at = now
        quote.rejection_reason = ""
        quote.save(update_fields=["status", "approved_by", "approved_at", "rejection_reason", "updated_at"])
        return quote

    @classmethod
    def reject_quote(cls, quote: Quote, approver, reason: str = "") -> Quote:
        """
        Rejects quotation discount terms.
        """
        if quote.status != QuoteStatus.PENDING_APPROVAL:
            raise ValueError(f"Quote '{quote.quote_number}' is not pending approval.")

        now = timezone.now()
        pending_approvals = quote.approvals.filter(status="pending")
        for app in pending_approvals:
            app.status = "rejected"
            app.approver = approver
            app.decided_at = now
            app.decision_notes = reason
            app.save()

        quote.status = QuoteStatus.REJECTED
        quote.rejection_reason = reason
        quote.save(update_fields=["status", "rejection_reason", "updated_at"])
        return quote

    @classmethod
    def present_quote(cls, quote: Quote, user) -> Quote:
        """
        Marks quote as presented to the customer.
        """
        if quote.status not in [QuoteStatus.APPROVED, QuoteStatus.DRAFT]:
            raise ValueError(f"Cannot present quote with status '{quote.status}'. Must be Approved or Draft.")
        if quote.requires_approval and quote.status != QuoteStatus.APPROVED:
            raise ValueError("Quotation requires managerial approval before being presented to customer.")

        quote.status = QuoteStatus.PRESENTED
        quote.save(update_fields=["status", "updated_at"])
        return quote

    @classmethod
    def accept_quote(cls, quote: Quote, user) -> Quote:
        """
        Marks quotation as formally accepted by the customer.
        """
        if quote.status not in [QuoteStatus.PRESENTED, QuoteStatus.APPROVED]:
            raise ValueError(f"Cannot accept quote with status '{quote.status}'.")

        quote.status = QuoteStatus.ACCEPTED
        quote.save(update_fields=["status", "updated_at"])
        return quote

    @classmethod
    def decline_quote(cls, quote: Quote, user, reason: str = "") -> Quote:
        """
        Marks quotation as declined by customer.
        """
        if quote.status != QuoteStatus.PRESENTED:
            raise ValueError("Only presented quotes can be declined by customer.")

        quote.status = QuoteStatus.REJECTED
        quote.rejection_reason = reason
        quote.save(update_fields=["status", "rejection_reason", "updated_at"])
        return quote

