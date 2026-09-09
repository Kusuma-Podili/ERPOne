"""
EnterpriseOne Sales & Order Management Domain Models.
Defines product catalogs, units of measurement, price books, tiered discounts,
quotations, approvals, sales orders, order items, and audit state machines.
"""
import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone


class ProductCategory(models.Model):
    """
    Hierarchical product classification tree supporting nested subcategories.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="product_categories",
    )
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subcategories",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Product Category"
        verbose_name_plural = "Product Categories"
        ordering = ["name"]
        unique_together = ("organization", "code")

    def __str__(self):
        return self.get_full_path()

    def get_full_path(self):
        """Returns the breadcrumb path of the category, e.g. 'Hardware > Networking > Routers'."""
        parts = [self.name]
        curr = self.parent
        visited = {self.id}
        while curr:
            if curr.id in visited:
                break
            visited.add(curr.id)
            parts.append(curr.name)
            curr = curr.parent
        return " > ".join(reversed(parts))

    def clean(self):
        super().clean()
        if self.parent_id:
            if self.parent_id == self.id:
                raise ValidationError({"parent": "A category cannot be its own parent."})
            # Check for circular loops
            curr = self.parent
            visited = {self.id}
            while curr:
                if curr.id in visited:
                    raise ValidationError({"parent": "Circular category hierarchy detected."})
                visited.add(curr.id)
                curr = curr.parent


class UnitOfMeasure(models.Model):
    """
    Standardized measurement units for inventory, sales pricing, and line items.
    """
    CATEGORY_CHOICES = [
        ("unit", "Count / Unit"),
        ("time", "Time / Duration"),
        ("weight", "Weight / Mass"),
        ("length", "Length / Distance"),
        ("volume", "Volume / Liquid"),
        ("area", "Surface Area"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="units_of_measure",
    )
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default="unit")
    is_base_unit = models.BooleanField(default=True, help_text="Designates the reference standard unit for this category.")
    ratio_to_base = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=Decimal("1.0000"),
        help_text="Multiplier to convert this unit into the category base unit.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Unit of Measure"
        verbose_name_plural = "Units of Measure"
        ordering = ["category", "name"]
        unique_together = ("organization", "code")

    def __str__(self):
        return f"{self.name} ({self.code})"

    def convert_to_base(self, quantity: Decimal) -> Decimal:
        """Converts a given quantity in this UOM to the standard base unit."""
        return Decimal(quantity) * self.ratio_to_base

    def convert_from_base(self, base_quantity: Decimal) -> Decimal:
        """Converts a quantity from standard base unit into this UOM."""
        if self.ratio_to_base == Decimal("0"):
            return Decimal("0")
        return Decimal(base_quantity) / self.ratio_to_base


class Product(models.Model):
    """
    Master product catalog entity encompassing physical goods, professional services,
    digital licenses, and subscriptions.
    """
    PRODUCT_TYPE_CHOICES = [
        ("goods", "Physical Goods"),
        ("service", "Professional Service"),
        ("digital", "Digital Software / License"),
        ("subscription", "Recurring Subscription"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="products",
    )
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100, db_index=True)
    barcode = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    product_type = models.CharField(max_length=30, choices=PRODUCT_TYPE_CHOICES, default="goods")
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    uom = models.ForeignKey(
        UnitOfMeasure,
        on_delete=models.PROTECT,
        related_name="products",
    )
    cost_price = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    list_price = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=3, default="USD")
    taxable = models.BooleanField(default=True)
    track_inventory = models.BooleanField(
        default=True,
        help_text="Track stock levels and warehouse allocations for physical goods.",
    )
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    specifications = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_products",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ["name"]
        unique_together = ("organization", "sku")

    def __str__(self):
        return f"{self.name} [{self.sku}]"

    @property
    def profit_margin(self) -> Decimal:
        """Computes gross profit per unit in base currency."""
        return self.list_price - self.cost_price

    @property
    def margin_percentage(self) -> Decimal:
        """Computes margin as a percentage of list price."""
        if self.list_price == Decimal("0"):
            return Decimal("0.00")
        return ((self.list_price - self.cost_price) / self.list_price * Decimal("100")).quantize(Decimal("0.01"))


class PriceBook(models.Model):
    """
    Price book grouping products with custom negotiated or market-tier price schedules.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="price_books",
    )
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    currency = models.CharField(max_length=3, default="USD")
    is_default = models.BooleanField(
        default=False,
        help_text="Default price book applied when no customer-specific schedule is assigned.",
    )
    is_active = models.BooleanField(default=True)
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_price_books",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Price Book"
        verbose_name_plural = "Price Books"
        ordering = ["-is_default", "name"]
        unique_together = ("organization", "code")

    def __str__(self):
        suffix = " (Default)" if self.is_default else ""
        return f"{self.name}{suffix}"

    def clean(self):
        super().clean()
        if self.valid_from and self.valid_to and self.valid_from > self.valid_to:
            raise ValidationError({"valid_to": "Valid To date must be greater than or equal to Valid From date."})

    def save(self, *args, **kwargs):
        if self.is_default:
            PriceBook.objects.filter(
                organization=self.organization,
                is_default=True,
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    def is_effective(self, check_date=None) -> bool:
        """Determines if the price book is active and within effective dates."""
        if not self.is_active:
            return False
        if check_date is None:
            check_date = timezone.now().date()
        if self.valid_from and check_date < self.valid_from:
            return False
        if self.valid_to and check_date > self.valid_to:
            return False
        return True


class PriceBookEntry(models.Model):
    """
    Specific product unit price mapped within a designated PriceBook.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="price_book_entries",
    )
    price_book = models.ForeignKey(
        PriceBook,
        on_delete=models.CASCADE,
        related_name="entries",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="price_book_entries",
    )
    unit_price = models.DecimalField(max_digits=14, decimal_places=2)
    minimum_quantity = models.PositiveIntegerField(
        default=1,
        help_text="Minimum order quantity required to qualify for this price entry.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Price Book Entry"
        verbose_name_plural = "Price Book Entries"
        ordering = ["price_book", "product"]
        unique_together = ("price_book", "product")

    def __str__(self):
        return f"{self.price_book.name} - {self.product.name}: {self.unit_price}"

    def clean(self):
        super().clean()
        if self.unit_price < Decimal("0.00"):
            raise ValidationError({"unit_price": "Unit price cannot be negative."})


class TieredDiscount(models.Model):
    """
    Volume break tiered discounts for quantity purchases under a price book entry.
    """
    DISCOUNT_TYPE_CHOICES = [
        ("percentage", "Percentage Discount (%)"),
        ("fixed_price", "Fixed Unit Price ($)"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="tiered_discounts",
    )
    price_book_entry = models.ForeignKey(
        PriceBookEntry,
        on_delete=models.CASCADE,
        related_name="tiered_discounts",
    )
    min_quantity = models.PositiveIntegerField(help_text="Minimum order threshold for this tier.")
    max_quantity = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Upper threshold for tier. Leave blank for unbounded/infinity.",
    )
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES, default="percentage")
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Percentage off base price (e.g. 15.00 for 15%) or overridden fixed unit price.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tiered Discount"
        verbose_name_plural = "Tiered Discounts"
        ordering = ["min_quantity"]

    def __str__(self):
        max_str = self.max_quantity if self.max_quantity else "∞"
        if self.discount_type == "percentage":
            val_str = f"{self.discount_value}%"
        else:
            val_str = f"${self.discount_value}"
        return f"Qty {self.min_quantity}-{max_str}: {val_str}"

    def clean(self):
        super().clean()
        if self.max_quantity and self.min_quantity > self.max_quantity:
            raise ValidationError({"max_quantity": "Max quantity must be greater than or equal to min quantity."})
        if self.discount_type == "percentage" and (self.discount_value < Decimal("0") or self.discount_value > Decimal("100")):
            raise ValidationError({"discount_value": "Percentage discount must be between 0 and 100."})
        if self.discount_type == "fixed_price" and self.discount_value < Decimal("0"):
            raise ValidationError({"discount_value": "Fixed price discount cannot be negative."})

    def calculate_effective_unit_price(self, base_price: Decimal) -> Decimal:
        """Calculates effective unit price given the base entry price."""
        if self.discount_type == "fixed_price":
            return self.discount_value
        # Percentage discount
        discount_fraction = self.discount_value / Decimal("100")
        effective = base_price * (Decimal("1") - discount_fraction)
        return max(Decimal("0.00"), effective.quantize(Decimal("0.01")))


class TaxRule(models.Model):
    """
    Tax regulatory framework defining regional tax governance (e.g. US State Sales Tax, VAT, GST).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="tax_rules",
    )
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=30)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tax Rule"
        verbose_name_plural = "Tax Rules"
        ordering = ["name"]
        unique_together = ("organization", "code")

    def __str__(self):
        return f"{self.name} ({self.code})"


