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
    currency = models.CharField(_("Default Currency"), max_length=3, default="INR")
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
    currency = models.CharField(_("Currency"), max_length=3, default="INR")
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
    currency = models.CharField(_("Currency"), max_length=3, default="INR")
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


class POStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    PENDING_APPROVAL = "pending_approval", _("Pending Approval Gate")
    APPROVED = "approved", _("Approved / Authorized")
    REJECTED = "rejected", _("Rejected")
    ISSUED = "issued", _("Issued to Vendor")
    PARTIALLY_RECEIVED = "partially_received", _("Partially Received")
    COMPLETED = "completed", _("Completed / Fully Received")
    CANCELLED = "cancelled", _("Cancelled")


class ApprovalTier(models.IntegerChoices):
    TIER_1_MANAGER = 1, _("Tier 1: Department Manager (Up to $10,000)")
    TIER_2_DIRECTOR = 2, _("Tier 2: Procurement Director (Up to $50,000)")
    TIER_3_EXECUTIVE = 3, _("Tier 3: CFO / Executive Board (Over $50,000)")


class PurchaseOrder(models.Model):
    """
    Legally binding commercial Purchase Order (PO) issued to a vendor.
    Governs delivery commitments, unit pricing, tax rates, and multi-tier financial approval gates.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="purchase_orders",
    )
    po_number = models.CharField(_("PO Number"), max_length=50, db_index=True)
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name="purchase_orders",
    )
    rfq = models.ForeignKey(
        RequestForQuotation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_pos",
    )
    status = models.CharField(
        _("Status"),
        max_length=30,
        choices=POStatus.choices,
        default=POStatus.DRAFT,
        db_index=True,
    )
    order_date = models.DateField(_("Order Date"), default=timezone.now)
    expected_delivery_date = models.DateField(_("Expected Delivery Date"), null=True, blank=True)
    payment_terms = models.CharField(
        _("Payment Terms"),
        max_length=30,
        choices=PaymentTerms.choices,
        default=PaymentTerms.NET30,
    )
    currency = models.CharField(_("Currency"), max_length=3, default="INR")
    subtotal = models.DecimalField(
        _("Line Items Subtotal"),
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    tax_amount = models.DecimalField(
        _("Tax Amount"),
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    shipping_cost = models.DecimalField(
        _("Shipping / Freight"),
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    total_amount = models.DecimalField(
        _("Total Commercial Value"),
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    shipping_address = models.TextField(_("Destination Warehouse / Delivery Address"), blank=True)
    billing_address = models.TextField(_("Billing Address"), blank=True)
    notes = models.TextField(_("Special Instructions & Commercial Terms"), blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_pos",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_pos",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    issued_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Purchase Order")
        verbose_name_plural = _("Purchase Orders")
        ordering = ["-created_at"]
        unique_together = ("organization", "po_number")

    def __str__(self):
        return f"{self.po_number} — {self.supplier.name} (${self.total_amount})"

    @classmethod
    def generate_po_number(cls, organization) -> str:
        current_year = timezone.now().year
        prefix = f"PO-{current_year}-"
        last_po = cls.objects.filter(
            organization=organization,
            po_number__startswith=prefix,
        ).order_by("-po_number").first()

        if last_po:
            try:
                seq_str = last_po.po_number.split("-")[-1]
                next_seq = int(seq_str) + 1
            except (ValueError, IndexError):
                next_seq = 1
        else:
            next_seq = 1

        return f"{prefix}{next_seq:05d}"

    @property
    def total_lines_count(self) -> int:
        return self.lines.count()

    @property
    def can_submit_for_approval(self) -> bool:
        return self.status == POStatus.DRAFT and self.lines.exists()

    @property
    def can_approve(self) -> bool:
        return self.status == POStatus.PENDING_APPROVAL

    @property
    def can_issue(self) -> bool:
        return self.status == POStatus.APPROVED

    @property
    def can_receive(self) -> bool:
        return self.status in (POStatus.ISSUED, POStatus.PARTIALLY_RECEIVED)

    def recalculate_totals(self):
        """
        Recalculates subtotal, tax_amount, and total_amount across all lines.
        """
        sub = Decimal("0.00")
        tax = Decimal("0.00")
        for line in self.lines.all():
            sub += line.line_subtotal
            tax += line.line_tax
        self.subtotal = sub
        self.tax_amount = tax
        self.total_amount = sub + tax + self.shipping_cost
        self.save(update_fields=["subtotal", "tax_amount", "total_amount", "updated_at"])


class PurchaseOrderLine(models.Model):
    """
    Individual product line committed on a purchase order.
    Tracks ordered, received, and billed quantities for 3-way matching.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    line_number = models.PositiveIntegerField(_("Line No."), default=1)
    product = models.ForeignKey(
        "sales.Product",
        on_delete=models.PROTECT,
        related_name="po_lines",
    )
    ordered_quantity = models.DecimalField(_("Ordered Quantity"), max_digits=12, decimal_places=2)
    received_quantity = models.DecimalField(_("Received Quantity"), max_digits=12, decimal_places=2, default=Decimal("0.00"))
    billed_quantity = models.DecimalField(_("Billed Quantity"), max_digits=12, decimal_places=2, default=Decimal("0.00"))
    uom = models.ForeignKey(
        "sales.UnitOfMeasure",
        on_delete=models.PROTECT,
        related_name="po_lines",
    )
    unit_price = models.DecimalField(_("Unit Price"), max_digits=14, decimal_places=2)
    tax_rate = models.DecimalField(_("Tax Rate (%)"), max_digits=5, decimal_places=2, default=Decimal("0.00"))
    line_subtotal = models.DecimalField(_("Subtotal"), max_digits=14, decimal_places=2, default=Decimal("0.00"))
    line_tax = models.DecimalField(_("Tax"), max_digits=14, decimal_places=2, default=Decimal("0.00"))
    line_total = models.DecimalField(_("Line Total"), max_digits=14, decimal_places=2, default=Decimal("0.00"))
    notes = models.CharField(_("Line Notes"), max_length=255, blank=True)

    class Meta:
        verbose_name = _("Purchase Order Line")
        verbose_name_plural = _("Purchase Order Lines")
        ordering = ["line_number"]
        unique_together = ("purchase_order", "line_number")

    def __str__(self):
        return f"{self.purchase_order.po_number} #{self.line_number}: {self.product.name} ({self.ordered_quantity} {self.uom.code})"

    @property
    def pending_quantity(self) -> Decimal:
        return max(Decimal("0.00"), self.ordered_quantity - self.received_quantity)

    @property
    def is_fully_received(self) -> bool:
        return self.received_quantity >= self.ordered_quantity

    def save(self, *args, **kwargs):
        self.line_subtotal = self.ordered_quantity * self.unit_price
        self.line_tax = self.line_subtotal * (self.tax_rate / Decimal("100.00"))
        self.line_total = self.line_subtotal + self.line_tax
        super().save(*args, **kwargs)


