"""
Enterprise CRM Forms.
Provides forms for Accounts and Contacts.
"""
from django import forms
from django.utils.translation import gettext_lazy as _
from apps.accounts.forms import FormStylingMixin
from apps.accounts.models import User
from apps.crm.models import Account, Contact, Lead


class AccountForm(FormStylingMixin, forms.ModelForm):
    """
    Form to create or edit a corporate Account in the CRM.
    """
    class Meta:
        model = Account
        fields = [
            "name",
            "account_type",
            "industry",
            "annual_revenue",
            "employee_count",
            "website",
            "phone",
            "email",
            "billing_address_line1",
            "billing_address_line2",
            "billing_city",
            "billing_state",
            "billing_postal_code",
            "billing_country",
            "shipping_address_line1",
            "shipping_address_line2",
            "shipping_city",
            "shipping_state",
            "shipping_postal_code",
            "shipping_country",
            "lifecycle_stage",
            "status",
            "owner",
            "description",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4, "placeholder": "Enter account notes, history, or key background details..."}),
            "website": forms.URLInput(attrs={"placeholder": "https://company.com"}),
            "email": forms.EmailInput(attrs={"placeholder": "contact@company.com"}),
            "annual_revenue": forms.NumberInput(attrs={"placeholder": "0.00", "step": "0.01"}),
            "employee_count": forms.NumberInput(attrs={"placeholder": "e.g. 250"}),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            member_user_ids = organization.members.filter(status="ACTIVE").values_list("user_id", flat=True)
            self.fields["owner"].queryset = User.objects.filter(id__in=member_user_ids)
            self.fields["owner"].empty_label = _("-- Select Account Owner --")


class ContactForm(FormStylingMixin, forms.ModelForm):
    """
    Form to create or edit an individual Contact.
    """
    class Meta:
        model = Contact
        fields = [
            "account",
            "first_name",
            "last_name",
            "email",
            "phone",
            "mobile",
            "job_title",
            "department",
            "is_primary_contact",
            "do_not_call",
            "do_not_email",
            "address_line1",
            "address_line2",
            "city",
            "state",
            "postal_code",
            "country",
            "lifecycle_stage",
            "owner",
            "notes",
        ]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 4, "placeholder": "Key notes about this contact, relationship history..."}),
            "email": forms.EmailInput(attrs={"placeholder": "first.last@company.com"}),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            self.fields["account"].queryset = Account.objects.filter(organization=organization)
            self.fields["account"].empty_label = _("-- No Associated Account --")
            member_user_ids = organization.members.filter(status="ACTIVE").values_list("user_id", flat=True)
            self.fields["owner"].queryset = User.objects.filter(id__in=member_user_ids)
            self.fields["owner"].empty_label = _("-- Select Contact Owner --")


class LeadForm(FormStylingMixin, forms.ModelForm):
    """
    Form to create or edit an inbound/outbound sales Lead.
    """
    class Meta:
        model = Lead
        fields = [
            "first_name",
            "last_name",
            "company_name",
            "job_title",
            "email",
            "phone",
            "website",
            "lead_source",
            "status",
            "priority",
            "estimated_value",
            "industry",
            "employee_count",
            "annual_revenue",
            "address_line1",
            "city",
            "state",
            "postal_code",
            "country",
            "owner",
            "notes",
        ]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 4, "placeholder": "Prospect needs, background discussion, procurement schedule..."}),
            "website": forms.URLInput(attrs={"placeholder": "https://prospect.com"}),
            "email": forms.EmailInput(attrs={"placeholder": "prospect@company.com"}),
            "estimated_value": forms.NumberInput(attrs={"placeholder": "0.00", "step": "0.01"}),
            "annual_revenue": forms.NumberInput(attrs={"placeholder": "0.00", "step": "0.01"}),
            "employee_count": forms.NumberInput(attrs={"placeholder": "e.g. 150"}),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            member_user_ids = organization.members.filter(status="ACTIVE").values_list("user_id", flat=True)
            self.fields["owner"].queryset = User.objects.filter(id__in=member_user_ids)
            self.fields["owner"].empty_label = _("-- Select Lead Owner --")


class LeadConvertForm(FormStylingMixin, forms.Form):
    """
    Form to guide atomic conversion of a Lead into Account, Contact, and Deal.
    """
    create_account = forms.BooleanField(
        label=_("Create New Corporate Account"),
        required=False,
        initial=True,
    )
    account_name = forms.CharField(
        label=_("Account Name"),
        max_length=255,
        required=False,
    )
    existing_account = forms.ModelChoiceField(
        label=_("Or Attach to Existing Account"),
        queryset=Account.objects.none(),
        required=False,
        empty_label=_("-- Select Existing Account --"),
    )
    create_contact = forms.BooleanField(
        label=_("Create Key Decision Maker Contact"),
        required=False,
        initial=True,
    )
    create_deal = forms.BooleanField(
        label=_("Create Sales Opportunity / Deal"),
        required=False,
        initial=True,
    )
    deal_name = forms.CharField(
        label=_("Deal / Opportunity Name"),
        max_length=255,
        required=False,
    )
    deal_amount = forms.DecimalField(
        label=_("Deal Amount ($)"),
        max_digits=18,
        decimal_places=2,
        required=False,
    )

    def __init__(self, *args, lead=None, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            self.fields["existing_account"].queryset = Account.objects.filter(organization=organization).order_by("name")
        if lead:
            self.fields["account_name"].initial = lead.company_name
            self.fields["deal_name"].initial = f"{lead.company_name} — Initial Contract"
            self.fields["deal_amount"].initial = lead.estimated_value

