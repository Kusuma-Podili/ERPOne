"""
EnterpriseOne Finance & General Ledger Views (Milestone 7.1).
Multi-tenant views for General Ledger Dashboard, Chart of Accounts,
Fiscal Calendars, and Double-Entry Journal Entry Vouchers.
"""
from decimal import Decimal
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    TemplateView,
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    View,
)
from apps.organizations.views import OrganizationAccessMixin
from apps.finance.models import (
    FiscalYear,
    FiscalPeriod,
    AccountCategory,
    AccountSubtype,
    NormalBalance,
    GLAccount,
    JournalStatus,
    SourceDocumentType,
    JournalEntry,
    JournalEntryLine,
)
from apps.finance.forms import (
    GLAccountForm,
    FiscalYearForm,
    FiscalPeriodForm,
    JournalEntryHeaderForm,
    JournalEntryLineFormSet,
    JournalReversalForm,
)
from apps.finance.services import (
    FiscalPeriodService,
    GLAccountService,
    JournalEntryService,
)


class FinanceDashboardView(OrganizationAccessMixin, TemplateView):
    """
    Executive financial overview displaying real-time General Ledger balances and metrics.
    """
    template_name = "finance/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        org = self.request.organization
        if not org:
            return context

        # Account balances by category
        accounts = GLAccount.objects.filter(organization=org, is_active=True)

        asset_balance = sum((acc.current_balance for acc in accounts if acc.category == AccountCategory.ASSET), Decimal("0.00"))
        liability_balance = sum((acc.current_balance for acc in accounts if acc.category == AccountCategory.LIABILITY), Decimal("0.00"))
        equity_balance = sum((acc.current_balance for acc in accounts if acc.category == AccountCategory.EQUITY), Decimal("0.00"))
        revenue_balance = sum((acc.current_balance for acc in accounts if acc.category == AccountCategory.REVENUE), Decimal("0.00"))
        expense_balance = sum((acc.current_balance for acc in accounts if acc.category == AccountCategory.EXPENSE), Decimal("0.00"))
        net_income = revenue_balance - expense_balance

        # Active / current fiscal period
        today = self.request.session.get("current_date")
        from django.utils import timezone
        today = timezone.now().date()
        current_period = FiscalPeriod.objects.filter(
            organization=org,
            start_date__lte=today,
            end_date__gte=today,
        ).first()

        # Journal stats
        entries = JournalEntry.objects.filter(organization=org)
        posted_count = entries.filter(status=JournalStatus.POSTED).count()
        draft_count = entries.filter(status=JournalStatus.DRAFT).count()
        reversed_count = entries.filter(status=JournalStatus.REVERSED).count()
        recent_entries = entries.select_related("fiscal_period").order_by("-created_at")[:8]

        context.update({
            "asset_balance": asset_balance,
            "liability_balance": liability_balance,
            "equity_balance": equity_balance,
            "revenue_balance": revenue_balance,
            "expense_balance": expense_balance,
            "net_income": net_income,
            "current_period": current_period,
            "posted_count": posted_count,
            "draft_count": draft_count,
            "reversed_count": reversed_count,
            "recent_entries": recent_entries,
            "total_accounts_count": accounts.count(),
        })
        return context


class GLAccountListView(OrganizationAccessMixin, ListView):
    """
    Hierarchical Chart of Accounts list and management view.
    """
    model = GLAccount
    template_name = "finance/account_list.html"
    context_object_name = "accounts"
    paginate_by = 50

    def get_queryset(self):
        org = self.request.organization
        if not org:
            return GLAccount.objects.none()

        qs = GLAccount.objects.filter(organization=org).select_related("parent")

        category = self.request.GET.get("category", "").strip()
        if category:
            qs = qs.filter(category=category)

        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(code__icontains=q) | Q(name__icontains=q) | Q(description__icontains=q))

        return qs.order_by("code")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        org = self.request.organization
        context["categories"] = AccountCategory.choices
        context["selected_category"] = self.request.GET.get("category", "")
        context["search_query"] = self.request.GET.get("q", "")
        context["has_accounts"] = GLAccount.objects.filter(organization=org).exists() if org else False
        return context