class TaxRate(models.Model):
    """
    Specific percentage tax rate mapped under a TaxRule.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="tax_rates",
    )
    tax_rule = models.ForeignKey(
        TaxRule,
        on_delete=models.CASCADE,
        related_name="rates",
    )
    name = models.CharField(max_length=100)
    rate = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        help_text="Tax percentage (e.g. 8.250 for 8.25%).",
    )
    is_compound = models.BooleanField(
        default=False,
        help_text="Compounded on top of previously calculated taxes.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tax Rate"
        verbose_name_plural = "Tax Rates"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.rate}%)"


class QuoteStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PENDING_APPROVAL = "pending_approval", "Pending Approval"
    APPROVED = "approved", "Approved"
    PRESENTED = "presented", "Presented to Customer"
    ACCEPTED = "accepted", "Accepted by Customer"
    REJECTED = "rejected", "Rejected by Customer"
    EXPIRED = "expired", "Expired"
    CONVERTED = "converted", "Converted to Order"


class Quote(models.Model):
    """
    Formal commercial quotation issued to prospective or existing accounts.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="quotes",
    )
    quote_number = models.CharField(max_length=64, db_index=True)
    title = models.CharField(max_length=255)
    account = models.ForeignKey(
        "crm.Account",
        on_delete=models.CASCADE,
        related_name="quotes",
    )
    contact = models.ForeignKey(
        "crm.Contact",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quotes",
    )
    deal = models.ForeignKey(
        "crm.Deal",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quotes",
    )
    price_book = models.ForeignKey(
        PriceBook,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quotes",
    )
    status = models.CharField(
        max_length=30,
        choices=QuoteStatus.choices,
        default=QuoteStatus.DRAFT,
        db_index=True,
    )
    currency = models.CharField(max_length=3, default="USD")
    subtotal_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    discount_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    shipping_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    grand_total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    valid_until = models.DateField(null=True, blank=True)
    payment_terms = models.CharField(max_length=100, default="Net 30")
    terms_and_conditions = models.TextField(blank=True)
    customer_notes = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)
    requires_approval = models.BooleanField(
        default=False,
        help_text="Flagged when discounts exceed managerial approval thresholds.",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_quotes",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    version = models.PositiveIntegerField(default=1)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_quotes",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Quotation"
        verbose_name_plural = "Quotations"
        ordering = ["-created_at"]
        unique_together = ("organization", "quote_number")

    def __str__(self):
        return f"{self.quote_number} - {self.title} ({self.account.name})"

    def save(self, *args, **kwargs):
        if not self.quote_number:
            self.quote_number = self.generate_quote_number()
        super().save(*args, **kwargs)

    def generate_quote_number(self) -> str:
        """Generates sequential quote identifier e.g. QT-2026-00001."""
        year = timezone.now().year
        count = Quote.objects.filter(
            organization=self.organization,
            quote_number__startswith=f"QT-{year}",
        ).count() + 1
        return f"QT-{year}-{count:05d}"

    def is_expired(self) -> bool:
        """Checks whether the quote validity period has expired."""
        if self.valid_until and timezone.now().date() > self.valid_until:
            return True
        return False

    @property
    def can_edit(self) -> bool:
        """Indicates if quote can be modified."""
        return self.status in [QuoteStatus.DRAFT, QuoteStatus.REJECTED]

    @property
    def can_convert(self) -> bool:
        """Indicates if quote is eligible to convert into a Sales Order."""
        return self.status == QuoteStatus.ACCEPTED

    def recalculate_totals(self):
        """
        Recalculates subtotal, discounts, taxes, and grand total from line items.
        """
        subtotal = Decimal("0.00")
        total_discount = Decimal("0.00")
        total_tax = Decimal("0.00")

        for line in self.line_items.all():
            subtotal += line.subtotal
            total_discount += line.discount_amount
            total_tax += line.tax_amount

        self.subtotal_amount = subtotal.quantize(Decimal("0.01"))
        self.discount_amount = total_discount.quantize(Decimal("0.01"))
        self.tax_amount = total_tax.quantize(Decimal("0.01"))
        self.grand_total = (
            subtotal - total_discount + total_tax + self.shipping_amount
        ).quantize(Decimal("0.01"))
        self.save(update_fields=[
            "subtotal_amount",
            "discount_amount",
            "tax_amount",
            "grand_total",
            "updated_at",
        ])


class QuoteLineItem(models.Model):
    """
    Individual product line item within a commercial Quotation.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="quote_line_items",
    )
    quote = models.ForeignKey(
        Quote,
        on_delete=models.CASCADE,
        related_name="line_items",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="quote_lines",
    )
    line_number = models.PositiveIntegerField(default=1)
    description = models.TextField(blank=True)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2)
    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Percentage discount applied to this line.",
    )
    discount_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    total_price = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Quote Line Item"
        verbose_name_plural = "Quote Line Items"
        ordering = ["quote", "line_number"]

    def __str__(self):
        return f"{self.quote.quote_number} - Line {self.line_number}: {self.product.name}"

    def calculate_amounts(self):
        """
        Calculates line subtotal, discount, tax, and net total.
        """
        qty = Decimal(self.quantity)
        self.subtotal = (self.unit_price * qty).quantize(Decimal("0.01"))
        
        # Discount
        if self.discount_percent > Decimal("0.00"):
            disc_fraction = self.discount_percent / Decimal("100")
            self.discount_amount = (self.subtotal * disc_fraction).quantize(Decimal("0.01"))
        else:
            self.discount_amount = Decimal("0.00")
        
        taxable_amount = self.subtotal - self.discount_amount
        if self.tax_rate > Decimal("0.00"):
            tax_fraction = self.tax_rate / Decimal("100")
            self.tax_amount = (taxable_amount * tax_fraction).quantize(Decimal("0.01"))
        else:
            self.tax_amount = Decimal("0.00")

        self.total_price = (taxable_amount + self.tax_amount).quantize(Decimal("0.01"))

    def save(self, *args, **kwargs):
        self.calculate_amounts()
        super().save(*args, **kwargs)


class QuoteApproval(models.Model):
    """
    Formal approval record tracking executive discount authorization.
    """
    STATUS_CHOICES = [
        ("pending", "Pending Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="quote_approvals",
    )
    quote = models.ForeignKey(
        Quote,
        on_delete=models.CASCADE,
        related_name="approvals",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="requested_quote_approvals",
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_quote_approvals",
    )
    discount_threshold_exceeded = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Highest discount percentage requiring approval.",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    requested_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Quote Approval"
        verbose_name_plural = "Quote Approvals"
        ordering = ["-requested_at"]

    def __str__(self):
        return f"Approval for {self.quote.quote_number} ({self.status})"

