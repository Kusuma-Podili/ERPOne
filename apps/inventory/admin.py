"""
EnterpriseOne Inventory Admin Registrations.
"""
from django.contrib import admin
from .models import (
    Warehouse,
    StorageZone,
    StorageLocation,
    StockItem,
    StockMovement,
    StockMovementLine,
    LotBatch,
    SerialNumber,
    ReorderRule,
    PurchaseRequisition,
    PurchaseRequisitionLine,
)


class StorageZoneInline(admin.TabularInline):
    model = StorageZone
    extra = 0
    fields = ("name", "code", "zone_type", "temperature_controlled", "is_active")


class StorageLocationInline(admin.TabularInline):
    model = StorageLocation
    extra = 0
    fields = ("code", "aisle", "rack", "shelf", "bin", "max_weight_kg", "is_locked", "is_active")


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "organization", "warehouse_type", "city", "is_primary", "is_active", "created_at")
    list_filter = ("organization", "warehouse_type", "is_primary", "is_active")
    search_fields = ("name", "code", "city")
    inlines = [StorageZoneInline]


@admin.register(StorageZone)
class StorageZoneAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "warehouse", "zone_type", "temperature_controlled", "is_active")
    list_filter = ("warehouse", "zone_type", "temperature_controlled", "is_active")
    search_fields = ("name", "code", "warehouse__name")
    inlines = [StorageLocationInline]


@admin.register(StorageLocation)
class StorageLocationAdmin(admin.ModelAdmin):
    list_display = ("code", "warehouse", "zone", "barcode", "max_weight_kg", "is_locked", "is_active")
    list_filter = ("warehouse", "zone", "is_locked", "is_active")
    search_fields = ("code", "barcode", "warehouse__code")


@admin.register(StockItem)
class StockItemAdmin(admin.ModelAdmin):
    list_display = ("product", "warehouse", "location", "quantity_on_hand", "quantity_reserved", "quantity_available", "needs_reorder")
    list_filter = ("warehouse", "product")
    search_fields = ("product__name", "product__sku", "warehouse__code", "location__code")


class StockMovementLineInline(admin.TabularInline):
    model = StockMovementLine
    extra = 0
    fields = ("product", "source_location", "destination_location", "quantity", "unit_cost", "batch_number", "serial_number")


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("movement_number", "movement_type", "status", "source_warehouse", "destination_warehouse", "movement_date", "posted_at", "created_by")
    list_filter = ("movement_type", "status", "source_warehouse", "destination_warehouse")
    search_fields = ("movement_number", "reference_document", "notes")
    inlines = [StockMovementLineInline]


@admin.register(LotBatch)
class LotBatchAdmin(admin.ModelAdmin):
    list_display = ("batch_number", "product", "supplier_lot_number", "expiration_date", "qc_status", "current_quantity", "is_active")
    list_filter = ("qc_status", "is_active", "expiration_date")
    search_fields = ("batch_number", "supplier_lot_number", "product__name", "product__sku")


@admin.register(SerialNumber)
class SerialNumberAdmin(admin.ModelAdmin):
    list_display = ("serial_number", "product", "lot", "warehouse", "location", "status", "warranty_end_date")
    list_filter = ("status", "warehouse")
    search_fields = ("serial_number", "product__name", "product__sku", "lot__batch_number")


@admin.register(ReorderRule)
class ReorderRuleAdmin(admin.ModelAdmin):
    list_display = ("product", "warehouse", "min_quantity", "max_quantity", "reorder_quantity", "lead_time_days", "auto_reorder_enabled", "is_active")
    list_filter = ("warehouse", "auto_reorder_enabled", "is_active")
    search_fields = ("product__name", "product__sku", "warehouse__code", "preferred_vendor_name")


class PurchaseRequisitionLineInline(admin.TabularInline):
    model = PurchaseRequisitionLine
    extra = 0
    fields = ("product", "quantity_requested", "estimated_unit_cost", "notes")


@admin.register(PurchaseRequisition)
class PurchaseRequisitionAdmin(admin.ModelAdmin):
    list_display = ("requisition_number", "warehouse", "status", "priority", "required_by_date", "requested_by", "approved_by", "approved_at")
    list_filter = ("status", "priority", "warehouse")
    search_fields = ("requisition_number", "justification")
    inlines = [PurchaseRequisitionLineInline]



