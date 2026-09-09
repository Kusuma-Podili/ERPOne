"""
EnterpriseOne Sales Views.
Handles Product Catalog, Categories, UOMs, Price Books, and Tiered Discounts.
"""
from django.contrib import messages
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
    View,
)
from apps.organizations.views import OrganizationAccessMixin
from .models import (
    Product,
    ProductCategory,
    UnitOfMeasure,
    PriceBook,
    PriceBookEntry,
    TieredDiscount,
)
from .forms import (
    ProductForm,
    ProductCategoryForm,
    PriceBookForm,
    PriceBookEntryForm,
    TieredDiscountForm,
)
from .services import PricingEngineService


class ProductListView(OrganizationAccessMixin, ListView):
    model = Product
    template_name = "sales/product_list.html"
    context_object_name = "products"
    paginate_by = 25

    def get_queryset(self):
        org = self.request.organization
        if not org:
            return Product.objects.none()
        qs = Product.objects.filter(organization=org).select_related("category", "uom")
        search = self.request.GET.get("q")
        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(sku__icontains=search)
                | Q(barcode__icontains=search)
                | Q(description__icontains=search)
            )
        category_id = self.request.GET.get("category")
        if category_id:
            qs = qs.filter(category_id=category_id)
        ptype = self.request.GET.get("type")
        if ptype:
            qs = qs.filter(product_type=ptype)
        status = self.request.GET.get("status")
        if status == "active":
            qs = qs.filter(is_active=True)
        elif status == "inactive":
            qs = qs.filter(is_active=False)
        return qs.order_by("name")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        org = self.request.organization
        if org:
            ctx["categories"] = ProductCategory.objects.filter(organization=org, is_active=True)
        ctx["current_category"] = self.request.GET.get("category", "")
        ctx["current_type"] = self.request.GET.get("type", "")
        ctx["current_status"] = self.request.GET.get("status", "")
        ctx["search_query"] = self.request.GET.get("q", "")
        return ctx


class ProductDetailView(OrganizationAccessMixin, DetailView):
    model = Product
    template_name = "sales/product_detail.html"
    context_object_name = "product"

    def get_queryset(self):
        org = self.request.organization
        if not org:
            return Product.objects.none()
        return Product.objects.filter(organization=org).select_related("category", "uom", "created_by")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        product = self.object
        ctx["price_entries"] = PriceBookEntry.objects.filter(
            product=product
        ).select_related("price_book").prefetch_related("tiered_discounts")
        return ctx


class ProductCreateView(OrganizationAccessMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = "sales/product_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.request.organization
        return kwargs

    def form_valid(self, form):
        form.instance.organization = self.request.organization
        form.instance.created_by = self.request.user
        messages.success(self.request, f"Product '{form.instance.name}' created successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("sales:product_detail", kwargs={"pk": self.object.pk})


class ProductUpdateView(OrganizationAccessMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = "sales/product_form.html"

    def get_queryset(self):
        org = self.request.organization
        return Product.objects.filter(organization=org)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.request.organization
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, f"Product '{form.instance.name}' updated successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("sales:product_detail", kwargs={"pk": self.object.pk})


class ProductDeleteView(OrganizationAccessMixin, DeleteView):
    model = Product
    template_name = "sales/product_confirm_delete.html"
    success_url = reverse_lazy("sales:product_list")

    def get_queryset(self):
        org = self.request.organization
        return Product.objects.filter(organization=org)

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        messages.success(request, f"Product '{obj.name}' was successfully deleted.")
        return super().delete(request, *args, **kwargs)


class PriceBookListView(OrganizationAccessMixin, ListView):
    model = PriceBook
    template_name = "sales/pricebook_list.html"
    context_object_name = "price_books"

    def get_queryset(self):
        org = self.request.organization
        if not org:
            return PriceBook.objects.none()
        return PriceBook.objects.filter(organization=org).annotate(
            entry_count=Count("entries")
        ).order_by("-is_default", "name")


class PriceBookDetailView(OrganizationAccessMixin, DetailView):
    model = PriceBook
    template_name = "sales/pricebook_detail.html"
    context_object_name = "price_book"

    def get_queryset(self):
        org = self.request.organization
        if not org:
            return PriceBook.objects.none()
        return PriceBook.objects.filter(organization=org)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["entries"] = self.object.entries.select_related("product", "product__uom").prefetch_related("tiered_discounts")
        ctx["entry_form"] = PriceBookEntryForm(organization=self.request.organization)
        return ctx


class PriceBookCreateView(OrganizationAccessMixin, CreateView):
    model = PriceBook
    form_class = PriceBookForm
    template_name = "sales/pricebook_form.html"

    def form_valid(self, form):
        form.instance.organization = self.request.organization
        form.instance.created_by = self.request.user
        messages.success(self.request, f"Price book '{form.instance.name}' created.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("sales:pricebook_detail", kwargs={"pk": self.object.pk})


class PriceBookUpdateView(OrganizationAccessMixin, UpdateView):
    model = PriceBook
    form_class = PriceBookForm
    template_name = "sales/pricebook_form.html"

    def get_queryset(self):
        org = self.request.organization
        return PriceBook.objects.filter(organization=org)

    def form_valid(self, form):
        messages.success(self.request, f"Price book '{form.instance.name}' updated.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("sales:pricebook_detail", kwargs={"pk": self.object.pk})


class PriceBookDeleteView(OrganizationAccessMixin, DeleteView):
    model = PriceBook
    template_name = "sales/pricebook_confirm_delete.html"
    success_url = reverse_lazy("sales:pricebook_list")

    def get_queryset(self):
        org = self.request.organization
        return PriceBook.objects.filter(organization=org, is_default=False)


class PriceBookEntryCreateView(OrganizationAccessMixin, View):
    """Adds a product price entry into a designated price book."""
    def post(self, request, pk):
        org = request.organization
        price_book = get_object_or_404(PriceBook, pk=pk, organization=org)
        form = PriceBookEntryForm(request.POST, organization=org)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.organization = org
            entry.price_book = price_book
            entry.save()
            messages.success(request, f"Added {entry.product.name} to {price_book.name}.")
        else:
            messages.error(request, "Failed to add price entry. Please check the form fields.")
        return redirect("sales:pricebook_detail", pk=price_book.pk)


class PriceBookEntryDeleteView(OrganizationAccessMixin, View):
    """Removes a product price entry from a price book."""
    def post(self, request, pk):
        org = request.organization
        entry = get_object_or_404(PriceBookEntry, pk=pk, organization=org)
        price_book_id = entry.price_book_id
        entry.delete()
        messages.success(request, "Price book entry removed.")
        return redirect("sales:pricebook_detail", pk=price_book_id)


class TieredDiscountCreateView(OrganizationAccessMixin, View):
    """Adds a tiered volume discount to a specific price book entry."""
    def post(self, request, entry_pk):
        org = request.organization
        entry = get_object_or_404(PriceBookEntry, pk=entry_pk, organization=org)
        form = TieredDiscountForm(request.POST)
        if form.is_valid():
            tier = form.save(commit=False)
            tier.organization = org
            tier.price_book_entry = entry
            tier.save()
            messages.success(request, f"Volume discount tier added for {entry.product.name}.")
        else:
            messages.error(request, "Failed to add tiered discount.")
        return redirect("sales:pricebook_detail", pk=entry.price_book_id)