class PurchaseOrderApproval(models.Model):
    """
    Audit log of financial approval gates traversed for high-value purchase orders.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name="approvals",
    )
    tier = models.IntegerField(_("Approval Tier"), choices=ApprovalTier.choices, default=ApprovalTier.TIER_1_MANAGER)
    threshold_amount = models.DecimalField(_("Threshold Amount"), max_digits=14, decimal_places=2)
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="po_approval_decisions",
    )
    status = models.CharField(_("Approval Status"), max_length=20, default="pending")
    comments = models.TextField(_("Comments / Justification"), blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("PO Approval Gate")
        verbose_name_plural = _("PO Approval Gates")
        ordering = ["tier"]

    def __str__(self):
        return f"{self.purchase_order.po_number} - Tier {self.tier}: {self.status}"


class BillStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    PENDING_MATCH = "pending_match", _("Pending 3-Way Match")
    MATCHED = "matched", _("Matched & Approved for Payment")
    DISPUTED = "disputed", _("Disputed / Variance Flagged")
    PAID = "paid", _("Paid")
    CANCELLED = "cancelled", _("Cancelled")


class MatchStatus(models.TextChoices):
    MATCHED = "matched", _("Perfect 3-Way Match")
    TOLERANCE_ACCEPTED = "tolerance_accepted", _("Within Commercial Tolerance")
    PRICE_VARIANCE = "price_variance", _("Price Variance Flagged")
    QUANTITY_VARIANCE = "quantity_variance", _("Quantity Variance Flagged")
    DISPUTED = "disputed", _("Disputed")
    RESOLVED = "resolved", _("Resolved / Authorized Override")


class VendorBill(models.Model):
    """
    Vendor invoice/bill record submitted for commercial payment against received goods.
    Subject to automated 3-Way Matching against Purchase Order commitments and Goods Receipts.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="vendor_bills",
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name="bills",
    )
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bills",
    )
    bill_number = models.CharField(_("Vendor Invoice / Bill #"), max_length=100, db_index=True)
    status = models.CharField(
        _("Status"),
        max_length=30,
        choices=BillStatus.choices,
        default=BillStatus.DRAFT,
        db_index=True,
    )
    match_status = models.CharField(
        _("3-Way Match Status"),
        max_length=30,
        choices=MatchStatus.choices,
        default=MatchStatus.MATCHED,
        db_index=True,
    )
    bill_date = models.DateField(_("Invoice Date"), default=timezone.now)
    due_date = models.DateField(_("Due Date"))
    subtotal = models.DecimalField(
        _("Subtotal"),
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    tax_amount = models.DecimalField(
        _("Tax Amount"),
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    total_amount = models.DecimalField(
        _("Total Invoiced Amount"),
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    currency = models.CharField(_("Currency"), max_length=3, default="INR")
    notes = models.TextField(_("Invoice Notes"), blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_bills",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Vendor Bill")
        verbose_name_plural = _("Vendor Bills")
        ordering = ["-bill_date"]
        unique_together = ("organization", "supplier", "bill_number")

    def __str__(self):
        return f"{self.supplier.code}: Bill #{self.bill_number} (${self.total_amount})"

    def recalculate_totals(self):
        sub = sum((l.line_subtotal for l in self.lines.all()), Decimal("0.00"))
        tax = sum((l.line_tax for l in self.lines.all()), Decimal("0.00"))
        self.subtotal = sub
        self.tax_amount = tax
        self.total_amount = sub + tax
        self.save(update_fields=["subtotal", "tax_amount", "total_amount", "updated_at"])


class VendorBillLine(models.Model):
    """
    Priced line item on a vendor invoice referencing a PO line item.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bill = models.ForeignKey(
        VendorBill,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    po_line = models.ForeignKey(
        PurchaseOrderLine,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bill_lines",
    )
    product = models.ForeignKey(
        "sales.Product",
        on_delete=models.PROTECT,
        related_name="vendor_bill_lines",
    )
    billed_quantity = models.DecimalField(_("Billed Quantity"), max_digits=12, decimal_places=2)
    unit_price = models.DecimalField(_("Billed Unit Price"), max_digits=14, decimal_places=2)
    tax_rate = models.DecimalField(_("Tax Rate (%)"), max_digits=5, decimal_places=2, default=Decimal("0.00"))
    line_subtotal = models.DecimalField(_("Subtotal"), max_digits=14, decimal_places=2, default=Decimal("0.00"))
    line_tax = models.DecimalField(_("Tax"), max_digits=14, decimal_places=2, default=Decimal("0.00"))
    line_total = models.DecimalField(_("Line Total"), max_digits=14, decimal_places=2, default=Decimal("0.00"))
    notes = models.CharField(_("Line Notes"), max_length=255, blank=True)

    class Meta:
        verbose_name = _("Vendor Bill Line")
        verbose_name_plural = _("Vendor Bill Lines")

    def __str__(self):
        return f"{self.bill.bill_number}: {self.product.name} ({self.billed_quantity} @ ${self.unit_price})"

    def save(self, *args, **kwargs):
        self.line_subtotal = self.billed_quantity * self.unit_price
        self.line_tax = self.line_subtotal * (self.tax_rate / Decimal("100.00"))
        self.line_total = self.line_subtotal + self.line_tax
        super().save(*args, **kwargs)


class ThreeWayMatch(models.Model):
    """
    Verification record reconciling:
    1. Purchase Order (Commercial Agreement)
    2. Warehouse Goods Receipt (Physical Verification)
    3. Vendor Invoice / Bill (Financial Claim)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="three_way_matches",
    )
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name="three_way_matches",
    )
    vendor_bill = models.ForeignKey(
        VendorBill,
        on_delete=models.CASCADE,
        related_name="three_way_matches",
    )
    status = models.CharField(
        _("Match Outcome"),
        max_length=30,
        choices=MatchStatus.choices,
        default=MatchStatus.MATCHED,
    )
    po_total_ordered = models.DecimalField(_("PO Total Quantity"), max_digits=12, decimal_places=2, default=Decimal("0.00"))
    warehouse_received = models.DecimalField(_("Warehouse Received Quantity"), max_digits=12, decimal_places=2, default=Decimal("0.00"))
    invoice_billed = models.DecimalField(_("Invoice Billed Quantity"), max_digits=12, decimal_places=2, default=Decimal("0.00"))
    quantity_variance = models.DecimalField(_("Quantity Variance"), max_digits=12, decimal_places=2, default=Decimal("0.00"))
    po_amount = models.DecimalField(_("PO Amount"), max_digits=14, decimal_places=2, default=Decimal("0.00"))
    billed_amount = models.DecimalField(_("Billed Amount"), max_digits=14, decimal_places=2, default=Decimal("0.00"))
    price_variance_amount = models.DecimalField(_("Price Variance ($)"), max_digits=14, decimal_places=2, default=Decimal("0.00"))
    is_within_tolerance = models.BooleanField(_("Within Commercial Tolerance"), default=True)
    dispute_reason = models.TextField(_("Dispute / Variance Details"), blank=True)
    resolution_notes = models.TextField(_("Resolution Justification"), blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_matches",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Three-Way Match")
        verbose_name_plural = _("Three-Way Matches")
        ordering = ["-created_at"]

    def __str__(self):
        return f"Match for {self.purchase_order.po_number} vs Bill #{self.vendor_bill.bill_number}: {self.status}"
