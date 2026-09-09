"""
Enterprise CRM Views.
Handles accounts, customer directory, contacts, and relationship management.
"""
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views import View
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
    TemplateView,
)

from apps.organizations.views import OrganizationAccessMixin
from apps.crm.models import (
    Account,
    Contact,
    AccountType,
    IndustryChoice,
    LifecycleStage,
    AccountStatus,
)
from apps.crm.forms import AccountForm, ContactForm


# =====================================================================
# ACCOUNT VIEWS
# =====================================================================

class AccountListView(OrganizationAccessMixin, ListView):
    """
    Paginated list of all corporate accounts for the active organization.
    Supports full-text filtering by name, account number, email, and industry.
    """
    model = Account
    template_name = "crm/account_list.html"
    context_object_name = "accounts"
    paginate_by = 20

    def get_queryset(self):
        qs = Account.objects.filter(
            organization=self.request.organization
        ).select_related("owner", "created_by")

        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(account_number__icontains=q)
                | Q(email__icontains=q)
                | Q(phone__icontains=q)
                | Q(website__icontains=q)
            )

        account_type = self.request.GET.get("type", "").strip()
        if account_type:
            qs = qs.filter(account_type=account_type)

        industry = self.request.GET.get("industry", "").strip()
        if industry:
            qs = qs.filter(industry=industry)

        lifecycle = self.request.GET.get("lifecycle", "").strip()
        if lifecycle:
            qs = qs.filter(lifecycle_stage=lifecycle)

        status = self.request.GET.get("status", "").strip()
        if status:
            qs = qs.filter(status=status)

        sort = self.request.GET.get("sort", "-created_at")
        allowed_sorts = ["name", "-name", "annual_revenue", "-annual_revenue", "created_at", "-created_at"]
        if sort in allowed_sorts:
            qs = qs.order_by(sort)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        org = self.request.organization
        ctx["total_accounts_count"] = Account.objects.filter(organization=org).count()
        ctx["customer_accounts_count"] = Account.objects.filter(
            organization=org, account_type=AccountType.CUSTOMER
        ).count()
        ctx["active_accounts_count"] = Account.objects.filter(
            organization=org, status=AccountStatus.ACTIVE
        ).count()
        ctx["account_types"] = AccountType.choices
        ctx["industries"] = IndustryChoice.choices
        ctx["lifecycle_stages"] = LifecycleStage.choices
        ctx["account_statuses"] = AccountStatus.choices
        ctx["current_q"] = self.request.GET.get("q", "")
        ctx["current_type"] = self.request.GET.get("type", "")
        ctx["current_industry"] = self.request.GET.get("industry", "")
        ctx["current_lifecycle"] = self.request.GET.get("lifecycle", "")
        ctx["current_status"] = self.request.GET.get("status", "")
        ctx["current_sort"] = self.request.GET.get("sort", "-created_at")
        return ctx


class AccountDetailView(OrganizationAccessMixin, DetailView):
    """
    Detailed profile view for a customer account.
    Displays company demographics, contacts roster, deals, and interactions.
    """
    model = Account
    template_name = "crm/account_detail.html"
    context_object_name = "account"

    def get_queryset(self):
        return Account.objects.filter(
            organization=self.request.organization
        ).select_related("owner", "created_by")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        account = self.get_object()
        ctx["contacts"] = account.contacts.all().order_by("-is_primary_contact", "last_name")
        if hasattr(account, "deals"):
            ctx["deals"] = account.deals.select_related("stage", "owner").order_by("-created_at")
        else:
            ctx["deals"] = []
        if hasattr(account, "activities"):
            ctx["activities"] = account.activities.select_related("assigned_to").order_by("-due_date")[:10]
        else:
            ctx["activities"] = []
        return ctx


