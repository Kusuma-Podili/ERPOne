"""
EnterpriseOne Inventory Admin Registrations.
"""
from django.contrib import admin
from .models import (
    Warehouse,
    StorageZone,
    StorageLocation,
    StockItem,
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
