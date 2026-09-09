"""
Customer Portal URL Routing.
Endpoints for customer dashboard, orders, invoices, support tickets, and shared documents.
"""
from django.urls import path
from apps.accounts.views_customer import (
    CustomerDashboardView,
    CustomerOrderListView,
    CustomerOrderDetailView,
    CustomerTicketListView,
    CustomerTicketCreateView,
    CustomerTicketDetailView,
    CustomerDocumentListView,
)
from apps.accounts.views import UserProfileView

app_name = "customer"

urlpatterns = [
    path("", CustomerDashboardView.as_view(), name="dashboard"),
    path("orders/", CustomerOrderListView.as_view(), name="order_list"),
    path("orders/<uuid:pk>/", CustomerOrderDetailView.as_view(), name="order_detail"),
    path("tickets/", CustomerTicketListView.as_view(), name="ticket_list"),
    path("tickets/create/", CustomerTicketCreateView.as_view(), name="ticket_create"),
    path("tickets/<uuid:pk>/", CustomerTicketDetailView.as_view(), name="ticket_detail"),
    path("documents/", CustomerDocumentListView.as_view(), name="document_list"),
    path("profile/", UserProfileView.as_view(), name="profile"),
]