class GLAccountCreateView(OrganizationAccessMixin, CreateView):
    """
    Creates a new GL Account node in the Chart of Accounts.
    """
    model = GLAccount
    form_class = GLAccountForm
    template_name = "finance/account_form.html"
    success_url = reverse_lazy("finance:account_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.request.organization
        return kwargs

    def form_valid(self, form):
        form.instance.organization = self.request.organization
        messages.success(self.request, f"GL Account {form.instance.code} - {form.instance.name} created successfully.")
        return super().form_valid(form)


class GLAccountUpdateView(OrganizationAccessMixin, UpdateView):
    """
    Modifies an existing GL Account.
    """
    model = GLAccount
    form_class = GLAccountForm
    template_name = "finance/account_form.html"
    success_url = reverse_lazy("finance:account_list")

    def get_queryset(self):
        org = self.request.organization
        return GLAccount.objects.filter(organization=org) if org else GLAccount.objects.none()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.request.organization
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, f"GL Account {form.instance.code} updated successfully.")
        return super().form_valid(form)


class GLAccountDetailView(OrganizationAccessMixin, DetailView):
    """
    General Ledger Account Card detailing historical debits, credits, and running balance.
    """
    model = GLAccount
    template_name = "finance/account_detail.html"
    context_object_name = "account"

    def get_queryset(self):
        org = self.request.organization
        return GLAccount.objects.filter(organization=org) if org else GLAccount.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        account = self.object

        # Retrieve all posted journal lines for this account
        posted_lines = (
            JournalEntryLine.objects.filter(
                account=account,
                journal_entry__status__in=[JournalStatus.POSTED, JournalStatus.REVERSED],
            )
            .select_related("journal_entry", "journal_entry__fiscal_period")
            .order_by("journal_entry__entry_date", "journal_entry__entry_number", "line_number")
        )

        ledger_rows = []
        running_bal = Decimal("0.00")

        for line in posted_lines:
            if account.normal_balance == NormalBalance.DEBIT:
                running_bal += (line.debit - line.credit)
            else:
                running_bal += (line.credit - line.debit)

            ledger_rows.append({
                "entry_number": line.journal_entry.entry_number,
                "entry_id": line.journal_entry.id,
                "entry_date": line.journal_entry.entry_date,
                "period": line.journal_entry.fiscal_period.name,
                "reference": line.journal_entry.reference,
                "memo": line.narration or line.journal_entry.narration,
                "partner": line.partner_name,
                "cost_center": line.cost_center,
                "debit": line.debit,
                "credit": line.credit,
                "running_balance": running_bal,
            })

        total_debits = sum((row["debit"] for row in ledger_rows), Decimal("0.00"))
        total_credits = sum((row["credit"] for row in ledger_rows), Decimal("0.00"))

        context.update({
            "ledger_rows": ledger_rows,
            "total_debits": total_debits,
            "total_credits": total_credits,
            "final_balance": running_bal,
        })
        return context


class GLAccountProvisionStandardView(OrganizationAccessMixin, View):
    """
    One-click action to seed standard GAAP/IFRS Chart of Accounts.
    """
    def post(self, request, *args, **kwargs):
        org = request.organization
        if not org:
            messages.error(request, "No active organization selected.")
            return redirect("accounts:dashboard")

        count = GLAccountService.provision_standard_chart_of_accounts(org)
        if count > 0:
            messages.success(request, f"Successfully provisioned standard Chart of Accounts ({count} accounts created).")
        else:
            messages.info(request, "Chart of Accounts is already initialized for this organization.")
        return redirect("finance:account_list")


class FiscalYearListView(OrganizationAccessMixin, ListView):
    """
    Lists fiscal reporting years and periods with posting lock statuses.
    """
    model = FiscalYear
    template_name = "finance/fiscal_year_list.html"
    context_object_name = "fiscal_years"

    def get_queryset(self):
        org = self.request.organization
        if not org:
            return FiscalYear.objects.none()
        return FiscalYear.objects.filter(organization=org).prefetch_related("periods").order_by("-start_date")


