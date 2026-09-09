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
