"""
EnterpriseOne Inventory URL Configuration.
"""
from django.urls import path
from . import views

app_name = "inventory"

urlpatterns = [
    # Warehouses
    path("", views.WarehouseListView.as_view(), name="index"),
    path("warehouses/", views.WarehouseListView.as_view(), name="warehouse_list"),
    path("warehouses/create/", views.WarehouseCreateView.as_view(), name="warehouse_create"),
    path("warehouses/<uuid:pk>/", views.WarehouseDetailView.as_view(), name="warehouse_detail"),
    path("warehouses/<uuid:pk>/edit/", views.WarehouseUpdateView.as_view(), name="warehouse_edit"),
    path("warehouses/<uuid:pk>/delete/", views.WarehouseDeleteView.as_view(), name="warehouse_delete"),

    # Storage Zones & Locations
    path("zones/create/", views.StorageZoneCreateView.as_view(), name="zone_create"),
    path("zones/<uuid:pk>/delete/", views.StorageZoneDeleteView.as_view(), name="zone_delete"),
    path("locations/create/", views.StorageLocationCreateView.as_view(), name="location_create"),
    path("locations/<uuid:pk>/delete/", views.StorageLocationDeleteView.as_view(), name="location_delete"),

    # Stock Items / Inventory Levels
    path("stock/", views.StockItemListView.as_view(), name="stock_list"),
    path("stock/create/", views.StockItemCreateView.as_view(), name="stock_create"),
    path("stock/<uuid:pk>/", views.StockItemDetailView.as_view(), name="stock_detail"),
    path("stock/<uuid:pk>/edit/", views.StockItemUpdateView.as_view(), name="stock_edit"),
]
