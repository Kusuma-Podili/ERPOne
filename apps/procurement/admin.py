"""
EnterpriseOne Procurement Admin Registrations.
"""
from django.contrib import admin
from .models import (
    Supplier,
    SupplierContact,
    SupplierProduct,
)


class SupplierContactInline(admin.TabularInline):
    model = SupplierContact
    extra = 0
    fields = ("name", "title", "email", "phone", "is_primary")


class SupplierProductInline(admin.TabularInline):
    model = SupplierProduct
    extra = 0
    fields = ("product", "supplier_sku", "unit_price", "minimum_order_quantity", "lead_time_days", "is_preferred", "is_active")


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "organization", "supplier_type", "status", "payment_terms", "city", "lead_time_rating", "quality_rating", "is_active")
    list_filter = ("supplier_type", "status", "payment_terms", "is_active")
    search_fields = ("name", "code", "tax_id", "email")
    inlines = [SupplierContactInline, SupplierProductInline]


@admin.register(SupplierContact)
class SupplierContactAdmin(admin.ModelAdmin):
    list_display = ("name", "supplier", "title", "email", "phone", "is_primary")
    list_filter = ("is_primary",)
    search_fields = ("name", "email", "supplier__name")


@admin.register(SupplierProduct)
class SupplierProductAdmin(admin.ModelAdmin):
    list_display = ("supplier", "product", "supplier_sku", "unit_price", "minimum_order_quantity", "lead_time_days", "is_preferred", "is_active")
    list_filter = ("is_preferred", "is_active")
    search_fields = ("supplier__name", "product__name", "product__sku", "supplier_sku")
