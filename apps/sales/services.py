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
