"""
EnterpriseOne Finance & General Ledger Forms (Milestone 7.1).
Includes forms for Chart of Accounts, Fiscal Calendars, and Journal Vouchers.
"""
from decimal import Decimal
from django import forms
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory, BaseInlineFormSet
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

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


class GLAccountForm(forms.ModelForm):
    """
    Form for registering or updating General Ledger accounts.
    """
    class Meta:
        model = GLAccount
        fields = [
            "code",
            "name",
            "category",
            "subtype",
            "normal_balance",
            "parent",
            "currency",
            "is_reconciliation",
            "is_active",
            "allow_direct_posting",
            "description",
        ]
        widgets = {
            "code": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. 1010"}),
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Cash in Bank"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "subtype": forms.Select(attrs={"class": "form-select"}),
            "normal_balance": forms.Select(attrs={"class": "form-select"}),
            "parent": forms.Select(attrs={"class": "form-select"}),
            "currency": forms.TextInput(attrs={"class": "form-control", "value": "USD"}),
            "is_reconciliation": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "allow_direct_posting": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.organization = organization
        if organization:
            # Only show parent accounts belonging to this org
            parents_qs = GLAccount.objects.filter(organization=organization)
            if self.instance and self.instance.pk:
                parents_qs = parents_qs.exclude(pk=self.instance.pk)
            self.fields["parent"].queryset = parents_qs
        else:
            self.fields["parent"].queryset = GLAccount.objects.none()


class FiscalYearForm(forms.ModelForm):
    """
    Form for establishing a new fiscal reporting year.
    """
    auto_create_periods = forms.BooleanField(
        required=False,
        initial=True,
        label=_("Auto-generate 12 monthly periods"),
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    class Meta:
        model = FiscalYear
        fields = ["code", "name", "start_date", "end_date"]
        widgets = {
            "code": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. FY2026"}),
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Fiscal Year 2026"}),
            "start_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "end_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }


class FiscalPeriodForm(forms.ModelForm):
    """
    Form for configuring individual accounting periods.
    """
    class Meta:
        model = FiscalPeriod
        fields = ["period_number", "name", "start_date", "end_date"]
        widgets = {
            "period_number": forms.NumberInput(attrs={"class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "start_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "end_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }


class JournalEntryHeaderForm(forms.ModelForm):
    """
    Header voucher form for manual journal entry creation.
    """
    class Meta:
        model = JournalEntry
        fields = [
            "entry_date",
            "fiscal_period",
            "reference",
            "source_document_type",
            "narration",
        ]
        widgets = {
            "entry_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "fiscal_period": forms.Select(attrs={"class": "form-select"}),
            "reference": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Invoice # / Check #"}),
            "source_document_type": forms.Select(attrs={"class": "form-select"}),
            "narration": forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "Transaction explanation..."}),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.organization = organization
        if organization:
            # Only show open periods for this organization
            self.fields["fiscal_period"].queryset = FiscalPeriod.objects.filter(
                organization=organization,
                is_closed=False,
            ).select_related("fiscal_year")
        else:
            self.fields["fiscal_period"].queryset = FiscalPeriod.objects.none()


class JournalEntryLineForm(forms.ModelForm):
    """
    Individual debit/credit line form.
    """
    class Meta:
        model = JournalEntryLine
        fields = [
            "account",
            "debit",
            "credit",
            "narration",
            "partner_name",
            "cost_center",
        ]
        widgets = {
            "account": forms.Select(attrs={"class": "form-select account-select"}),
            "debit": forms.NumberInput(attrs={"class": "form-control debit-input", "step": "0.01", "min": "0"}),
            "credit": forms.NumberInput(attrs={"class": "form-control credit-input", "step": "0.01", "min": "0"}),
            "narration": forms.TextInput(attrs={"class": "form-control", "placeholder": "Line memo"}),
            "partner_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Customer / Supplier"}),
            "cost_center": forms.TextInput(attrs={"class": "form-control", "placeholder": "Dept / Cost Center"}),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            self.fields["account"].queryset = GLAccount.objects.filter(
                organization=organization,
                is_active=True,
                allow_direct_posting=True,
            ).order_by("code")


class BaseJournalEntryLineFormSet(BaseInlineFormSet):
    """
    FormSet enforcing strict double-entry balancing across all active lines.
    """
    def __init__(self, *args, organization=None, **kwargs):
        self.organization = organization
        super().__init__(*args, **kwargs)
        for form in self.forms:
            if organization and "account" in form.fields:
                form.fields["account"].queryset = GLAccount.objects.filter(
                    organization=organization,
                    is_active=True,
                    allow_direct_posting=True,
                ).order_by("code")

    def clean(self):
        super().clean()
        if any(self.errors):
            return

        total_debit = Decimal("0.00")
        total_credit = Decimal("0.00")
        valid_lines_count = 0

        for form in self.forms:
            if not form.cleaned_data or form.cleaned_data.get("DELETE", False):
                continue

            account = form.cleaned_data.get("account")
            debit = form.cleaned_data.get("debit") or Decimal("0.00")
            credit = form.cleaned_data.get("credit") or Decimal("0.00")

            if not account:
                continue

            if debit < 0 or credit < 0:
                raise ValidationError(_("Debit and Credit amounts must not be negative."))

            if debit == 0 and credit == 0:
                raise ValidationError(_(f"Line for account {account.code} must have a non-zero debit or credit amount."))

            if debit > 0 and credit > 0:
                raise ValidationError(_(f"Line for account {account.code} cannot have both debit and credit amounts."))

            total_debit += debit
            total_credit += credit
            valid_lines_count += 1

        if valid_lines_count < 2:
            raise ValidationError(_("A journal entry requires at least two valid transaction lines."))

        if total_debit != total_credit:
            diff = abs(total_debit - total_credit)
            raise ValidationError(
                _(f"Transaction is out of balance! Total Debit: ${total_debit:,.2f} | Total Credit: ${total_credit:,.2f} | Difference: ${diff:,.2f}")
            )


JournalEntryLineFormSet = inlineformset_factory(
    JournalEntry,
    JournalEntryLine,
    form=JournalEntryLineForm,
    formset=BaseJournalEntryLineFormSet,
    extra=2,
    can_delete=True,
    min_num=2,
    validate_min=True,
)


class JournalReversalForm(forms.Form):
    """
    Form for posting a counter-balancing journal reversal.
    """
    reversal_date = forms.DateField(
        initial=timezone.now,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        label=_("Reversal Posting Date"),
    )
    narration = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "Optional reason for reversal..."}),
        label=_("Reversal Reason / Memo"),
    )
