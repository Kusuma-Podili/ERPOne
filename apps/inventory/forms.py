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
    StockMovement,
    StockMovementLine,
    StockMovementType,
    StockMovementStatus,
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

from django.forms import inlineformset_factory


class StockMovementForm(forms.ModelForm):
    class Meta:
        model = StockMovement
        fields = [
            "movement_type",
            "source_warehouse",
            "destination_warehouse",
            "reference_document",
            "movement_date",
            "notes",
        ]
        widgets = {
            "movement_type": forms.Select(attrs={"class": "form-select", "id": "id_movement_type"}),
            "source_warehouse": forms.Select(attrs={"class": "form-select"}),
            "destination_warehouse": forms.Select(attrs={"class": "form-select"}),
            "reference_document": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. PO-2026-0045, RMA-102"}),
            "movement_date": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Reason or operational notes..."}),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            wh_qs = Warehouse.objects.filter(organization=organization, is_active=True)
            self.fields["source_warehouse"].queryset = wh_qs
            self.fields["destination_warehouse"].queryset = wh_qs


class StockMovementLineForm(forms.ModelForm):
    class Meta:
        model = StockMovementLine
        fields = [
            "product",
            "source_location",
            "destination_location",
            "quantity",
            "unit_cost",
            "batch_number",
            "serial_number",
            "notes",
        ]
        widgets = {
            "product": forms.Select(attrs={"class": "form-select"}),
            "source_location": forms.Select(attrs={"class": "form-select"}),
            "destination_location": forms.Select(attrs={"class": "form-select"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0.01"}),
            "unit_cost": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "batch_number": forms.TextInput(attrs={"class": "form-control", "placeholder": "Lot/Batch"}),
            "serial_number": forms.TextInput(attrs={"class": "form-control", "placeholder": "Serial #"}),
            "notes": forms.TextInput(attrs={"class": "form-control", "placeholder": "Notes"}),
        }

    def __init__(self, *args, organization=None, source_warehouse=None, destination_warehouse=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            self.fields["product"].queryset = Product.objects.filter(organization=organization, is_active=True)
        if source_warehouse:
            self.fields["source_location"].queryset = StorageLocation.objects.filter(
                warehouse=source_warehouse, is_active=True
            )
        else:
            self.fields["source_location"].queryset = StorageLocation.objects.none() if not self.instance.pk else self.fields["source_location"].queryset

        if destination_warehouse:
            self.fields["destination_location"].queryset = StorageLocation.objects.filter(
                warehouse=destination_warehouse, is_active=True
            )
        else:
            self.fields["destination_location"].queryset = StorageLocation.objects.none() if not self.instance.pk else self.fields["destination_location"].queryset


StockMovementLineFormSet = inlineformset_factory(
    StockMovement,
    StockMovementLine,
    fields=[
        "product",
        "source_location",
        "destination_location",
        "quantity",
        "unit_cost",
        "batch_number",
        "serial_number",
        "notes",
    ],
    extra=1,
    can_delete=True,
    widgets={
        "product": forms.Select(attrs={"class": "form-select"}),
        "source_location": forms.Select(attrs={"class": "form-select"}),
        "destination_location": forms.Select(attrs={"class": "form-select"}),
        "quantity": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0.01"}),
        "unit_cost": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
        "batch_number": forms.TextInput(attrs={"class": "form-control", "placeholder": "Lot #"}),
        "serial_number": forms.TextInput(attrs={"class": "form-control", "placeholder": "Serial"}),
        "notes": forms.TextInput(attrs={"class": "form-control", "placeholder": "Notes"}),
    }
)


class StockQuickAdjustmentForm(forms.Form):
    ADJUSTMENT_CHOICES = [
        ("gain", "Inventory Gain / Found Stock"),
        ("loss", "Inventory Loss / Shrinkage"),
        ("scrap", "Damaged Goods / Scrap Write-Off"),
    ]

    warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Target Warehouse",
    )
    location = forms.ModelChoiceField(
        queryset=StorageLocation.objects.none(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Storage Location",
    )
    product = forms.ModelChoiceField(
        queryset=Product.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Product",
    )
    adjustment_type = forms.ChoiceField(
        choices=ADJUSTMENT_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Adjustment Type",
    )
    quantity = forms.DecimalField(
        min_value=Decimal("0.01"),
        decimal_places=2,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
        label="Quantity",
    )
    reference = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. AUDIT-2026-Q1"}),
        label="Audit / Reference Code",
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Reason for variance..."}),
        label="Reason & Justification",
    )

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            self.fields["warehouse"].queryset = Warehouse.objects.filter(organization=organization, is_active=True)
            self.fields["location"].queryset = StorageLocation.objects.filter(organization=organization, is_active=True)
            self.fields["product"].queryset = Product.objects.filter(organization=organization, is_active=True)
