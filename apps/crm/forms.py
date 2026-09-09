"""
Enterprise CRM Forms.
Provides forms for Accounts and Contacts.
"""
from django import forms
from django.utils.translation import gettext_lazy as _
from apps.accounts.forms import FormStylingMixin
from apps.accounts.models import User
from apps.crm.models import Account, Contact


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