class FiscalYearCreateView(OrganizationAccessMixin, CreateView):
    """
    Creates a new fiscal year and auto-generates 12 monthly accounting periods.
    """
    model = FiscalYear
    form_class = FiscalYearForm
    template_name = "finance/fiscal_year_form.html"
    success_url = reverse_lazy("finance:fiscal_year_list")

    def form_valid(self, form):
        org = self.request.organization
        auto_periods = form.cleaned_data.get("auto_create_periods", True)
        try:
            FiscalPeriodService.create_fiscal_year(
                organization=org,
                name=form.cleaned_data["name"],
                code=form.cleaned_data["code"],
                start_date=form.cleaned_data["start_date"],
                end_date=form.cleaned_data["end_date"],
                auto_create_monthly_periods=auto_periods,
            )
            messages.success(self.request, f"Fiscal Year {form.cleaned_data['code']} created with periodic boundaries.")
            return redirect(self.success_url)
        except Exception as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)


class FiscalPeriodToggleCloseView(OrganizationAccessMixin, View):
    """
    Toggles open/closed state for a fiscal period, preventing or permitting postings.
    """
    def post(self, request, pk, *args, **kwargs):
        org = request.organization
        period = get_object_or_404(FiscalPeriod, pk=pk, organization=org)

        try:
            if period.is_closed:
                FiscalPeriodService.reopen_period(period, request.user)
                messages.success(request, f"Fiscal period '{period.name}' has been reopened.")
            else:
                FiscalPeriodService.close_period(period, request.user)
                messages.success(request, f"Fiscal period '{period.name}' is now closed to transaction postings.")
        except Exception as e:
            messages.error(request, f"Unable to modify period status: {e}")

        return redirect("finance:fiscal_year_list")


class JournalEntryListView(OrganizationAccessMixin, ListView):
    """
    Lists general journal vouchers with filters for period, status, and search query.
    """
    model = JournalEntry
    template_name = "finance/journal_entry_list.html"
    context_object_name = "journal_entries"
    paginate_by = 30

    def get_queryset(self):
        org = self.request.organization
        if not org:
            return JournalEntry.objects.none()

        qs = (
            JournalEntry.objects.filter(organization=org)
            .select_related("fiscal_period", "fiscal_period__fiscal_year", "posted_by", "reversed_by_entry")
            .order_by("-entry_date", "-created_at")
        )

        status = self.request.GET.get("status", "").strip()
        if status:
            qs = qs.filter(status=status)

        period_id = self.request.GET.get("period", "").strip()
        if period_id:
            qs = qs.filter(fiscal_period_id=period_id)

        source_type = self.request.GET.get("source", "").strip()
        if source_type:
            qs = qs.filter(source_document_type=source_type)

        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(entry_number__icontains=q)
                | Q(reference__icontains=q)
                | Q(narration__icontains=q)
            )

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        org = self.request.organization
        context["statuses"] = JournalStatus.choices
        context["selected_status"] = self.request.GET.get("status", "")
        context["selected_period"] = self.request.GET.get("period", "")
        context["selected_source"] = self.request.GET.get("source", "")
        context["search_query"] = self.request.GET.get("q", "")
        if org:
            context["periods"] = FiscalPeriod.objects.filter(organization=org).order_by("-start_date")
        return context


