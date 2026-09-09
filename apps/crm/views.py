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
    FormView,
    TemplateView,
)

from apps.organizations.views import OrganizationAccessMixin
from apps.crm.models import (
    Account,
    Contact,
    Lead,
    AccountType,
    IndustryChoice,
    LifecycleStage,
    AccountStatus,
    LeadSource,
    LeadStatus,
    LeadPriority,
)
from apps.crm.forms import AccountForm, ContactForm, LeadForm, LeadConvertForm
from apps.crm.services import LeadScoringService, LeadConversionService


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


# =====================================================================
# LEAD & SCORING VIEWS
# =====================================================================

class LeadListView(OrganizationAccessMixin, ListView):
    """
    Inbound sales pipeline leads list.
    Displays algorithmic scores, acquisition channels, and qualification stages.
    """
    model = Lead
    template_name = "crm/lead_list.html"
    context_object_name = "leads"
    paginate_by = 25

    def get_queryset(self):
        qs = Lead.objects.filter(
            organization=self.request.organization
        ).select_related("owner", "created_by", "converted_account", "converted_contact")

        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(company_name__icontains=q)
                | Q(email__icontains=q)
                | Q(phone__icontains=q)
            )

        status = self.request.GET.get("status", "").strip()
        if status:
            qs = qs.filter(status=status)

        source = self.request.GET.get("source", "").strip()
        if source:
            qs = qs.filter(lead_source=source)

        priority = self.request.GET.get("priority", "").strip()
        if priority:
            qs = qs.filter(priority=priority)

        min_score = self.request.GET.get("min_score", "").strip()
        if min_score and min_score.isdigit():
            qs = qs.filter(lead_score__gte=int(min_score))

        sort = self.request.GET.get("sort", "-lead_score")
        allowed_sorts = ["-lead_score", "lead_score", "-created_at", "created_at", "company_name", "-estimated_value"]
        if sort in allowed_sorts:
            qs = qs.order_by(sort)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        org = self.request.organization
        ctx["total_leads_count"] = Lead.objects.filter(organization=org).count()
        ctx["qualified_leads_count"] = Lead.objects.filter(
            organization=org, status=LeadStatus.QUALIFIED
        ).count()
        ctx["converted_leads_count"] = Lead.objects.filter(
            organization=org, is_converted=True
        ).count()
        ctx["hot_leads_count"] = Lead.objects.filter(
            organization=org, is_converted=False, lead_score__gte=75
        ).count()
        ctx["lead_sources"] = LeadSource.choices
        ctx["lead_statuses"] = LeadStatus.choices
        ctx["lead_priorities"] = LeadPriority.choices
        ctx["current_q"] = self.request.GET.get("q", "")
        ctx["current_status"] = self.request.GET.get("status", "")
        ctx["current_source"] = self.request.GET.get("source", "")
        ctx["current_priority"] = self.request.GET.get("priority", "")
        ctx["current_min_score"] = self.request.GET.get("min_score", "")
        ctx["current_sort"] = self.request.GET.get("sort", "-lead_score")
        return ctx


class LeadDetailView(OrganizationAccessMixin, DetailView):
    """
    Lead dossier view.
    Displays algorithmic scoring breakdown, demographic details, and conversion triggers.
    """
    model = Lead
    template_name = "crm/lead_detail.html"
    context_object_name = "lead"

    def get_queryset(self):
        return Lead.objects.filter(
            organization=self.request.organization
        ).select_related("owner", "created_by", "converted_account", "converted_contact")


class LeadCreateView(OrganizationAccessMixin, CreateView):
    """
    Registers an inbound or outbound sales Lead and immediately calculates its score.
    """
    model = Lead
    form_class = LeadForm
    template_name = "crm/lead_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.request.organization
        return kwargs

    def form_valid(self, form):
        form.instance.organization = self.request.organization
        form.instance.created_by = self.request.user
        if not form.instance.owner:
            form.instance.owner = self.request.user
        response = super().form_valid(form)
        # Calculate algorithmic score
        LeadScoringService.score_and_save(self.object)
        messages.success(
            self.request,
            f"Lead '{self.object.full_name}' created with an initial Lead Score of {self.object.lead_score}/100."
        )
        return response

    def get_success_url(self):
        return reverse("crm:lead_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form_title"] = "Create Inbound Lead"
        ctx["form_action"] = "Create Lead"
        return ctx


