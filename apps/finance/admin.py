"""
EnterpriseOne Finance Django Admin Registration.
"""
from django.contrib import admin
from apps.finance.models import (
    FiscalYear,
    FiscalPeriod,
    GLAccount,
    JournalEntry,
    JournalEntryLine,
)


@admin.register(FiscalYear)
class FiscalYearAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "organization", "start_date", "end_date", "is_closed"]
    list_filter = ["is_closed", "organization"]
    search_fields = ["code", "name"]


@admin.register(FiscalPeriod)
class FiscalPeriodAdmin(admin.ModelAdmin):
    list_display = ["name", "fiscal_year", "period_number", "organization", "start_date", "end_date", "is_closed"]
    list_filter = ["is_closed", "fiscal_year"]
    search_fields = ["name"]


@admin.register(GLAccount)
class GLAccountAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "organization", "category", "subtype", "normal_balance", "current_balance", "is_active", "allow_direct_posting"]
    list_filter = ["category", "subtype", "normal_balance", "is_active", "organization"]
    search_fields = ["code", "name"]


class JournalEntryLineInline(admin.TabularInline):
    model = JournalEntryLine
    extra = 0
    fields = ["line_number", "account", "debit", "credit", "narration", "partner_name", "cost_center"]


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ["entry_number", "organization", "entry_date", "fiscal_period", "status", "total_debit", "total_credit", "is_balanced"]
    list_filter = ["status", "fiscal_period", "organization"]
    search_fields = ["entry_number", "reference", "narration"]
    inlines = [JournalEntryLineInline]
