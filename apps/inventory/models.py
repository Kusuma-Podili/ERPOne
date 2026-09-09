"""
EnterpriseOne Inventory & Warehouse Management Domain Models.
Defines multi-warehouse hierarchies, spatial zones, bin coordinates, and product inventory levels.
"""
import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class WarehouseType(models.TextChoices):
    DISTRIBUTION_CENTER = "distribution_center", _("Distribution Center")
    MANUFACTURING_PLANT = "manufacturing_plant", _("Manufacturing Plant")
    RETAIL_STORE = "retail_store", _("Retail Outlet / Store")
    TRANSIT_HUB = "transit_hub", _("Transit / Cross-Dock Hub")
    QUARANTINE_FACILITY = "quarantine_facility", _("Quarantine & Inspection Facility")


class Warehouse(models.Model):
    """
    Physical distribution center, storage plant, or retail logistics facility.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="warehouses",
    )
    name = models.CharField(_("Warehouse Name"), max_length=150)
    code = models.CharField(_("Warehouse Code"), max_length=50)
    warehouse_type = models.CharField(
        _("Warehouse Type"),
        max_length=40,
        choices=WarehouseType.choices,
        default=WarehouseType.DISTRIBUTION_CENTER,
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="warehouses",
    )
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_warehouses",
    )
    address = models.TextField(_("Street Address"), blank=True)
    city = models.CharField(_("City"), max_length=100, blank=True)
    state_province = models.CharField(_("State / Province"), max_length=100, blank=True)
    postal_code = models.CharField(_("Postal Code"), max_length=20, blank=True)
    country = models.CharField(_("Country"), max_length=100, default="USA", blank=True)
    is_primary = models.BooleanField(
        _("Primary Headquarters Facility"),
        default=False,
        help_text=_("Designates the primary fulfillment node for standard order allocation."),
    )
    total_capacity_cbm = models.DecimalField(
        _("Capacity (Cubic Meters)"),
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Total usable storage volume in cubic meters."),
    )
    is_active = models.BooleanField(_("Active"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Warehouse")
        verbose_name_plural = _("Warehouses")
        ordering = ["name"]
        unique_together = ("organization", "code")

    def __str__(self):
        return f"{self.name} ({self.code})"

    def clean(self):
        super().clean()
        if self.is_primary:
            existing = Warehouse.objects.filter(
                organization=self.organization,
                is_primary=True,
            ).exclude(pk=self.pk)
            if existing.exists():
                raise ValidationError({"is_primary": _("An organization can only designate one primary warehouse.")})

    @property
    def total_zones_count(self) -> int:
        return self.zones.count()

    @property
    def total_locations_count(self) -> int:
        return self.locations.count()

    @property
    def total_stock_items_count(self) -> int:
        return self.stock_items.count()


class StorageZoneType(models.TextChoices):
    GENERAL = "general", _("General Storage")
    COLD_STORAGE = "cold_storage", _("Cold / Refrigerated Storage")
    HAZARDOUS = "hazardous", _("Hazardous Materials (HazMat)")
    BULK_STORAGE = "bulk_storage", _("Bulk / High-Bay Storage")
    RECEIVING = "receiving", _("Inbound Receiving Dock")
    SHIPPING = "shipping", _("Outbound Staging & Shipping")
    PICKING = "picking", _("Fast-Pick Forward Area")
    QUARANTINE = "quarantine", _("Quality Quarantine & Inspection")


class StorageZone(models.Model):
    """
    Subdivided operational sector within a warehouse with environmental or logistical specializations.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="storage_zones",
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="zones",
    )
    name = models.CharField(_("Zone Name"), max_length=100)
    code = models.CharField(_("Zone Code"), max_length=30)
    zone_type = models.CharField(
        _("Zone Classification"),
        max_length=30,
        choices=StorageZoneType.choices,
        default=StorageZoneType.GENERAL,
    )
    temperature_controlled = models.BooleanField(_("Temperature Controlled"), default=False)
    target_temp_celsius = models.DecimalField(
        _("Target Temp (°C)"),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Operating temperature threshold if climate-controlled."),
    )
    is_active = models.BooleanField(_("Active"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Storage Zone")
        verbose_name_plural = _("Storage Zones")
        ordering = ["warehouse", "code"]
        unique_together = ("warehouse", "code")

    def __str__(self):
        return f"{self.warehouse.code} / {self.name} ({self.code})"

    @property
    def total_locations_count(self) -> int:
        return self.locations.count()


class StorageLocation(models.Model):
    """
    Granular coordinate slot (Aisle-Rack-Shelf-Bin) holding physical inventory.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="storage_locations",
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="locations",
    )
    zone = models.ForeignKey(
        StorageZone,
        on_delete=models.CASCADE,
        related_name="locations",
    )
    code = models.CharField(_("Location Identifier Code"), max_length=60, db_index=True)
    aisle = models.CharField(_("Aisle"), max_length=20, default="01")
    rack = models.CharField(_("Rack / Bay"), max_length=20, default="01")
    shelf = models.CharField(_("Shelf / Tier"), max_length=20, default="01")
    bin = models.CharField(_("Bin / Position"), max_length=20, default="01")
    barcode = models.CharField(_("Barcode Identifier"), max_length=100, blank=True, db_index=True)
    max_weight_kg = models.DecimalField(
        _("Max Weight (kg)"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("1000.00"),
    )
    max_volume_cbm = models.DecimalField(
        _("Max Volume (m³)"),
        max_digits=8,
        decimal_places=3,
        default=Decimal("2.000"),
    )
    is_locked = models.BooleanField(
        _("Locked"),
        default=False,
        help_text=_("Disables putaway and picking during cycle count or maintenance."),
    )
    lock_reason = models.CharField(_("Lock Reason"), max_length=255, blank=True)
    is_active = models.BooleanField(_("Active"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Storage Location")
        verbose_name_plural = _("Storage Locations")
        ordering = ["warehouse", "code"]
        unique_together = ("warehouse", "code")

    def __str__(self):
        return f"{self.warehouse.code} - {self.code}"

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.generate_location_code()
        if not self.barcode:
            self.barcode = f"LOC-{self.warehouse.code}-{self.code}"
        super().save(*args, **kwargs)

    def generate_location_code(self) -> str:
        return f"{self.zone.code}-A{self.aisle}-R{self.rack}-S{self.shelf}-B{self.bin}"

    def clean(self):
        super().clean()
        if self.zone.warehouse_id != self.warehouse_id:
            raise ValidationError({"zone": _("Storage zone must belong to the selected warehouse.")})


class StockItem(models.Model):
    """
    Product inventory level snapshot positioned at a specific warehouse and storage location.
    Tracks on-hand physical stock, reserved allocations, and replenishment triggers.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="stock_items",
    )
    product = models.ForeignKey(
        "sales.Product",
        on_delete=models.CASCADE,
        related_name="stock_levels",
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="stock_items",
    )
    location = models.ForeignKey(
        StorageLocation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_items",
    )
    quantity_on_hand = models.DecimalField(
        _("Quantity On-Hand"),
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Total physical items present in storage."),
    )
    quantity_reserved = models.DecimalField(
        _("Quantity Reserved"),
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Items allocated to confirmed sales orders awaiting picking."),
    )
    safety_stock = models.DecimalField(
        _("Safety Stock Buffer"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("10.00"),
        help_text=_("Buffer quantity below which emergency procurement is required."),
    )
    reorder_point = models.DecimalField(
        _("Reorder Point Threshold"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("25.00"),
        help_text=_("Inventory level triggering standard restocking requisition."),
    )
    reorder_quantity = models.DecimalField(
        _("Economic Reorder Quantity (EOQ)"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("50.00"),
        help_text=_("Standard replenishment batch order quantity."),
    )
    last_counted_at = models.DateTimeField(_("Last Physical Audit Date"), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Stock Item Level")
        verbose_name_plural = _("Stock Item Levels")
        ordering = ["product__name", "warehouse__code"]
        unique_together = ("warehouse", "location", "product")

    def __str__(self):
        loc_str = self.location.code if self.location else "Unassigned Location"
        return f"{self.product.name} @ {self.warehouse.code} ({loc_str}): {self.quantity_on_hand} On-Hand"

    @property
    def quantity_available(self) -> Decimal:
        return max(Decimal("0.00"), self.quantity_on_hand - self.quantity_reserved)

    @property
    def needs_reorder(self) -> bool:
        return self.quantity_on_hand <= self.reorder_point

    @property
    def is_below_safety(self) -> bool:
        return self.quantity_on_hand <= self.safety_stock

    def clean(self):
        super().clean()
        if self.quantity_on_hand < Decimal("0.00"):
            raise ValidationError({"quantity_on_hand": _("Physical stock on-hand cannot be negative.")})
        if self.quantity_reserved < Decimal("0.00"):
            raise ValidationError({"quantity_reserved": _("Reserved quantity cannot be negative.")})
        if self.quantity_reserved > self.quantity_on_hand:
            raise ValidationError(
                {"quantity_reserved": _("Reserved quantity cannot exceed total physical on-hand stock.")}
            )


class StockMovementType(models.TextChoices):
    RECEIPT = "receipt", _("Inbound Goods Receipt")
    TRANSFER = "transfer", _("Warehouse Transfer")
    LOCATION_TRANSFER = "location_transfer", _("Internal Location Relocation")
    ADJUSTMENT = "adjustment", _("Inventory Adjustment / Variance")
    SCRAP = "scrap", _("Damaged / Scrap Write-Off")
    RETURN = "return", _("Customer / Vendor Return")


class StockMovementStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    APPROVED = "approved", _("Approved")
    COMPLETED = "completed", _("Completed / Posted")
    CANCELLED = "cancelled", _("Cancelled")


class StockMovement(models.Model):
    """
    Stock movement ledger document tracking physical inventory transfers,
    goods receipts, scrap write-offs, and location relocations.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="stock_movements",
    )
    movement_number = models.CharField(_("Movement Number"), max_length=64, blank=True, db_index=True)
    movement_type = models.CharField(
        _("Movement Type"),
        max_length=30,
        choices=StockMovementType.choices,
        default=StockMovementType.RECEIPT,
    )
    status = models.CharField(
        _("Status"),
        max_length=30,
        choices=StockMovementStatus.choices,
        default=StockMovementStatus.DRAFT,
    )
    source_warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="outbound_movements",
        help_text=_("Origin facility for transfers, scrap, and negative adjustments."),
    )
    destination_warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="inbound_movements",
        help_text=_("Destination facility for receipts, inbound transfers, and returns."),
    )
    reference_document = models.CharField(
        _("Reference Document"),
        max_length=100,
        blank=True,
        help_text=_("External PO number, Sales Order, RMA, or Audit Count ID."),
    )
    movement_date = models.DateTimeField(_("Movement Date"), default=timezone.now)
    posted_at = models.DateTimeField(_("Posted At"), null=True, blank=True)
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posted_stock_movements",
    )
    notes = models.TextField(_("Notes & Operational Justification"), blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_stock_movements",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Stock Movement")
        verbose_name_plural = _("Stock Movements")
        ordering = ["-created_at"]
        unique_together = ("organization", "movement_number")

    def __str__(self):
        return f"{self.movement_number} ({self.get_movement_type_display()}) - {self.get_status_display()}"

    def save(self, *args, **kwargs):
        if not self.movement_number:
            self.movement_number = self.generate_movement_number()
        super().save(*args, **kwargs)

    def generate_movement_number(self) -> str:
        year = timezone.now().year
        count = StockMovement.objects.filter(
            organization=self.organization,
            movement_date__year=year,
        ).count() + 1
        return f"SM-{year}-{count:05d}"

    def clean(self):
        super().clean()
        if not self.movement_number and self.organization_id:
            self.movement_number = self.generate_movement_number()
        if self.movement_type == StockMovementType.TRANSFER:
            if not self.source_warehouse:
                raise ValidationError({"source_warehouse": _("Source warehouse is required for transfers.")})
            if not self.destination_warehouse:
                raise ValidationError({"destination_warehouse": _("Destination warehouse is required for transfers.")})
            if self.source_warehouse_id == self.destination_warehouse_id:
                raise ValidationError(
                    {"destination_warehouse": _("Source and destination warehouses cannot be the same.")}
                )
        elif self.movement_type == StockMovementType.LOCATION_TRANSFER:
            if not self.source_warehouse:
                raise ValidationError({"source_warehouse": _("Warehouse facility is required for location transfers.")})
            if not self.destination_warehouse:
                self.destination_warehouse = self.source_warehouse
        elif self.movement_type == StockMovementType.RECEIPT:
            if not self.destination_warehouse:
                raise ValidationError({"destination_warehouse": _("Destination warehouse is required for goods receipts.")})
        elif self.movement_type in [StockMovementType.SCRAP, StockMovementType.ADJUSTMENT]:
            if not self.source_warehouse:
                raise ValidationError({"source_warehouse": _("Warehouse is required for inventory adjustments / scrap.")})

    @property
    def total_lines_count(self) -> int:
        return self.lines.count()

    @property
    def total_quantity(self) -> Decimal:
        return sum((line.quantity for line in self.lines.all()), Decimal("0.00"))

    @property
    def total_value(self) -> Decimal:
        return sum((line.total_value for line in self.lines.all()), Decimal("0.00"))

    @property
    def can_post(self) -> bool:
        return self.status in [StockMovementStatus.DRAFT, StockMovementStatus.APPROVED]

    @property
    def can_cancel(self) -> bool:
        return self.status in [StockMovementStatus.DRAFT, StockMovementStatus.APPROVED]


class StockMovementLine(models.Model):
    """
    Individual item entry within a stock movement document.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    movement = models.ForeignKey(
        StockMovement,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    product = models.ForeignKey(
        "sales.Product",
        on_delete=models.CASCADE,
        related_name="movement_lines",
    )
    source_location = models.ForeignKey(
        StorageLocation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_movement_lines",
    )
    destination_location = models.ForeignKey(
        StorageLocation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dest_movement_lines",
    )
    quantity = models.DecimalField(
        _("Quantity Moved"),
        max_digits=12,
        decimal_places=2,
    )
    unit_cost = models.DecimalField(
        _("Unit Cost"),
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    batch_number = models.CharField(_("Batch / Lot #"), max_length=60, blank=True)
    serial_number = models.CharField(_("Serial Number"), max_length=60, blank=True)
    notes = models.CharField(_("Line Notes"), max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Stock Movement Line")
        verbose_name_plural = _("Stock Movement Lines")
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.product.name} x {self.quantity} ({self.movement.movement_number})"

    @property
    def total_value(self) -> Decimal:
        return (self.quantity or Decimal("0.00")) * (self.unit_cost or Decimal("0.00"))

    def clean(self):
        super().clean()
        if self.quantity is not None and self.quantity <= Decimal("0.00"):
            raise ValidationError({"quantity": _("Quantity moved must be greater than zero.")})
        if self.source_location and self.movement.source_warehouse_id:
            if self.source_location.warehouse_id != self.movement.source_warehouse_id:
                raise ValidationError({"source_location": _("Source location must belong to movement source warehouse.")})
        if self.destination_location and self.movement.destination_warehouse_id:
            if self.destination_location.warehouse_id != self.movement.destination_warehouse_id:
                raise ValidationError({"destination_location": _("Destination location must belong to movement destination warehouse.")})
