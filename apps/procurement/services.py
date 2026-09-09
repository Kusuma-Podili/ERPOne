"""
EnterpriseOne Procurement & Supplier Domain Services (Milestone 6.1).
Provides vendor lifecycle management, preferred vendor sourcing resolution, and supplier performance tracking.
"""
from decimal import Decimal
from typing import Optional, List, Dict
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.organizations.models import Organization
from apps.sales.models import Product
from .models import (
    Supplier,
    SupplierType,
    PaymentTerms,
    SupplierStatus,
    SupplierContact,
    SupplierProduct,
)


class SupplierService:
    """
    Governs supplier registration, commercial catalog relationships, and optimal sourcing resolutions.
    """

    @classmethod
    def create_supplier(
        cls,
        organization: Organization,
        name: str,
        code: str,
        supplier_type: str = SupplierType.DISTRIBUTOR,
        payment_terms: str = PaymentTerms.NET30,
        currency: str = "USD",
        tax_id: str = "",
        email: str = "",
        phone: str = "",
        website: str = "",
        address: str = "",
        city: str = "",
        state_province: str = "",
        postal_code: str = "",
        country: str = "USA",
        lead_time_rating: Decimal = Decimal("5.0"),
        quality_rating: Decimal = Decimal("5.0"),
        notes: str = "",
    ) -> Supplier:
        """
        Creates and registers an enterprise supplier master record.
        """
        supplier = Supplier(
            organization=organization,
            name=name.strip(),
            code=code.strip().upper(),
            supplier_type=supplier_type,
            payment_terms=payment_terms,
            currency=currency,
            tax_id=tax_id.strip(),
            email=email.strip(),
            phone=phone.strip(),
            website=website.strip(),
            address=address.strip(),
            city=city.strip(),
            state_province=state_province.strip(),
            postal_code=postal_code.strip(),
            country=country.strip(),
            lead_time_rating=lead_time_rating,
            quality_rating=quality_rating,
            notes=notes.strip(),
        )
        supplier.full_clean()
        supplier.save()
        return supplier

    @classmethod
    def add_contact(
        cls,
        supplier: Supplier,
        name: str,
        email: str,
        title: str = "",
        phone: str = "",
        is_primary: bool = False,
        notes: str = "",
    ) -> SupplierContact:
        """
        Attaches a liaison contact person to a supplier profile.
        """
        if is_primary:
            # Set other contacts to non-primary
            supplier.contacts.filter(is_primary=True).update(is_primary=False)

        contact = SupplierContact(
            supplier=supplier,
            name=name.strip(),
            email=email.strip(),
            title=title.strip(),
            phone=phone.strip(),
            is_primary=is_primary,
            notes=notes.strip(),
        )
        contact.full_clean()
        contact.save()
        return contact

    @classmethod
    @transaction.atomic
    def link_product(
        cls,
        supplier: Supplier,
        product: Product,
        unit_price: Decimal,
        supplier_sku: str = "",
        currency: str = "USD",
        minimum_order_quantity: Decimal = Decimal("1.00"),
        lead_time_days: int = 7,
        is_preferred: bool = False,
    ) -> SupplierProduct:
        """
        Registers or updates a vendor catalog offering for a product SKU.
        """
        if is_preferred:
            # Demote existing preferred supplier offerings for this product in the same organization
            SupplierProduct.objects.filter(
                organization=supplier.organization,
                product=product,
                is_preferred=True,
            ).exclude(supplier=supplier).update(is_preferred=False)

        offering, created = SupplierProduct.objects.update_or_create(
            organization=supplier.organization,
            supplier=supplier,
            product=product,
            defaults={
                "supplier_sku": supplier_sku.strip(),
                "unit_price": unit_price,
                "currency": currency,
                "minimum_order_quantity": minimum_order_quantity,
                "lead_time_days": lead_time_days,
                "is_preferred": is_preferred,
                "is_active": True,
            },
        )
        return offering

    @classmethod
    def get_preferred_supplier_offering(
        cls,
        product: Product,
    ) -> Optional[SupplierProduct]:
        """
        Resolves the optimal supplier offering for a product:
        1. Checks for explicitly designated preferred supplier offering
        2. Falls back to active supplier offering with lowest unit price
        """
        offerings = SupplierProduct.objects.filter(
            product=product,
            is_active=True,
            supplier__is_active=True,
            supplier__status=SupplierStatus.ACTIVE,
        ).select_related("supplier")

        preferred = offerings.filter(is_preferred=True).first()
        if preferred:
            return preferred

        return offerings.order_by("unit_price").first()
