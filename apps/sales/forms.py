"""
EnterpriseOne Sales Forms.
Defines form classes for Product, Category, UOM, PriceBook, PriceBookEntry, and TieredDiscount.
"""
from django import forms
from apps.crm.models import Account, Contact, Deal
from .models import (
    ProductCategory,
    UnitOfMeasure,
    Product,
    PriceBook,
    PriceBookEntry,
    TieredDiscount,
    Quote,
    QuoteLineItem,
    QuoteApproval,
    SalesOrder,
    OrderLineItem,
)


class BaseSalesForm(forms.ModelForm):
    """Base form applying enterprise design system CSS classes."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({"class": "form-checkbox"})
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.update({"class": "form-select"})
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({"class": "form-textarea", "rows": 3})
            elif isinstance(field.widget, (forms.DateInput, forms.DateTimeInput)):
                field.widget.attrs.update({"class": "form-input", "type": "date"})
            else:
                field.widget.attrs.update({"class": "form-input"})


class ProductCategoryForm(BaseSalesForm):
    class Meta:
        model = ProductCategory
        fields = ["name", "code", "parent", "description", "is_active"]

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            qs = ProductCategory.objects.filter(organization=organization)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            self.fields["parent"].queryset = qs


class UnitOfMeasureForm(BaseSalesForm):
    class Meta:
        model = UnitOfMeasure
        fields = ["name", "code", "category", "is_base_unit", "ratio_to_base", "is_active"]


class ProductForm(BaseSalesForm):
    class Meta:
        model = Product
        fields = [
            "name",
            "sku",
            "barcode",
            "product_type",
            "category",
            "uom",
            "cost_price",
            "list_price",
            "currency",
            "taxable",
            "track_inventory",
            "is_active",
            "description",
        ]

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            self.fields["category"].queryset = ProductCategory.objects.filter(
                organization=organization, is_active=True
            )
            self.fields["uom"].queryset = UnitOfMeasure.objects.filter(
                organization=organization, is_active=True
            )


class PriceBookForm(BaseSalesForm):
    class Meta:
        model = PriceBook
        fields = [
            "name",
            "code",
            "description",
            "currency",
            "is_default",
            "is_active",
            "valid_from",
            "valid_to",
        ]
        widgets = {
            "valid_from": forms.DateInput(attrs={"type": "date"}),
            "valid_to": forms.DateInput(attrs={"type": "date"}),
        }


class PriceBookEntryForm(BaseSalesForm):
    class Meta:
        model = PriceBookEntry
        fields = ["product", "unit_price", "minimum_quantity", "is_active"]

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            self.fields["product"].queryset = Product.objects.filter(
                organization=organization, is_active=True
            )


class TieredDiscountForm(BaseSalesForm):
    class Meta:
        model = TieredDiscount
        fields = ["min_quantity", "max_quantity", "discount_type", "discount_value", "is_active"]


class QuoteForm(BaseSalesForm):
    class Meta:
        model = Quote
        fields = [
            "title",
            "account",
            "contact",
            "deal",
            "price_book",
            "valid_until",
            "payment_terms",
            "shipping_amount",
            "terms_and_conditions",
            "customer_notes",
            "internal_notes",
        ]
        widgets = {
            "valid_until": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            self.fields["account"].queryset = Account.objects.filter(organization=organization)
            self.fields["contact"].queryset = Contact.objects.filter(organization=organization)
            self.fields["deal"].queryset = Deal.objects.filter(organization=organization, is_closed=False)
            self.fields["price_book"].queryset = PriceBook.objects.filter(organization=organization, is_active=True)


class QuoteLineItemForm(BaseSalesForm):
    class Meta:
        model = QuoteLineItem
        fields = [
            "product",
            "description",
            "quantity",
            "unit_price",
            "discount_percent",
            "tax_rate",
        ]

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            self.fields["product"].queryset = Product.objects.filter(
                organization=organization, is_active=True
            )


class QuoteApprovalActionForm(forms.Form):
    decision = forms.ChoiceField(
        choices=[("approve", "Approve Quotation"), ("reject", "Reject Terms")],
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-textarea", "rows": 3, "placeholder": "Approval or rejection notes..."}),
    )


class SalesOrderForm(BaseSalesForm):
    class Meta:
        model = SalesOrder
        fields = [
            "account",
            "contact",
            "deal",
            "required_date",
            "payment_terms",
            "shipping_address",
            "billing_address",
            "shipping_amount",
            "customer_notes",
            "internal_notes",
        ]
        widgets = {
            "required_date": forms.DateInput(attrs={"type": "date"}),
            "shipping_address": forms.Textarea(attrs={"rows": 2}),
            "billing_address": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            self.fields["account"].queryset = Account.objects.filter(organization=organization)
            self.fields["contact"].queryset = Contact.objects.filter(organization=organization)
            self.fields["deal"].queryset = Deal.objects.filter(organization=organization)


class OrderLineItemForm(BaseSalesForm):
    class Meta:
        model = OrderLineItem
        fields = [
            "product",
            "description",
            "quantity_ordered",
            "unit_price",
            "discount_amount",
            "tax_amount",
        ]

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            self.fields["product"].queryset = Product.objects.filter(organization=organization, is_active=True)


class QuoteConvertForm(forms.Form):
    required_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "form-input", "type": "date"}),
    )
    shipping_address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-textarea", "rows": 2, "placeholder": "Shipping destination address..."}),
    )
    billing_address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-textarea", "rows": 2, "placeholder": "Billing invoice address..."}),
    )


