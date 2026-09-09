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
    path("price-books/entries/<uuid:entry_pk>/add-tier/", views.TieredDiscountCreateView.as_view(), name="tiered_discount_create"),
]
