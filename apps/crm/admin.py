from django.contrib import admin
from apps.crm.models import (
    Account,
    Contact,
    Lead,
    PipelineStage,
    Deal,
    DealStageTransition,
    Activity,
    Note,
)


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


@admin.register(PipelineStage)
class PipelineStageAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "organization", "order", "default_probability", "is_won_stage", "is_lost_stage", "is_active")
    list_filter = ("is_won_stage", "is_lost_stage", "is_active", "organization")
    search_fields = ("name", "code")


class DealStageTransitionInline(admin.TabularInline):
    model = DealStageTransition
    extra = 0
    readonly_fields = ("from_stage", "to_stage", "changed_by", "transition_notes", "duration_in_previous_stage_seconds", "created_at")
    can_delete = False


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "deal_number",
        "account",
        "stage",
        "amount",
        "probability",
        "is_closed",
        "is_won",
        "expected_close_date",
        "owner",
    )
    list_filter = (
        "stage",
        "is_closed",
        "is_won",
        "organization",
    )
    search_fields = (
        "name",
        "deal_number",
        "account__name",
        "primary_contact__first_name",
        "primary_contact__last_name",
    )
    readonly_fields = ("id", "deal_number", "created_at", "updated_at")
    inlines = [DealStageTransitionInline]


@admin.register(DealStageTransition)
class DealStageTransitionAdmin(admin.ModelAdmin):
    list_display = ("deal", "from_stage", "to_stage", "changed_by", "duration_in_previous_stage_seconds", "created_at")
    list_filter = ("to_stage", "organization")
    readonly_fields = ("id", "deal", "from_stage", "to_stage", "changed_by", "transition_notes", "duration_in_previous_stage_seconds", "created_at")


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = (
        "subject",
        "activity_type",
        "status",
        "priority",
        "due_date",
        "account",
        "deal",
        "assigned_to",
        "organization",
    )
    list_filter = (
        "activity_type",
        "status",
        "priority",
        "organization",
    )
    search_fields = (
        "subject",
        "description",
        "account__name",
        "deal__name",
    )
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ("title", "account", "deal", "contact", "created_by", "created_at")
    search_fields = ("title", "content", "account__name", "deal__name")
    readonly_fields = ("id", "created_at", "updated_at")