class JournalEntryCreateView(OrganizationAccessMixin, View):
    """
    Creates a new multi-line double-entry Journal Voucher with dynamic balancing lines.
    """
    template_name = "finance/journal_entry_form.html"

    def get(self, request, *args, **kwargs):
        org = request.organization
        header_form = JournalEntryHeaderForm(organization=org)
        dummy_instance = JournalEntry(organization=org)
        formset = JournalEntryLineFormSet(instance=dummy_instance, organization=org)
        return render(request, self.template_name, {
            "header_form": header_form,
            "formset": formset,
        })

    def post(self, request, *args, **kwargs):
        org = request.organization
        header_form = JournalEntryHeaderForm(request.POST, organization=org)
        dummy_instance = JournalEntry(organization=org)
        formset = JournalEntryLineFormSet(request.POST, instance=dummy_instance, organization=org)

        if header_form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    lines_data = []
                    for line_form in formset:
                        if not line_form.cleaned_data or line_form.cleaned_data.get("DELETE", False):
                            continue
                        lines_data.append({
                            "account": line_form.cleaned_data["account"],
                            "debit": line_form.cleaned_data.get("debit") or Decimal("0.00"),
                            "credit": line_form.cleaned_data.get("credit") or Decimal("0.00"),
                            "narration": line_form.cleaned_data.get("narration", ""),
                            "partner_name": line_form.cleaned_data.get("partner_name", ""),
                            "cost_center": line_form.cleaned_data.get("cost_center", ""),
                        })

                    entry = JournalEntryService.create_journal_entry(
                        organization=org,
                        user=request.user,
                        fiscal_period=header_form.cleaned_data["fiscal_period"],
                        entry_date=header_form.cleaned_data["entry_date"],
                        narration=header_form.cleaned_data["narration"],
                        lines_data=lines_data,
                        reference=header_form.cleaned_data.get("reference", ""),
                        source_document_type=header_form.cleaned_data.get("source_document_type", SourceDocumentType.MANUAL),
                    )

                    messages.success(request, f"Journal Entry {entry.entry_number} created in Draft status.")
                    return redirect("finance:journal_entry_detail", pk=entry.pk)
            except Exception as e:
                messages.error(request, f"Failed to save Journal Entry: {e}")

        return render(request, self.template_name, {
            "header_form": header_form,
            "formset": formset,
        })


class JournalEntryDetailView(OrganizationAccessMixin, DetailView):
    """
    Detailed voucher view showing debits, credits, balancing check, and posting audit trail.
    """
    model = JournalEntry
    template_name = "finance/journal_entry_detail.html"
    context_object_name = "entry"

    def get_queryset(self):
        org = self.request.organization
        return (
            JournalEntry.objects.filter(organization=org)
            .select_related("fiscal_period", "fiscal_period__fiscal_year", "posted_by", "created_by", "reversed_by_entry")
            .prefetch_related("lines", "lines__account")
            if org
            else JournalEntry.objects.none()
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["reversal_form"] = JournalReversalForm()
        return context


class JournalEntryPostView(OrganizationAccessMixin, View):
    """
    Posts a draft journal entry to the General Ledger.
    """
    def post(self, request, pk, *args, **kwargs):
        org = request.organization
        entry = get_object_or_404(JournalEntry, pk=pk, organization=org)

        try:
            JournalEntryService.post_journal_entry(entry, request.user)
            messages.success(request, f"Journal Entry {entry.entry_number} has been successfully posted to the General Ledger.")
        except Exception as e:
            messages.error(request, f"Posting failed: {e}")

        return redirect("finance:journal_entry_detail", pk=entry.pk)


class JournalEntryReverseView(OrganizationAccessMixin, View):
    """
    Posts an offsetting reversal entry to undo a posted journal voucher.
    """
    def post(self, request, pk, *args, **kwargs):
        org = request.organization
        entry = get_object_or_404(JournalEntry, pk=pk, organization=org)
        form = JournalReversalForm(request.POST)

        if form.is_valid():
            rev_date = form.cleaned_data["reversal_date"]
            memo = form.cleaned_data["narration"]
            try:
                reversal_entry = JournalEntryService.reverse_journal_entry(
                    entry,
                    request.user,
                    reversal_date=rev_date,
                    narration=memo,
                )
                messages.success(request, f"Journal Entry {entry.entry_number} reversed. Offsetting entry {reversal_entry.entry_number} posted.")
                return redirect("finance:journal_entry_detail", pk=reversal_entry.pk)
            except Exception as e:
                messages.error(request, f"Reversal failed: {e}")
        else:
            messages.error(request, "Invalid reversal parameters.")

        return redirect("finance:journal_entry_detail", pk=entry.pk)


class JournalEntryPrintView(OrganizationAccessMixin, DetailView):
    """
    Formal printable Journal Voucher layout.
    """
    model = JournalEntry
    template_name = "finance/journal_entry_print.html"
    context_object_name = "entry"

    def get_queryset(self):
        org = self.request.organization
        return (
            JournalEntry.objects.filter(organization=org)
            .select_related("fiscal_period", "fiscal_period__fiscal_year", "posted_by", "created_by")
            .prefetch_related("lines", "lines__account")
            if org
            else JournalEntry.objects.none()
        )
