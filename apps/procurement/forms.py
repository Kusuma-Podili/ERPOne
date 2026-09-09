"""
EnterpriseOne Procurement Forms (Milestone 6.1).
Provides forms for Supplier profile registration, contacts, and vendor catalog offerings.
"""
from django import forms
from decimal import Decimal
from apps.sales.models import Product
from .models import (
    Supplier,
    SupplierType,
    PaymentTerms,
    SupplierStatus,
    SupplierContact,
    SupplierProduct,
)


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = [
            "name",
            "code",
            "supplier_type",
            "status",
            "payment_terms",
            "currency",
            "tax_id",
            "email",
            "phone",
            "website",
            "address",
            "city",
            "state_province",
            "postal_code",
            "country",
            "lead_time_rating",
            "quality_rating",
            "notes",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Acme Industrial Supply Inc."}),
            "code": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. VEND-ACME-01"}),
            "supplier_type": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "payment_terms": forms.Select(attrs={"class": "form-select"}),
            "currency": forms.TextInput(attrs={"class": "form-control"}),
            "tax_id": forms.TextInput(attrs={"class": "form-control", "placeholder": "Tax ID / EIN"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "orders@supplier.com"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "website": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://..."}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "city": forms.TextInput(attrs={"class": "form-control"}),
            "state_province": forms.TextInput(attrs={"class": "form-control"}),
            "postal_code": forms.TextInput(attrs={"class": "form-control"}),
            "country": forms.TextInput(attrs={"class": "form-control"}),
            "lead_time_rating": forms.NumberInput(attrs={"class": "form-control", "step": "0.1", "min": "1.0", "max": "5.0"}),
            "quality_rating": forms.NumberInput(attrs={"class": "form-control", "step": "0.1", "min": "1.0", "max": "5.0"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class SupplierContactForm(forms.ModelForm):
    class Meta:
        model = SupplierContact
        fields = [
            "name",
            "title",
            "email",
            "phone",
            "is_primary",
            "notes",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Full Name"}),
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Account Executive"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "is_primary": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "notes": forms.TextInput(attrs={"class": "form-control"}),
        }


class SupplierProductForm(forms.ModelForm):
    class Meta:
        model = SupplierProduct
        fields = [
            "product",
            "supplier_sku",
            "unit_price",
            "currency",
            "minimum_order_quantity",
            "lead_time_days",
            "is_preferred",
            "is_active",
        ]
        widgets = {
            "product": forms.Select(attrs={"class": "form-select"}),
            "supplier_sku": forms.TextInput(attrs={"class": "form-control", "placeholder": "Vendor Part #"}),
            "unit_price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "currency": forms.TextInput(attrs={"class": "form-control"}),
            "minimum_order_quantity": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "lead_time_days": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
            "is_preferred": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            self.fields["product"].queryset = Product.objects.filter(organization=organization, is_active=True)


from apps.sales.models import UnitOfMeasure
from .models import (
    RequestForQuotation,
    RFQLine,
    RFQVendorInvitation,
    VendorBid,
    VendorBidLine,
)


class RFQForm(forms.ModelForm):
    class Meta:
        model = RequestForQuotation
        fields = [
            "title",
            "submission_deadline",
            "delivery_deadline",
            "notes",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Q4 Precision Fastener Sourcing"}),
            "submission_deadline": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}),
            "delivery_deadline": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Specify commercial terms, delivery location, evaluation criteria..."}),
        }


class RFQLineForm(forms.ModelForm):
    class Meta:
        model = RFQLine
        fields = [
            "product",
            "target_quantity",
            "uom",
            "target_delivery_date",
            "specifications",
        ]
        widgets = {
            "product": forms.Select(attrs={"class": "form-select product-select"}),
            "target_quantity": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "uom": forms.Select(attrs={"class": "form-select"}),
            "target_delivery_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "specifications": forms.TextInput(attrs={"class": "form-control", "placeholder": "Grade, tolerance, packaging..."}),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            self.fields["product"].queryset = Product.objects.filter(organization=organization, is_active=True)
            self.fields["uom"].queryset = UnitOfMeasure.objects.filter(organization=organization, is_active=True)


RFQLineFormSet = forms.inlineformset_factory(
    RequestForQuotation,
    RFQLine,
    form=RFQLineForm,
    extra=1,
    can_delete=True,
)


class RFQInviteVendorForm(forms.Form):
    suppliers = forms.ModelMultipleChoiceField(
        queryset=Supplier.objects.none(),
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
        label="Select Suppliers to Invite",
    )

    def __init__(self, *args, organization=None, rfq=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            qs = Supplier.objects.filter(organization=organization, is_active=True, status=SupplierStatus.ACTIVE)
            if rfq:
                already_invited = rfq.invitations.values_list("supplier_id", flat=True)
                qs = qs.exclude(id__in=already_invited)
            self.fields["suppliers"].queryset = qs


class VendorBidForm(forms.ModelForm):
    class Meta:
        model = VendorBid
        fields = [
            "supplier",
            "bid_reference",
            "valid_until",
            "payment_terms",
            "lead_time_days",
            "shipping_cost",
            "currency",
            "notes",
        ]
        widgets = {
            "supplier": forms.Select(attrs={"class": "form-select"}),
            "bid_reference": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. QT-2026-8842"}),
            "valid_until": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "payment_terms": forms.Select(attrs={"class": "form-select"}),
            "lead_time_days": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
            "shipping_cost": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "currency": forms.TextInput(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

    def __init__(self, *args, organization=None, rfq=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            qs = Supplier.objects.filter(organization=organization, is_active=True)
            if rfq:
                # Optionally prioritize invited vendors
                pass
            self.fields["supplier"].queryset = qs


class VendorBidLineForm(forms.ModelForm):
    class Meta:
        model = VendorBidLine
        fields = [
            "rfq_line",
            "offered_unit_price",
            "offered_quantity",
            "lead_time_days",
            "notes",
        ]
        widgets = {
            "rfq_line": forms.HiddenInput(),
            "offered_unit_price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "offered_quantity": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "lead_time_days": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
            "notes": forms.TextInput(attrs={"class": "form-control", "placeholder": "Remarks"}),
        }


VendorBidLineFormSet = forms.inlineformset_factory(
    VendorBid,
    VendorBidLine,
    form=VendorBidLineForm,
    extra=0,
    can_delete=False,
)


class AwardBidForm(forms.Form):
    bid_id = forms.UUIDField(widget=forms.HiddenInput())
    award_reason = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Commercial justification, competitive scoring, lead-time preference..."}),
        label="Award Justification Notes",
        required=True,
    )