class AccountCreateView(OrganizationAccessMixin, CreateView):
    """
    Registers a new corporate account under the active organization.
    """
    model = Account
    form_class = AccountForm
    template_name = "crm/account_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.request.organization
        return kwargs

    def form_valid(self, form):
        form.instance.organization = self.request.organization
        form.instance.created_by = self.request.user
        if not form.instance.owner:
            form.instance.owner = self.request.user
        messages.success(self.request, f"Account '{form.instance.name}' successfully created.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("crm:account_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form_title"] = "Create New Account"
        ctx["form_action"] = "Create"
        return ctx


class AccountUpdateView(OrganizationAccessMixin, UpdateView):
    """
    Modifies an existing corporate account profile.
    """
    model = Account
    form_class = AccountForm
    template_name = "crm/account_form.html"

    def get_queryset(self):
        return Account.objects.filter(organization=self.request.organization)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.request.organization
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, f"Account '{form.instance.name}' has been updated.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("crm:account_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form_title"] = f"Edit Account: {self.object.name}"
        ctx["form_action"] = "Save Changes"
        ctx["account"] = self.object
        return ctx


class AccountDeleteView(OrganizationAccessMixin, DeleteView):
    """
    Archives or removes an account from the organization.
    """
    model = Account
    template_name = "crm/account_confirm_delete.html"
    success_url = reverse_lazy("crm:account_list")

    def get_queryset(self):
        return Account.objects.filter(organization=self.request.organization)

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        name = obj.name
        messages.warning(request, f"Account '{name}' and its related records were deleted.")
        return super().delete(request, *args, **kwargs)


# =====================================================================
# CONTACT VIEWS
# =====================================================================

class ContactListView(OrganizationAccessMixin, ListView):
    """
    Directory of individual contacts across all corporate accounts.
    """
    model = Contact
    template_name = "crm/contact_list.html"
    context_object_name = "contacts"
    paginate_by = 25

    def get_queryset(self):
        qs = Contact.objects.filter(
            organization=self.request.organization
        ).select_related("account", "owner")

        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(email__icontains=q)
                | Q(phone__icontains=q)
                | Q(job_title__icontains=q)
                | Q(account__name__icontains=q)
            )

        account_id = self.request.GET.get("account", "").strip()
        if account_id:
            qs = qs.filter(account_id=account_id)

        lifecycle = self.request.GET.get("lifecycle", "").strip()
        if lifecycle:
            qs = qs.filter(lifecycle_stage=lifecycle)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        org = self.request.organization
        ctx["total_contacts_count"] = Contact.objects.filter(organization=org).count()
        ctx["primary_contacts_count"] = Contact.objects.filter(
            organization=org, is_primary_contact=True
        ).count()
        ctx["accounts"] = Account.objects.filter(organization=org).order_by("name")
        ctx["lifecycle_stages"] = LifecycleStage.choices
        ctx["current_q"] = self.request.GET.get("q", "")
        ctx["current_account"] = self.request.GET.get("account", "")
        ctx["current_lifecycle"] = self.request.GET.get("lifecycle", "")
        return ctx


class ContactDetailView(OrganizationAccessMixin, DetailView):
    """
    Individual contact dossier and history.
    """
    model = Contact
    template_name = "crm/contact_detail.html"
    context_object_name = "contact"

    def get_queryset(self):
        return Contact.objects.filter(
            organization=self.request.organization
        ).select_related("account", "owner", "created_by")


class ContactCreateView(OrganizationAccessMixin, CreateView):
    """
    Adds a new contact to an account or as a standalone contact.
    """
    model = Contact
    form_class = ContactForm
    template_name = "crm/contact_form.html"

    def get_initial(self):
        initial = super().get_initial()
        account_id = self.request.GET.get("account")
        if account_id:
            initial["account"] = account_id
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.request.organization
        return kwargs

    def form_valid(self, form):
        form.instance.organization = self.request.organization
        form.instance.created_by = self.request.user
        if not form.instance.owner:
            form.instance.owner = self.request.user
        messages.success(self.request, f"Contact '{form.instance.full_name}' successfully added.")
        return super().form_valid(form)

    def get_success_url(self):
        if self.object.account_id:
            return reverse("crm:account_detail", kwargs={"pk": self.object.account_id})
        return reverse("crm:contact_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form_title"] = "Create New Contact"
        ctx["form_action"] = "Create Contact"
        return ctx


class ContactUpdateView(OrganizationAccessMixin, UpdateView):
    """
    Updates an existing contact record.
    """
    model = Contact
    form_class = ContactForm
    template_name = "crm/contact_form.html"

    def get_queryset(self):
        return Contact.objects.filter(organization=self.request.organization)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.request.organization
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, f"Contact '{form.instance.full_name}' updated.")
        return super().form_valid(form)

    def get_success_url(self):
        if self.object.account_id:
            return reverse("crm:account_detail", kwargs={"pk": self.object.account_id})
        return reverse("crm:contact_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form_title"] = f"Edit Contact: {self.object.full_name}"
        ctx["form_action"] = "Save Changes"
        ctx["contact"] = self.object
        return ctx


class ContactDeleteView(OrganizationAccessMixin, DeleteView):
    """
    Removes a contact record.
    """
    model = Contact
    template_name = "crm/contact_confirm_delete.html"
    success_url = reverse_lazy("crm:contact_list")

    def get_queryset(self):
        return Contact.objects.filter(organization=self.request.organization)

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        name = obj.full_name
        messages.warning(request, f"Contact '{name}' was deleted.")
        return super().delete(request, *args, **kwargs)
