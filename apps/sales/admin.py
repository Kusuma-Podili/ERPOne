"""
EnterpriseOne Sales Admin Registrations.
"""
from django.contrib import admin
from .models import (
    ProductCategory,
    UnitOfMeasure,
    Product,
    PriceBook,
    PriceBookEntry,
    TieredDiscount,
)


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "organization", "parent", "is_active", "created_at")
    list_filter = ("organization", "is_active")
    search_fields = ("name", "code", "description")


@admin.register(UnitOfMeasure)
class UnitOfMeasureAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "category", "organization", "is_base_unit", "ratio_to_base", "is_active")
    list_filter = ("organization", "category", "is_base_unit", "is_active")
    search_fields = ("name", "code")


class PriceBookEntryInline(admin.TabularInline):
    model = PriceBookEntry
    extra = 0
    fields = ("product", "unit_price", "minimum_quantity", "is_active")


class TieredDiscountInline(admin.TabularInline):
    model = TieredDiscount
    extra = 0
    fields = ("min_quantity", "max_quantity", "discount_type", "discount_value", "is_active")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "sku", "product_type", "category", "organization", "cost_price", "list_price", "is_active")
    list_filter = ("organization", "product_type", "is_active", "taxable")
    search_fields = ("name", "sku", "barcode", "description")
    inlines = [PriceBookEntryInline]


@admin.register(PriceBook)
class PriceBookAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "organization", "currency", "is_default", "is_active", "valid_from", "valid_to")
    list_filter = ("organization", "is_default", "is_active")
    search_fields = ("name", "code", "description")
    inlines = [PriceBookEntryInline]


@admin.register(PriceBookEntry)
class PriceBookEntryAdmin(admin.ModelAdmin):
    list_display = ("price_book", "product", "unit_price", "minimum_quantity", "is_active")
    list_filter = ("is_active", "price_book")
    search_fields = ("price_book__name", "product__name", "product__sku")
    inlines = [TieredDiscountInline]


@admin.register(TieredDiscount)
class TieredDiscountAdmin(admin.ModelAdmin):
    list_display = ("price_book_entry", "min_quantity", "max_quantity", "discount_type", "discount_value", "is_active")
    list_filter = ("is_active", "discount_type")
