"""
EnterpriseOne Procurement Views (Milestone 6.1).
Provides multi-tenant views for Supplier management, Contact directories, and Vendor Product Catalogs.
"""
from decimal import Decimal
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    TemplateView,
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
    View,
)
from apps.organizations.views import OrganizationAccessMixin
from apps.sales.models import Product
from .models import (
    Supplier,
    SupplierType,
    PaymentTerms,
    SupplierStatus,
    SupplierContact,
    SupplierProduct,
)
from .forms import (
    SupplierForm,
    SupplierContactForm,
    SupplierProductForm,
)
from .services import SupplierService


class SupplierListView(OrganizationAccessMixin, ListView):
    model = Supplier
    template_name = "procurement/supplier_list.html"
    context_object_name = "suppliers"
    paginate_by = 25

    def get_queryset(self):
        org = self.request.organization
        if not org:
            return Supplier.objects.none()

        qs = Supplier.objects.filter(organization=org)
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(code__icontains=q) |
                Q(tax_id__icontains=q) |
                Q(city__icontains=q) |
                Q(email__icontains=q)
            )

        supplier_type = self.request.GET.get("type", "").strip()
        if supplier_type:
            qs = qs.filter(supplier_type=supplier_type)

        status = self.request.GET.get("status", "").strip()
        if status:
            qs = qs.filter(status=status)

        return qs.order_by("name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["supplier_types"] = SupplierType.choices
        context["supplier_statuses"] = SupplierStatus.choices
        context["current_q"] = self.request.GET.get("q", "")
        context["current_type"] = self.request.GET.get("type", "")
        context["current_status"] = self.request.GET.get("status", "")
        return context


class SupplierDetailView(OrganizationAccessMixin, DetailView):
    model = Supplier
    template_name = "procurement/supplier_detail.html"
    context_object_name = "supplier"

    def get_queryset(self):
        org = self.request.organization
        if not org:
            return Supplier.objects.none()
        return Supplier.objects.filter(organization=org).prefetch_related("contacts", "supplied_products__product")


class SupplierCreateView(OrganizationAccessMixin, CreateView):
    model = Supplier
    form_class = SupplierForm
    template_name = "procurement/supplier_form.html"

    def form_valid(self, form):
        form.instance.organization = self.request.organization
        messages.success(self.request, f"Supplier '{form.instance.name}' registered successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("procurement:supplier_detail", kwargs={"pk": self.object.pk})


class SupplierUpdateView(OrganizationAccessMixin, UpdateView):
    model = Supplier
    form_class = SupplierForm
    template_name = "procurement/supplier_form.html"

    def get_queryset(self):
        org = self.request.organization
        return Supplier.objects.filter(organization=org)

    def form_valid(self, form):
        messages.success(self.request, f"Supplier '{form.instance.name}' profile updated.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("procurement:supplier_detail", kwargs={"pk": self.object.pk})


class SupplierDeleteView(OrganizationAccessMixin, DeleteView):
    model = Supplier
    template_name = "procurement/supplier_confirm_delete.html"
    success_url = reverse_lazy("procurement:supplier_list")

    def get_queryset(self):
        org = self.request.organization
        return Supplier.objects.filter(organization=org)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Supplier record deleted.")
        return super().delete(request, *args, **kwargs)


class SupplierContactCreateView(OrganizationAccessMixin, CreateView):
    model = SupplierContact
    form_class = SupplierContactForm
    template_name = "procurement/supplier_contact_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.supplier = get_object_or_404(Supplier, pk=kwargs["supplier_pk"], organization=request.organization)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["supplier"] = self.supplier
        return context

    def form_valid(self, form):
        form.instance.supplier = self.supplier
        if form.instance.is_primary:
            self.supplier.contacts.filter(is_primary=True).update(is_primary=False)
        messages.success(self.request, f"Contact '{form.instance.name}' added to {self.supplier.name}.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("procurement:supplier_detail", kwargs={"pk": self.supplier.pk})


class SupplierProductCreateView(OrganizationAccessMixin, CreateView):
    model = SupplierProduct
    form_class = SupplierProductForm
    template_name = "procurement/supplier_product_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.supplier = get_object_or_404(Supplier, pk=kwargs["supplier_pk"], organization=request.organization)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.request.organization
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["supplier"] = self.supplier
        return context

    def form_valid(self, form):
        form.instance.organization = self.request.organization
        form.instance.supplier = self.supplier
        if form.instance.is_preferred:
            SupplierProduct.objects.filter(
                organization=self.request.organization,
                product=form.instance.product,
                is_preferred=True,
            ).exclude(supplier=self.supplier).update(is_preferred=False)
        messages.success(self.request, f"Catalog offering for '{form.instance.product.name}' recorded.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("procurement:supplier_detail", kwargs={"pk": self.supplier.pk})
