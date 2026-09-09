"""
EnterpriseOne Sales URL Configuration.
"""
from django.urls import path
from . import views

app_name = "sales"

urlpatterns = [
    # Products
    path("products/", views.ProductListView.as_view(), name="product_list"),
    path("products/create/", views.ProductCreateView.as_view(), name="product_create"),
    path("products/<uuid:pk>/", views.ProductDetailView.as_view(), name="product_detail"),
    path("products/<uuid:pk>/edit/", views.ProductUpdateView.as_view(), name="product_edit"),
    path("products/<uuid:pk>/delete/", views.ProductDeleteView.as_view(), name="product_delete"),

    # Price Books
    path("price-books/", views.PriceBookListView.as_view(), name="pricebook_list"),
    path("price-books/create/", views.PriceBookCreateView.as_view(), name="pricebook_create"),
    path("price-books/<uuid:pk>/", views.PriceBookDetailView.as_view(), name="pricebook_detail"),
    path("price-books/<uuid:pk>/edit/", views.PriceBookUpdateView.as_view(), name="pricebook_edit"),
    path("price-books/<uuid:pk>/delete/", views.PriceBookDeleteView.as_view(), name="pricebook_delete"),
    path("price-books/<uuid:pk>/add-entry/", views.PriceBookEntryCreateView.as_view(), name="pricebook_entry_create"),
    path("price-books/entries/<uuid:pk>/delete/", views.PriceBookEntryDeleteView.as_view(), name="pricebook_entry_delete"),
    # Quotes & Workflow
    path("quotes/", views.QuoteListView.as_view(), name="quote_list"),
    path("quotes/create/", views.QuoteCreateView.as_view(), name="quote_create"),
    path("quotes/<uuid:pk>/", views.QuoteDetailView.as_view(), name="quote_detail"),
    path("quotes/<uuid:pk>/edit/", views.QuoteUpdateView.as_view(), name="quote_edit"),
    path("quotes/<uuid:pk>/delete/", views.QuoteDeleteView.as_view(), name="quote_delete"),
    path("quotes/<uuid:pk>/add-line/", views.QuoteLineItemCreateView.as_view(), name="quote_line_create"),
    path("quotes/lines/<uuid:pk>/delete/", views.QuoteLineItemDeleteView.as_view(), name="quote_line_delete"),
    path("quotes/<uuid:pk>/submit-approval/", views.QuoteSubmitApprovalView.as_view(), name="quote_submit_approval"),
    path("quotes/<uuid:pk>/approve/", views.QuoteApproveView.as_view(), name="quote_approve"),
    path("quotes/<uuid:pk>/reject/", views.QuoteRejectView.as_view(), name="quote_reject"),
    path("quotes/<uuid:pk>/present/", views.QuotePresentView.as_view(), name="quote_present"),
    path("quotes/<uuid:pk>/accept/", views.QuoteAcceptView.as_view(), name="quote_accept"),
]
