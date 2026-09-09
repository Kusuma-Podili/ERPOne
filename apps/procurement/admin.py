"""
EnterpriseOne Procurement Admin Registrations.
"""
from django.contrib import admin
from .models import (
    Supplier,
    SupplierContact,
    SupplierProduct,
    RequestForQuotation,
    RFQLine,
    RFQVendorInvitation,
    VendorBid,
    VendorBidLine,
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


class RFQLineInline(admin.TabularInline):
    model = RFQLine
    extra = 0
    fields = ("line_number", "product", "target_quantity", "uom", "target_delivery_date", "specifications")


class RFQVendorInvitationInline(admin.TabularInline):
    model = RFQVendorInvitation
    extra = 0
    fields = ("supplier", "invited_at", "responded_at")


@admin.register(RequestForQuotation)
class RequestForQuotationAdmin(admin.ModelAdmin):
    list_display = ("rfq_number", "title", "organization", "status", "submission_deadline", "delivery_deadline", "created_by", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("rfq_number", "title", "notes")
    inlines = [RFQLineInline, RFQVendorInvitationInline]


class VendorBidLineInline(admin.TabularInline):
    model = VendorBidLine
    extra = 0
    fields = ("rfq_line", "offered_unit_price", "offered_quantity", "lead_time_days", "notes")


@admin.register(VendorBid)
class VendorBidAdmin(admin.ModelAdmin):
    list_display = ("bid_reference", "rfq", "supplier", "total_amount", "currency", "lead_time_days", "is_winning_bid", "submission_date")
    list_filter = ("is_winning_bid", "submission_date", "currency")
    search_fields = ("bid_reference", "supplier__name", "rfq__rfq_number")
    inlines = [VendorBidLineInline]