class LeadUpdateView(OrganizationAccessMixin, UpdateView):
    """
    Updates a Lead record and recalculates its algorithmic score.
    """
    model = Lead
    form_class = LeadForm
    template_name = "crm/lead_form.html"

    def get_queryset(self):
        return Lead.objects.filter(organization=self.request.organization)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.request.organization
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        LeadScoringService.score_and_save(self.object)
        messages.success(self.request, f"Lead '{self.object.full_name}' updated. Score recalculated to {self.object.lead_score}/100.")
        return response

    def get_success_url(self):
        return reverse("crm:lead_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form_title"] = f"Edit Lead: {self.object.full_name}"
        ctx["form_action"] = "Save Changes"
        ctx["lead"] = self.object
        return ctx


class LeadDeleteView(OrganizationAccessMixin, DeleteView):
    """
    Removes a Lead from the organization pipeline.
    """
    model = Lead
    template_name = "crm/lead_confirm_delete.html"
    success_url = reverse_lazy("crm:lead_list")

    def get_queryset(self):
        return Lead.objects.filter(organization=self.request.organization)

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        name = obj.full_name
        messages.warning(request, f"Lead '{name}' was permanently removed.")
        return super().delete(request, *args, **kwargs)


class LeadConvertView(OrganizationAccessMixin, FormView):
    """
    Interactive conversion view that atomizes a qualified Lead into
    an Account, primary Contact, and initial Opportunity Deal.
    """
    form_class = LeadConvertForm
    template_name = "crm/lead_convert.html"

    def dispatch(self, request, *args, **kwargs):
        self.lead = get_object_or_404(
            Lead, pk=kwargs["pk"], organization=request.organization
        )
        if self.lead.is_converted:
            messages.info(request, "This lead has already been converted into a customer account.")
            if self.lead.converted_account:
                return redirect("crm:account_detail", pk=self.lead.converted_account.pk)
            return redirect("crm:lead_detail", pk=self.lead.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["lead"] = self.lead
        kwargs["organization"] = self.request.organization
        return kwargs

    def form_valid(self, form):
        create_account = form.cleaned_data.get("create_account")
        account_name = form.cleaned_data.get("account_name")
        existing_account = form.cleaned_data.get("existing_account")
        create_contact = form.cleaned_data.get("create_contact")
        create_deal = form.cleaned_data.get("create_deal")
        deal_name = form.cleaned_data.get("deal_name") if create_deal else None
        deal_amount = form.cleaned_data.get("deal_amount") if create_deal else None

        result = LeadConversionService.convert_lead(
            lead=self.lead,
            create_account=create_account and not existing_account,
            create_contact=create_contact,
            account_id=str(existing_account.id) if existing_account else None,
            account_name=account_name,
            deal_name=deal_name,
            deal_amount=deal_amount,
            user=self.request.user,
        )

        messages.success(
            self.request,
            f"Successfully converted Lead '{self.lead.full_name}' into Customer Account and Contact!"
        )
        if result.get("account"):
            return redirect("crm:account_detail", pk=result["account"].pk)
        return redirect("crm:contact_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["lead"] = self.lead
        return ctx


class LeadRecalculateScoreView(OrganizationAccessMixin, View):
    """
    Trigger view to explicitly recalculate a lead's algorithmic score.
    """
    def post(self, request, pk, *args, **kwargs):
        lead = get_object_or_404(Lead, pk=pk, organization=request.organization)
        LeadScoringService.score_and_save(lead)
        messages.success(request, f"Lead Score recalculated to {lead.lead_score}/100.")
        return redirect("crm:lead_detail", pk=lead.pk)

