"""
EnterpriseOne Procurement URL Configuration (Milestone 6.1).
"""
from django.urls import path
from . import views

app_name = "procurement"

urlpatterns = [
    # Dashboard & Sourcing Overview
    path("", views.ProcurementDashboardView.as_view(), name="index"),
    path("dashboard/", views.ProcurementDashboardView.as_view(), name="dashboard"),

    # Suppliers Master
    path("suppliers/", views.SupplierListView.as_view(), name="supplier_list"),
    path("suppliers/create/", views.SupplierCreateView.as_view(), name="supplier_create"),
    path("suppliers/<uuid:pk>/", views.SupplierDetailView.as_view(), name="supplier_detail"),
    path("suppliers/<uuid:pk>/edit/", views.SupplierUpdateView.as_view(), name="supplier_edit"),
    path("suppliers/<uuid:pk>/delete/", views.SupplierDeleteView.as_view(), name="supplier_delete"),

    # Supplier Contacts
    path("suppliers/<uuid:supplier_pk>/contacts/create/", views.SupplierContactCreateView.as_view(), name="supplier_contact_create"),

    # Supplier Catalog Products
    path("suppliers/<uuid:supplier_pk>/products/create/", views.SupplierProductCreateView.as_view(), name="supplier_product_create"),

    # Requests for Quotation (RFQ)
    path("rfqs/", views.RFQListView.as_view(), name="rfq_list"),
    path("rfqs/create/", views.RFQCreateView.as_view(), name="rfq_create"),
    path("rfqs/<uuid:pk>/", views.RFQDetailView.as_view(), name="rfq_detail"),
    path("rfqs/<uuid:pk>/edit/", views.RFQUpdateView.as_view(), name="rfq_edit"),
    path("rfqs/<uuid:pk>/publish/", views.RFQPublishView.as_view(), name="rfq_publish"),
    path("rfqs/<uuid:pk>/invite/", views.RFQInviteView.as_view(), name="rfq_invite"),
    path("rfqs/<uuid:rfq_pk>/bids/create/", views.VendorBidCreateView.as_view(), name="vendor_bid_create"),
    path("rfqs/<uuid:pk>/compare/", views.RFQBidComparisonView.as_view(), name="rfq_comparison"),
    path("rfqs/<uuid:pk>/award/", views.RFQAwardBidView.as_view(), name="rfq_award"),
    path("rfqs/<uuid:pk>/print/", views.RFQPrintView.as_view(), name="rfq_print"),
    path("rfqs/<uuid:pk>/convert-po/", views.ConvertRFQToPOView.as_view(), name="rfq_convert_po"),

    # Purchase Orders (PO)
    path("orders/", views.POListView.as_view(), name="po_list"),
    path("orders/create/", views.POCreateView.as_view(), name="po_create"),
    path("orders/<uuid:pk>/", views.PODetailView.as_view(), name="po_detail"),
    path("orders/<uuid:pk>/edit/", views.POUpdateView.as_view(), name="po_edit"),
    path("orders/<uuid:pk>/submit-approval/", views.POSubmitApprovalView.as_view(), name="po_submit_approval"),
    path("orders/<uuid:pk>/approve/", views.POApproveView.as_view(), name="po_approve"),
    path("orders/<uuid:pk>/reject/", views.PORejectView.as_view(), name="po_reject"),
    path("orders/<uuid:pk>/issue/", views.POIssueView.as_view(), name="po_issue"),
    path("orders/<uuid:pk>/print/", views.POPrintView.as_view(), name="po_print"),

    # Vendor Bills & Three-Way Matching
    path("bills/", views.VendorBillListView.as_view(), name="bill_list"),
    path("bills/create/", views.VendorBillCreateView.as_view(), name="bill_create"),
    path("bills/<uuid:pk>/", views.VendorBillDetailView.as_view(), name="bill_detail"),
    path("bills/<uuid:bill_pk>/match/", views.ThreeWayMatchExecuteView.as_view(), name="bill_match"),
    path("matches/<uuid:pk>/", views.ThreeWayMatchDetailView.as_view(), name="match_detail"),
    path("matches/<uuid:pk>/resolve/", views.ThreeWayMatchResolveView.as_view(), name="match_resolve"),
]
