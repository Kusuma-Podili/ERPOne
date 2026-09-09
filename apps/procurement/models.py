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


class RFQStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    PUBLISHED = "published", _("Published / Open for Bids")
    CLOSED = "closed", _("Closed / Bidding Ended")
    AWARDED = "awarded", _("Awarded")
    CANCELLED = "cancelled", _("Cancelled")


class RequestForQuotation(models.Model):
    """
    Commercial Request for Quotation (RFQ) inviting competitive supplier bids for specified items.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="rfqs",
    )
    rfq_number = models.CharField(_("RFQ Number"), max_length=50, db_index=True)
    title = models.CharField(_("Title / Scope"), max_length=255)
    status = models.CharField(
        _("Status"),
        max_length=30,
        choices=RFQStatus.choices,
        default=RFQStatus.DRAFT,
        db_index=True,
    )
    submission_deadline = models.DateTimeField(_("Bid Submission Deadline"))
    delivery_deadline = models.DateField(_("Target Delivery Date"), null=True, blank=True)
    notes = models.TextField(_("Procurement Scope & Terms"), blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_rfqs",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Request for Quotation")
        verbose_name_plural = _("Requests for Quotation")
        ordering = ["-created_at"]
        unique_together = ("organization", "rfq_number")

    def __str__(self):
        return f"{self.rfq_number} — {self.title}"

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.submission_deadline

    @property
    def can_submit_bids(self) -> bool:
        return self.status == RFQStatus.PUBLISHED and not self.is_expired

    @property
    def total_lines_count(self) -> int:
        return self.lines.count()

    @property
    def total_bids_count(self) -> int:
        return self.bids.count()

    @property
    def winning_bid(self):
        return self.bids.filter(is_winning_bid=True).first()

    @classmethod
    def generate_rfq_number(cls, organization) -> str:
        current_year = timezone.now().year
        prefix = f"RFQ-{current_year}-"
        last_rfq = cls.objects.filter(
            organization=organization,
            rfq_number__startswith=prefix,
        ).order_by("-rfq_number").first()

        if last_rfq:
            try:
                seq_str = last_rfq.rfq_number.split("-")[-1]
                next_seq = int(seq_str) + 1
            except (ValueError, IndexError):
                next_seq = 1
        else:
            next_seq = 1

        return f"{prefix}{next_seq:05d}"


class RFQLine(models.Model):
    """
    Specific item, quantity, UOM, and specifications requested within an RFQ.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rfq = models.ForeignKey(
        RequestForQuotation,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    line_number = models.PositiveIntegerField(_("Line No."), default=1)
    product = models.ForeignKey(
        "sales.Product",
        on_delete=models.CASCADE,
        related_name="rfq_lines",
    )
    target_quantity = models.DecimalField(_("Target Quantity"), max_digits=12, decimal_places=2)
    uom = models.ForeignKey(
        "sales.UnitOfMeasure",
        on_delete=models.PROTECT,
        related_name="rfq_lines",
    )
    target_delivery_date = models.DateField(_("Target Delivery Date"), null=True, blank=True)
    specifications = models.TextField(_("Technical Specifications / Scope"), blank=True)

    class Meta:
        verbose_name = _("RFQ Line")
        verbose_name_plural = _("RFQ Lines")
        ordering = ["line_number"]
        unique_together = ("rfq", "line_number")

    def __str__(self):
        return f"{self.rfq.rfq_number} Line {self.line_number}: {self.product.name} ({self.target_quantity} {self.uom.code})"


class RFQVendorInvitation(models.Model):
    """
    Tracks invited vendor participation in a competitive bidding event.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rfq = models.ForeignKey(
        RequestForQuotation,
        on_delete=models.CASCADE,
        related_name="invitations",
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE,
        related_name="rfq_invitations",
    )
    invitation_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    invited_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("RFQ Vendor Invitation")
        verbose_name_plural = _("RFQ Vendor Invitations")
        ordering = ["-invited_at"]
        unique_together = ("rfq", "supplier")

    def __str__(self):
        return f"{self.supplier.name} invited to {self.rfq.rfq_number}"


class VendorBid(models.Model):
    """
    Formal commercial proposal submitted by a vendor responding to an RFQ.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rfq = models.ForeignKey(
        RequestForQuotation,
        on_delete=models.CASCADE,
        related_name="bids",
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE,
        related_name="submitted_bids",
    )
    bid_reference = models.CharField(_("Vendor Quote / Reference #"), max_length=100)
    submission_date = models.DateTimeField(default=timezone.now)
    valid_until = models.DateField(_("Proposal Validity Date"))
    payment_terms = models.CharField(
        _("Payment Terms"),
        max_length=30,
        choices=PaymentTerms.choices,
        default=PaymentTerms.NET30,
    )
    lead_time_days = models.PositiveIntegerField(_("Delivery Lead Time (Days)"), default=7)
    shipping_cost = models.DecimalField(
        _("Freight / Shipping Cost"),
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    currency = models.CharField(_("Currency"), max_length=3, default="USD")
    is_winning_bid = models.BooleanField(_("Awarded Winning Bid"), default=False)
    award_reason = models.TextField(_("Award Justification / Evaluation"), blank=True)
    awarded_at = models.DateTimeField(null=True, blank=True)
    awarded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="awarded_bids",
    )
    notes = models.TextField(_("Vendor Remarks & Assumptions"), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Vendor Bid")
        verbose_name_plural = _("Vendor Bids")
        ordering = ["-submission_date"]
        unique_together = ("rfq", "supplier")

    def __str__(self):
        status_tag = " [WINNER]" if self.is_winning_bid else ""
        return f"Bid by {self.supplier.name} for {self.rfq.rfq_number}: ${self.total_amount}{status_tag}"

    @property
    def lines_subtotal(self) -> Decimal:
        return sum((line.line_total for line in self.lines.all()), Decimal("0.00"))

    @property
    def total_amount(self) -> Decimal:
        return self.lines_subtotal + self.shipping_cost


class VendorBidLine(models.Model):
    """
    Priced line item submitted by a vendor corresponding to an RFQ line.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bid = models.ForeignKey(
        VendorBid,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    rfq_line = models.ForeignKey(
        RFQLine,
        on_delete=models.CASCADE,
        related_name="vendor_bid_lines",
    )
    offered_unit_price = models.DecimalField(
        _("Offered Unit Price"),
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    offered_quantity = models.DecimalField(
        _("Offered Quantity"),
        max_digits=12,
        decimal_places=2,
    )
    lead_time_days = models.PositiveIntegerField(_("Lead Time (Days)"), default=7)
    notes = models.CharField(_("Vendor Line Remarks"), max_length=255, blank=True)

    class Meta:
        verbose_name = _("Vendor Bid Line")
        verbose_name_plural = _("Vendor Bid Lines")
        unique_together = ("bid", "rfq_line")

    def __str__(self):
        return f"{self.bid.supplier.code}: {self.rfq_line.product.name} @ ${self.offered_unit_price}"

    @property
    def line_total(self) -> Decimal:
        return self.offered_unit_price * self.offered_quantity
