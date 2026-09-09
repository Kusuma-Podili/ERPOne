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
