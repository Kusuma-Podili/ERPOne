"""
EnterpriseOne Procurement & Supplier Domain Models (Milestone 6.1).
Defines Vendor/Supplier profiles, contact persons, and product supplier pricing catalogs.
"""
import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class SupplierType(models.TextChoices):
    MANUFACTURER = "manufacturer", _("Manufacturer / OEM")
    DISTRIBUTOR = "distributor", _("Authorized Distributor")
    WHOLESALER = "wholesaler", _("Wholesaler")
    SERVICE_PROVIDER = "service", _("Service Provider / Contractor")
    RAW_MATERIALS = "raw_materials", _("Raw Materials Supplier")


class PaymentTerms(models.TextChoices):
    IMMEDIATE = "immediate", _("Immediate / Due on Receipt")
    NET15 = "net15", _("Net 15 Days")
    NET30 = "net30", _("Net 30 Days")
    NET45 = "net45", _("Net 45 Days")
    NET60 = "net60", _("Net 60 Days")
    NET90 = "net90", _("Net 90 Days")


class SupplierStatus(models.TextChoices):
    ACTIVE = "active", _("Active")
    PENDING_REVIEW = "pending_review", _("Pending Compliance Review")
    ON_HOLD = "on_hold", _("On Hold / Suspended")
    DISQUALIFIED = "disqualified", _("Disqualified")


class Supplier(models.Model):
    """
    Master vendor profile governing commercial sourcing agreements, payment credit, and performance scorecards.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="suppliers",
    )
    name = models.CharField(_("Supplier Legal Name"), max_length=200)
    code = models.CharField(_("Supplier Code"), max_length=50, db_index=True)
    supplier_type = models.CharField(
        _("Supplier Type"),
        max_length=30,
        choices=SupplierType.choices,
        default=SupplierType.DISTRIBUTOR,
    )
    status = models.CharField(
        _("Status"),
        max_length=30,
        choices=SupplierStatus.choices,
        default=SupplierStatus.ACTIVE,
    )
    payment_terms = models.CharField(
        _("Payment Terms"),
        max_length=30,
        choices=PaymentTerms.choices,
        default=PaymentTerms.NET30,
    )
    currency = models.CharField(_("Default Currency"), max_length=3, default="USD")
    tax_id = models.CharField(_("Tax ID / EIN / VAT"), max_length=50, blank=True)
    email = models.EmailField(_("Primary Contact Email"), blank=True)
    phone = models.CharField(_("Telephone"), max_length=50, blank=True)
    website = models.URLField(_("Corporate Website"), blank=True)
    address = models.TextField(_("Street Address"), blank=True)
    city = models.CharField(_("City"), max_length=100, blank=True)
    state_province = models.CharField(_("State / Province"), max_length=100, blank=True)
    postal_code = models.CharField(_("Postal Code"), max_length=20, blank=True)
    country = models.CharField(_("Country"), max_length=100, default="USA", blank=True)
    lead_time_rating = models.DecimalField(
        _("Lead Time Rating (1-5)"),
        max_digits=3,
        decimal_places=1,
        default=Decimal("5.0"),
    )
    quality_rating = models.DecimalField(
        _("Quality Rating (1-5)"),
        max_digits=3,
        decimal_places=1,
        default=Decimal("5.0"),
    )
    notes = models.TextField(_("Notes & Compliance Requirements"), blank=True)
    is_active = models.BooleanField(_("Active"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Supplier")
        verbose_name_plural = _("Suppliers")
        ordering = ["name"]
        unique_together = ("organization", "code")

    def __str__(self):
        return f"{self.name} ({self.code})"

    @property
    def total_products_count(self) -> int:
        return self.supplied_products.count()

    @property
    def overall_rating(self) -> Decimal:
        return (self.lead_time_rating + self.quality_rating) / Decimal("2.0")


class SupplierContact(models.Model):
    """
    Direct vendor account representative or procurement liaison.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE,
        related_name="contacts",
    )
    name = models.CharField(_("Contact Person Name"), max_length=150)
    title = models.CharField(_("Job Title"), max_length=100, blank=True)
    email = models.EmailField(_("Email Address"))
    phone = models.CharField(_("Direct Phone"), max_length=50, blank=True)
    is_primary = models.BooleanField(_("Primary Contact"), default=False)
    notes = models.CharField(_("Notes"), max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Supplier Contact")
        verbose_name_plural = _("Supplier Contacts")
        ordering = ["-is_primary", "name"]

    def __str__(self):
        return f"{self.name} ({self.supplier.name})"


class SupplierProduct(models.Model):
    """
    Supplier catalog pricing entry linking vendor part numbers, cost prices, MOQs, and lead times.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="supplier_products",
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE,
        related_name="supplied_products",
    )
    product = models.ForeignKey(
        "sales.Product",
        on_delete=models.CASCADE,
        related_name="supplier_offerings",
    )
    supplier_sku = models.CharField(_("Vendor SKU / Part Number"), max_length=100, blank=True)
    unit_price = models.DecimalField(
        _("Supplier Unit Price"),
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    currency = models.CharField(_("Currency"), max_length=3, default="USD")
    minimum_order_quantity = models.DecimalField(
        _("Minimum Order Quantity (MOQ)"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("1.00"),
    )
    lead_time_days = models.PositiveIntegerField(
        _("Delivery Lead Time (Days)"),
        default=7,
    )
    is_preferred = models.BooleanField(
        _("Preferred Supplier"),
        default=False,
        help_text=_("Designates default vendor for automatic purchase requisition conversion."),
    )
    is_active = models.BooleanField(_("Active Offering"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Supplier Product Offering")
        verbose_name_plural = _("Supplier Product Offerings")
        ordering = ["product__name", "unit_price"]
        unique_together = ("supplier", "product")

    def __str__(self):
        pref_str = " [Preferred]" if self.is_preferred else ""
        return f"{self.supplier.code}: {self.product.name} @ ${self.unit_price}{pref_str}"

    def clean(self):
        super().clean()
        if self.unit_price < Decimal("0.00"):
            raise ValidationError({"unit_price": _("Unit price cannot be negative.")})
        if self.minimum_order_quantity <= Decimal("0.00"):
            raise ValidationError({"minimum_order_quantity": _("MOQ must be greater than zero.")})
