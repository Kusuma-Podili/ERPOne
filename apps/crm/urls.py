"""
Enterprise CRM URL Configuration.
"""
from django.urls import path
from django.views.generic import RedirectView
from apps.crm import views

app_name = "crm"

urlpatterns = [
    # Default CRM Dashboard
    path("", views.CRMDashboardView.as_view(), name="dashboard"),

    # Accounts
    path("accounts/", views.AccountListView.as_view(), name="account_list"),
    path("accounts/new/", views.AccountCreateView.as_view(), name="account_create"),
    path("accounts/<uuid:pk>/", views.AccountDetailView.as_view(), name="account_detail"),
    path("accounts/<uuid:pk>/edit/", views.AccountUpdateView.as_view(), name="account_update"),
    path("accounts/<uuid:pk>/delete/", views.AccountDeleteView.as_view(), name="account_delete"),

    # Contacts
    path("contacts/", views.ContactListView.as_view(), name="contact_list"),
    path("contacts/new/", views.ContactCreateView.as_view(), name="contact_create"),
    path("contacts/<uuid:pk>/", views.ContactDetailView.as_view(), name="contact_detail"),
    path("contacts/<uuid:pk>/edit/", views.ContactUpdateView.as_view(), name="contact_update"),
    path("contacts/<uuid:pk>/delete/", views.ContactDeleteView.as_view(), name="contact_delete"),

    # Leads
    path("leads/", views.LeadListView.as_view(), name="lead_list"),
    path("leads/new/", views.LeadCreateView.as_view(), name="lead_create"),
    path("leads/<uuid:pk>/", views.LeadDetailView.as_view(), name="lead_detail"),
    path("leads/<uuid:pk>/edit/", views.LeadUpdateView.as_view(), name="lead_update"),
    path("leads/<uuid:pk>/delete/", views.LeadDeleteView.as_view(), name="lead_delete"),
    path("leads/<uuid:pk>/convert/", views.LeadConvertView.as_view(), name="lead_convert"),
    path("leads/<uuid:pk>/recalculate-score/", views.LeadRecalculateScoreView.as_view(), name="lead_recalculate_score"),

    # Deals & Sales Pipeline
    path("deals/", views.DealListView.as_view(), name="deal_list"),
    path("deals/kanban/", views.DealKanbanView.as_view(), name="deal_kanban"),
    path("deals/new/", views.DealCreateView.as_view(), name="deal_create"),
    path("deals/<uuid:pk>/", views.DealDetailView.as_view(), name="deal_detail"),
    path("deals/<uuid:pk>/edit/", views.DealUpdateView.as_view(), name="deal_update"),
    path("deals/<uuid:pk>/delete/", views.DealDeleteView.as_view(), name="deal_delete"),
    path("deals/<uuid:pk>/transition/", views.DealTransitionStageView.as_view(), name="deal_transition_stage"),

    # Activities & Tasks
    path("activities/", views.ActivityListView.as_view(), name="activity_list"),
    path("activities/new/", views.ActivityCreateView.as_view(), name="activity_create"),
    path("activities/<uuid:pk>/edit/", views.ActivityUpdateView.as_view(), name="activity_update"),
    path("activities/<uuid:pk>/complete/", views.ActivityCompleteView.as_view(), name="activity_complete"),
    path("activities/<uuid:pk>/delete/", views.ActivityDeleteView.as_view(), name="activity_delete"),
]
