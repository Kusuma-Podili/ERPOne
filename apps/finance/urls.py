"""
EnterpriseOne Finance & General Ledger URLs (Milestone 7.1).
"""
from django.urls import path
from django.views.generic import RedirectView
from apps.finance import views

app_name = "finance"

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="finance:dashboard", permanent=False), name="index"),
    path("dashboard/", views.FinanceDashboardView.as_view(), name="dashboard"),
    
    # Chart of Accounts
    path("accounts/", views.GLAccountListView.as_view(), name="account_list"),
    path("accounts/create/", views.GLAccountCreateView.as_view(), name="account_create"),
    path("accounts/provision-standard/", views.GLAccountProvisionStandardView.as_view(), name="account_provision_standard"),
    path("accounts/<uuid:pk>/", views.GLAccountDetailView.as_view(), name="account_detail"),
    path("accounts/<uuid:pk>/update/", views.GLAccountUpdateView.as_view(), name="account_update"),
    
    # Fiscal Calendars
    path("fiscal-years/", views.FiscalYearListView.as_view(), name="fiscal_year_list"),
    path("fiscal-years/create/", views.FiscalYearCreateView.as_view(), name="fiscal_year_create"),
    path("fiscal-periods/<uuid:pk>/toggle-close/", views.FiscalPeriodToggleCloseView.as_view(), name="fiscal_period_toggle_close"),
    
    # Double-Entry Journal Entries
    path("journal-entries/", views.JournalEntryListView.as_view(), name="journal_entry_list"),
    path("journal-entries/create/", views.JournalEntryCreateView.as_view(), name="journal_entry_create"),
    path("journal-entries/<uuid:pk>/", views.JournalEntryDetailView.as_view(), name="journal_entry_detail"),
    path("journal-entries/<uuid:pk>/post/", views.JournalEntryPostView.as_view(), name="journal_entry_post"),
    path("journal-entries/<uuid:pk>/reverse/", views.JournalEntryReverseView.as_view(), name="journal_entry_reverse"),
    path("journal-entries/<uuid:pk>/print/", views.JournalEntryPrintView.as_view(), name="journal_entry_print"),
]
