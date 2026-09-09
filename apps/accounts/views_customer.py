"""
Customer Portal Domain Views.
Provides customer self-service portal: Dashboard, Orders, Invoices, Support Tickets, and Documents.
Enforces strict object-level isolation preventing cross-customer data access.
"""
from django import forms
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import models
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView, ListView, DetailView

from apps.accounts.permissions import CustomerRequiredMixin, is_admin
from apps.crm.models import Contact, Account
from apps.sales.models import SalesOrder
from apps.support.models import SupportTicket, SupportCategory, SupportTeam, TicketStatus, TicketPriority


def get_customer_context(user):
    """Helper to resolve linked CRM Contact and Account for the authenticated user."""
    contact = getattr(user, "crm_contact", None)
    if not contact:
        contact = Contact.objects.filter(email__iexact=user.email).first()
        if contact and not contact.user:
            contact.user = user
            contact.save(update_fields=["user"])
    account = contact.account if contact else None
    return contact, account


class CustomerDashboardView(CustomerRequiredMixin, TemplateView):
    """
    Customer self-service portal overview.
    """
    template_name = "customer/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        contact, account = get_customer_context(user)
        context["contact"] = contact
        context["account"] = account

        # Isolated Orders
        if account or contact:
            q = models.Q()
            if account:
                q |= models.Q(account=account)
            if contact:
                q |= models.Q(contact=contact)
            orders_qs = SalesOrder.objects.filter(q).order_by("-created_at")
            context["recent_orders"] = orders_qs[:5]
            context["total_orders_count"] = orders_qs.count()
        else:
            context["recent_orders"] = []
            context["total_orders_count"] = 0

        # Isolated Support Tickets
        tq = models.Q(requester=user)
        if account:
            tq |= models.Q(customer=account)
        tickets_qs = SupportTicket.objects.filter(tq).order_by("-created_at")
        context["recent_tickets"] = tickets_qs[:5]
        context["open_tickets_count"] = tickets_qs.exclude(status__in=["resolved", "closed", "RESOLVED", "CLOSED"]).count()

        # Isolated Documents
        try:
            from apps.documents.models import Document
            context["recent_documents"] = Document.objects.filter(
                models.Q(owner=user)
                | models.Q(shares__recipient_email=user.email)
                | models.Q(visibility="shared")
            ).distinct().order_by("-created_at")[:5]
        except Exception:
            context["recent_documents"] = []

        return context


class CustomerOrderListView(CustomerRequiredMixin, ListView):
    """
    List of orders belonging strictly to the authenticated customer.
    """
    template_name = "customer/order_list.html"
    context_object_name = "orders"
    paginate_by = 15

    def get_queryset(self):
        contact, account = get_customer_context(self.request.user)
        if not account and not contact:
            return SalesOrder.objects.none()
        q = models.Q()
        if account:
            q |= models.Q(account=account)
        if contact:
            q |= models.Q(contact=contact)
        return SalesOrder.objects.filter(q).select_related("account", "contact").order_by("-created_at")


class CustomerOrderDetailView(CustomerRequiredMixin, DetailView):
    """
    Detailed view of a sales order with strict object-level ownership check.
    """
    template_name = "customer/order_detail.html"
    model = SalesOrder
    context_object_name = "order"

    def get_object(self, queryset=None):
        order = super().get_object(queryset)
        # Superusers and Admins can view any order
        if is_admin(self.request.user):
            return order
        contact, account = get_customer_context(self.request.user)
        # Object-level security enforcement
        is_owner = False
        if account and order.account_id == account.id:
            is_owner = True
        if contact and order.contact_id == contact.id:
            is_owner = True
        if not is_owner:
            raise PermissionDenied("Forbidden: You do not possess ownership access to this commercial order.")
        return order


class CustomerTicketListView(CustomerRequiredMixin, ListView):
    """
    List of support tickets submitted by or associated with this customer.
    """
    template_name = "customer/ticket_list.html"
    context_object_name = "tickets"
    paginate_by = 15

    def get_queryset(self):
        contact, account = get_customer_context(self.request.user)
        tq = models.Q(requester=self.request.user)
        if account:
            tq |= models.Q(customer=account)
        return SupportTicket.objects.filter(tq).select_related("category", "customer").order_by("-created_at")


class CustomerTicketCreateForm(forms.ModelForm):
    class Meta:
        model = SupportTicket
        fields = ["subject", "description", "priority", "category"]
        widgets = {
            "subject": forms.TextInput(attrs={"class": "form-control enterprise-input", "placeholder": "Brief description of the issue"}),
            "description": forms.Textarea(attrs={"class": "form-control enterprise-input", "rows": 4, "placeholder": "Detailed information about your request..."}),
            "priority": forms.Select(attrs={"class": "form-select enterprise-input"}),
            "category": forms.Select(attrs={"class": "form-select enterprise-input"}),
        }


class CustomerTicketCreateView(CustomerRequiredMixin, View):
    """
    Self-service support ticket submission for customer clients.
    """
    template_name = "customer/ticket_create.html"

    def get(self, request):
        form = CustomerTicketCreateForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = CustomerTicketCreateForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            contact, account = get_customer_context(request.user)
            org = getattr(request, "organization", None)
            if not org and account:
                org = account.organization
            if not org:
                from apps.organizations.models import Organization
                org = Organization.objects.first()
            ticket.organization = org
            ticket.requester = request.user
            ticket.created_by = request.user
            ticket.customer = account
            ticket.source = "PORTAL"
            team = SupportTeam.objects.filter(organization=org).first()
            if team:
                ticket.team = team
            ticket.save()
            messages.success(request, f"Support ticket #{ticket.number} submitted successfully.")
            return redirect("customer:ticket_detail", pk=ticket.pk)
        return render(request, self.template_name, {"form": form})


class CustomerTicketDetailView(CustomerRequiredMixin, DetailView):
    """
    Ticket detail view with strict object ownership validation and message reply.
    """
    template_name = "customer/ticket_detail.html"
    model = SupportTicket
    context_object_name = "ticket"

    def get_object(self, queryset=None):
        ticket = super().get_object(queryset)
        if is_admin(self.request.user):
            return ticket
        contact, account = get_customer_context(self.request.user)
        is_owner = False
        if ticket.requester_id == self.request.user.id or ticket.created_by_id == self.request.user.id:
            is_owner = True
        if account and ticket.customer_id == account.id:
            is_owner = True
        if not is_owner:
            raise PermissionDenied("Forbidden: You do not possess authorization to view this support ticket.")
        return ticket

    def post(self, request, *args, **kwargs):
        ticket = self.get_object()
        message_body = request.POST.get("body", "").strip()
        if message_body:
            try:
                from apps.support.models import TicketMessage
                TicketMessage.objects.create(
                    ticket=ticket,
                    author=request.user,
                    body=message_body,
                    is_internal=False,
                )
                messages.success(request, "Your reply has been sent.")
            except Exception:
                pass
        return redirect("customer:ticket_detail", pk=ticket.pk)


class CustomerDocumentListView(CustomerRequiredMixin, ListView):
    """
    Documents repository visible to this customer.
    """
    template_name = "customer/document_list.html"
    context_object_name = "documents"
    paginate_by = 15

    def get_queryset(self):
        try:
            from apps.documents.models import Document
            return Document.objects.filter(
                models.Q(owner=self.request.user)
                | models.Q(shares__recipient_email=self.request.user.email)
                | models.Q(visibility="shared")
            ).distinct().order_by("-created_at")
        except Exception:
            return []
