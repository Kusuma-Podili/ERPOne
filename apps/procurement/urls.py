"""
EnterpriseOne Procurement URL Configuration (Milestone 6.1).
"""
from django.urls import path
from . import views

app_name = "procurement"

urlpatterns = [
    # Suppliers Master
    path("", views.SupplierListView.as_view(), name="index"),
    path("suppliers/", views.SupplierListView.as_view(), name="supplier_list"),
    path("suppliers/create/", views.SupplierCreateView.as_view(), name="supplier_create"),
    path("suppliers/<uuid:pk>/", views.SupplierDetailView.as_view(), name="supplier_detail"),
    path("suppliers/<uuid:pk>/edit/", views.SupplierUpdateView.as_view(), name="supplier_edit"),
    path("suppliers/<uuid:pk>/delete/", views.SupplierDeleteView.as_view(), name="supplier_delete"),

    # Supplier Contacts
    path("suppliers/<uuid:supplier_pk>/contacts/create/", views.SupplierContactCreateView.as_view(), name="supplier_contact_create"),

    # Supplier Catalog Products
    path("suppliers/<uuid:supplier_pk>/products/create/", views.SupplierProductCreateView.as_view(), name="supplier_product_create"),
]
