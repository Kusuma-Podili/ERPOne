"""
Enterprise CRM URL Configuration.
"""
from django.urls import path
from django.views.generic import RedirectView
from apps.crm import views

app_name = "crm"

urlpatterns = [
    # Default CRM Entrypoint
    path("", RedirectView.as_view(pattern_name="crm:account_list", permanent=False), name="crm_index"),

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
]
