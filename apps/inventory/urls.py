"""
EnterpriseOne Inventory URL Configuration.
"""
from django.urls import path
from . import views

app_name = "inventory"

urlpatterns = [
    # Executive Inventory Command Center
    path("", views.InventoryDashboardView.as_view(), name="index"),
    path("dashboard/", views.InventoryDashboardView.as_view(), name="dashboard"),

    # Warehouses
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

    # Stock Movements & Goods Receipts
    path("movements/", views.StockMovementListView.as_view(), name="movement_list"),
    path("movements/create/", views.StockMovementCreateView.as_view(), name="movement_create"),
    path("movements/<uuid:pk>/", views.StockMovementDetailView.as_view(), name="movement_detail"),
    path("movements/<uuid:pk>/post/", views.StockMovementPostView.as_view(), name="movement_post"),
    path("movements/<uuid:pk>/cancel/", views.StockMovementCancelView.as_view(), name="movement_cancel"),
    path("movements/<uuid:pk>/print/", views.StockMovementPrintView.as_view(), name="movement_print"),

    # Stock Movement Ledger / Audit
    path("ledger/", views.StockLedgerView.as_view(), name="stock_ledger"),

    # Lots & Batch Tracking (Milestone 5.3)
    path("lots/", views.LotBatchListView.as_view(), name="lot_list"),
    path("lots/create/", views.LotBatchCreateView.as_view(), name="lot_create"),
    path("lots/<uuid:pk>/", views.LotBatchDetailView.as_view(), name="lot_detail"),
    path("lots/<uuid:pk>/qc/", views.LotBatchQCUpdateView.as_view(), name="lot_qc_update"),

    # Serial Number Serialization
    path("serials/", views.SerialNumberListView.as_view(), name="serial_list"),
    path("serials/create/", views.SerialNumberBulkCreateView.as_view(), name="serial_bulk_create"),
    path("serials/<uuid:pk>/", views.SerialNumberDetailView.as_view(), name="serial_detail"),

    # Expiry & FEFO Reporting
    path("expiring-stock/", views.ExpiringStockReportView.as_view(), name="expiring_stock"),

    # Automated Reorder Policies (Milestone 5.4)
    path("reorder-rules/", views.ReorderRuleListView.as_view(), name="reorder_rule_list"),
    path("reorder-rules/create/", views.ReorderRuleCreateView.as_view(), name="reorder_rule_create"),
    path("reorder-rules/<uuid:pk>/edit/", views.ReorderRuleUpdateView.as_view(), name="reorder_rule_edit"),

    # Automated Replenishment Evaluation Trigger
    path("replenishment/scan/", views.ReplenishmentScanTriggerView.as_view(), name="replenishment_scan"),

    # Purchase Replenishment Requisitions
    path("requisitions/", views.PurchaseRequisitionListView.as_view(), name="requisition_list"),
    path("requisitions/create/", views.PurchaseRequisitionCreateView.as_view(), name="requisition_create"),
    path("requisitions/<uuid:pk>/", views.PurchaseRequisitionDetailView.as_view(), name="requisition_detail"),
    path("requisitions/<uuid:pk>/approve/", views.PurchaseRequisitionApproveView.as_view(), name="requisition_approve"),
    path("requisitions/<uuid:pk>/cancel/", views.PurchaseRequisitionCancelView.as_view(), name="requisition_cancel"),
]
