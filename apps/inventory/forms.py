"""
EnterpriseOne Inventory Forms.
Provides forms for Warehouses, Storage Zones, Storage Locations, and Stock Level tracking.
"""
from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal
from apps.organizations.models import Branch
from apps.accounts.models import User
from apps.sales.models import Product
from .models import (
    Warehouse,
    StorageZone,
    StorageLocation,
    StockItem,
)


class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = [
            "name",
            "code",
            "warehouse_type",
            "branch",
            "manager",
            "address",
            "city",
            "state_province",
            "postal_code",
            "country",
            "is_primary",
            "total_capacity_cbm",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Northeast Distribution Center"}),
            "code": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. WH-BOS-01"}),
            "warehouse_type": forms.Select(attrs={"class": "form-select"}),
            "branch": forms.Select(attrs={"class": "form-select"}),
            "manager": forms.Select(attrs={"class": "form-select"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "Street address..."}),
            "city": forms.TextInput(attrs={"class": "form-control"}),
            "state_province": forms.TextInput(attrs={"class": "form-control"}),
            "postal_code": forms.TextInput(attrs={"class": "form-control"}),
            "country": forms.TextInput(attrs={"class": "form-control"}),
            "is_primary": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "total_capacity_cbm": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            self.fields["branch"].queryset = Branch.objects.filter(organization=organization, is_active=True)
            self.fields["manager"].queryset = User.objects.filter(
                organization_memberships__organization=organization
            ).distinct()


class StorageZoneForm(forms.ModelForm):
    class Meta:
        model = StorageZone
        fields = [
            "warehouse",
            "name",
            "code",
            "zone_type",
            "temperature_controlled",
            "target_temp_celsius",
            "is_active",
        ]
        widgets = {
            "warehouse": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Cold Storage Bay A"}),
            "code": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Z-COLD-01"}),
            "zone_type": forms.Select(attrs={"class": "form-select"}),
            "temperature_controlled": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "target_temp_celsius": forms.NumberInput(attrs={"class": "form-control", "step": "0.1", "placeholder": "-18.0"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            self.fields["warehouse"].queryset = Warehouse.objects.filter(organization=organization, is_active=True)


class StorageLocationForm(forms.ModelForm):
    class Meta:
        model = StorageLocation
        fields = [
            "warehouse",
            "zone",
            "aisle",
            "rack",
            "shelf",
            "bin",
            "barcode",
            "max_weight_kg",
            "max_volume_cbm",
            "is_locked",
            "lock_reason",
            "is_active",
        ]
        widgets = {
            "warehouse": forms.Select(attrs={"class": "form-select"}),
            "zone": forms.Select(attrs={"class": "form-select"}),
            "aisle": forms.TextInput(attrs={"class": "form-control", "placeholder": "01"}),
            "rack": forms.TextInput(attrs={"class": "form-control", "placeholder": "01"}),
            "shelf": forms.TextInput(attrs={"class": "form-control", "placeholder": "01"}),
            "bin": forms.TextInput(attrs={"class": "form-control", "placeholder": "01"}),
            "barcode": forms.TextInput(attrs={"class": "form-control", "placeholder": "Optional or auto-generated"}),
            "max_weight_kg": forms.NumberInput(attrs={"class": "form-control", "step": "0.1"}),
            "max_volume_cbm": forms.NumberInput(attrs={"class": "form-control", "step": "0.001"}),
            "is_locked": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "lock_reason": forms.TextInput(attrs={"class": "form-control", "placeholder": "Reason for lock"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            self.fields["warehouse"].queryset = Warehouse.objects.filter(organization=organization, is_active=True)
            self.fields["zone"].queryset = StorageZone.objects.filter(organization=organization, is_active=True)


class StockItemForm(forms.ModelForm):
    class Meta:
        model = StockItem
        fields = [
            "product",
            "warehouse",
            "location",
            "quantity_on_hand",
            "quantity_reserved",
            "safety_stock",
            "reorder_point",
            "reorder_quantity",
        ]
        widgets = {
            "product": forms.Select(attrs={"class": "form-select"}),
            "warehouse": forms.Select(attrs={"class": "form-select"}),
            "location": forms.Select(attrs={"class": "form-select"}),
            "quantity_on_hand": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "quantity_reserved": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "safety_stock": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "reorder_point": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "reorder_quantity": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            self.fields["product"].queryset = Product.objects.filter(organization=organization, is_active=True)
            self.fields["warehouse"].queryset = Warehouse.objects.filter(organization=organization, is_active=True)
            self.fields["location"].queryset = StorageLocation.objects.filter(organization=organization, is_active=True)
