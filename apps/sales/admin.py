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
    TaxRule,
    TaxRate,
    Quote,
    QuoteLineItem,
    QuoteApproval,
    SalesOrder,
    OrderLineItem,
    OrderStatusHistory,
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


class TaxRateInline(admin.TabularInline):
    model = TaxRate
    extra = 0
    fields = ("name", "rate", "is_compound", "is_active")


@admin.register(TaxRule)
class TaxRuleAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "organization", "is_active")
    list_filter = ("organization", "is_active")
    search_fields = ("name", "code")
    inlines = [TaxRateInline]


class QuoteLineItemInline(admin.TabularInline):
    model = QuoteLineItem
    extra = 0
    fields = ("line_number", "product", "quantity", "unit_price", "discount_percent", "tax_rate", "total_price")
    readonly_fields = ("total_price",)


class QuoteApprovalInline(admin.TabularInline):
    model = QuoteApproval
    extra = 0
    fields = ("requested_by", "approver", "discount_threshold_exceeded", "status", "requested_at", "decided_at")
    readonly_fields = ("requested_at",)


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ("quote_number", "title", "account", "organization", "status", "grand_total", "valid_until", "created_at")
    list_filter = ("organization", "status")
    search_fields = ("quote_number", "title", "account__name")
    inlines = [QuoteLineItemInline, QuoteApprovalInline]


class OrderLineItemInline(admin.TabularInline):
    model = OrderLineItem
    extra = 0
    fields = ("line_number", "product", "quantity_ordered", "quantity_fulfilled", "unit_price", "discount_amount", "tax_amount", "total_price")
    readonly_fields = ("total_price",)


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    fields = ("from_status", "to_status", "changed_by", "timestamp", "notes")
    readonly_fields = ("timestamp",)


@admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "account", "organization", "status", "grand_total", "order_date", "fulfillment_percentage", "created_at")
    list_filter = ("organization", "status")
    search_fields = ("order_number", "account__name")
    inlines = [OrderLineItemInline, OrderStatusHistoryInline]


@admin.register(OrderLineItem)
class OrderLineItemAdmin(admin.ModelAdmin):
    list_display = ("order", "line_number", "product", "quantity_ordered", "quantity_fulfilled", "unit_price", "total_price")
    list_filter = ("order__status", "product")
    search_fields = ("order__order_number", "product__name")


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("order", "from_status", "to_status", "changed_by", "timestamp")
    list_filter = ("from_status", "to_status")
    search_fields = ("order__order_number",)


