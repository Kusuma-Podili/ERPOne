"""
Enterprise CRM Django Admin Registration.
Provides administrative inspection and management for Accounts and Contacts.
"""
from django.contrib import admin
from apps.crm.models import Account, Contact, Lead


class ContactInline(admin.TabularInline):
    model = Contact
    extra = 0
    fields = ("first_name", "last_name", "email", "phone", "job_title", "is_primary_contact")
    readonly_fields = ()


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "account_number",
        "organization",
        "account_type",
        "industry",
        "annual_revenue",
        "lifecycle_stage",
        "status",
        "owner",
        "created_at",
    )
    list_filter = (
        "account_type",
        "industry",
        "lifecycle_stage",
        "status",
        "organization",
    )
    search_fields = (
        "name",
        "account_number",
        "email",
        "phone",
        "website",
    )
    readonly_fields = ("id", "account_number", "created_at", "updated_at")
    inlines = [ContactInline]
    fieldsets = (
        ("Basic Information", {
            "fields": ("id", "organization", "name", "account_number", "account_type", "industry", "owner")
        }),
        ("Financial & Demographics", {
            "fields": ("annual_revenue", "employee_count", "website", "phone", "email")
        }),
        ("Lifecycle & Status", {
            "fields": ("lifecycle_stage", "status")
        }),
        ("Billing Address", {
            "fields": (
                "billing_address_line1",
                "billing_address_line2",
                "billing_city",
                "billing_state",
                "billing_postal_code",
                "billing_country",
            ),
            "classes": ("collapse",),
        }),
        ("Shipping Address", {
            "fields": (
                "shipping_address_line1",
                "shipping_address_line2",
                "shipping_city",
                "shipping_state",
                "shipping_postal_code",
                "shipping_country",
            ),
            "classes": ("collapse",),
        }),
        ("System Audit", {
            "fields": ("created_by", "created_at", "updated_at", "description"),
            "classes": ("collapse",),
        }),
    )


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "email",
        "phone",
        "account",
        "organization",
        "job_title",
        "is_primary_contact",
        "lifecycle_stage",
        "owner",
    )
    list_filter = (
        "is_primary_contact",
        "lifecycle_stage",
        "do_not_call",
        "do_not_email",
        "organization",
    )
    search_fields = (
        "first_name",
        "last_name",
        "email",
        "phone",
        "job_title",
        "account__name",
    )
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "company_name",
        "email",
        "lead_score",
        "status",
        "priority",
        "lead_source",
        "is_converted",
        "owner",
        "created_at",
    )
    list_filter = (
        "status",
        "priority",
        "lead_source",
        "is_converted",
        "organization",
    )
    search_fields = (
        "first_name",
        "last_name",
        "company_name",
        "email",
        "phone",
    )
    readonly_fields = ("id", "lead_score", "score_breakdown", "is_converted", "converted_at", "created_at", "updated_at")

