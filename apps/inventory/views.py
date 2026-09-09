"""
EnterpriseOne Inventory Views.
Implements views for Warehouse management, Storage Zones, Storage Locations, and Stock Level tracking.
"""
from decimal import Decimal
from django.contrib import messages
from django.db.models import Q, Count, Sum, F
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
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
from .models import (
    Warehouse,
    WarehouseType,
    StorageZone,
    StorageZoneType,
    StorageLocation,
    StockItem,
)
from .forms import (
    WarehouseForm,
    StorageZoneForm,
    StorageLocationForm,
    StockItemForm,
)
from .services import (
    WarehouseHierarchyService,
    StockLevelService,
)


class WarehouseListView(OrganizationAccessMixin, ListView):
    model = Warehouse
    template_name = "inventory/warehouse_list.html"
    context_object_name = "warehouses"
    paginate_by = 20

    def get_queryset(self):
        org = self.request.organization
        if not org:
            return Warehouse.objects.none()
        qs = Warehouse.objects.filter(organization=org).select_related("branch", "manager").annotate(
            zones_count=Count("zones", distinct=True),
            locations_count=Count("locations", distinct=True),
            items_count=Count("stock_items", distinct=True),
        )
        search = self.request.GET.get("q")
        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(code__icontains=search)
                | Q(city__icontains=search)
            )
        wh_type = self.request.GET.get("type")
        if wh_type:
            qs = qs.filter(warehouse_type=wh_type)
        return qs.order_by("-is_primary", "name")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["warehouse_types"] = WarehouseType.choices
        ctx["current_type"] = self.request.GET.get("type", "")
        ctx["search_query"] = self.request.GET.get("q", "")
        return ctx


class WarehouseDetailView(OrganizationAccessMixin, DetailView):
    model = Warehouse
    template_name = "inventory/warehouse_detail.html"
    context_object_name = "warehouse"

    def get_queryset(self):
        org = self.request.organization
        if not org:
            return Warehouse.objects.none()
        return Warehouse.objects.filter(organization=org).select_related("branch", "manager")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        wh = self.object
        ctx["zones"] = wh.zones.annotate(loc_count=Count("locations")).order_by("code")
        ctx["locations"] = wh.locations.select_related("zone").order_by("code")[:25]
        ctx["stock_items"] = wh.stock_items.select_related("product", "location").order_by("product__name")[:25]
        ctx["total_stock_count"] = wh.stock_items.count()
        ctx["zone_form"] = StorageZoneForm(organization=self.request.organization, initial={"warehouse": wh})
        ctx["location_form"] = StorageLocationForm(organization=self.request.organization, initial={"warehouse": wh})
        return ctx


class WarehouseCreateView(OrganizationAccessMixin, CreateView):
    model = Warehouse
    form_class = WarehouseForm
    template_name = "inventory/warehouse_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.request.organization
        return kwargs

    def form_valid(self, form):
        form.instance.organization = self.request.organization
        messages.success(self.request, f"Warehouse '{form.instance.name}' created successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("inventory:warehouse_detail", kwargs={"pk": self.object.pk})


class WarehouseUpdateView(OrganizationAccessMixin, UpdateView):
    model = Warehouse
    form_class = WarehouseForm
    template_name = "inventory/warehouse_form.html"

    def get_queryset(self):
        org = self.request.organization
        return Warehouse.objects.filter(organization=org)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.request.organization
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, f"Warehouse '{form.instance.name}' updated.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("inventory:warehouse_detail", kwargs={"pk": self.object.pk})


class WarehouseDeleteView(OrganizationAccessMixin, DeleteView):
    model = Warehouse
    template_name = "inventory/warehouse_confirm_delete.html"
    success_url = reverse_lazy("inventory:warehouse_list")

    def get_queryset(self):
        org = self.request.organization
        return Warehouse.objects.filter(organization=org)

    def form_valid(self, form):
        messages.success(self.request, f"Warehouse '{self.object.name}' was removed.")
        return super().form_valid(form)


# =====================================================================
# STORAGE ZONE VIEWS
# =====================================================================

class StorageZoneCreateView(OrganizationAccessMixin, CreateView):
    model = StorageZone
    form_class = StorageZoneForm
    template_name = "inventory/zone_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.request.organization
        return kwargs

    def form_valid(self, form):
        form.instance.organization = self.request.organization
        zone = form.save()
        messages.success(self.request, f"Storage zone '{zone.name}' added.")
        return redirect("inventory:warehouse_detail", pk=zone.warehouse_id)


class StorageZoneDeleteView(OrganizationAccessMixin, View):
    def post(self, request, pk):
        org = request.organization
        zone = get_object_or_404(StorageZone, pk=pk, organization=org)
        wh_id = zone.warehouse_id
        zone.delete()
        messages.success(request, "Storage zone removed.")
        return redirect("inventory:warehouse_detail", pk=wh_id)


# =====================================================================
# STORAGE LOCATION VIEWS
# =====================================================================

class StorageLocationCreateView(OrganizationAccessMixin, CreateView):
    model = StorageLocation
    form_class = StorageLocationForm
    template_name = "inventory/location_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.request.organization
        return kwargs

    def form_valid(self, form):
        form.instance.organization = self.request.organization
        loc = form.save()
        messages.success(self.request, f"Storage location '{loc.code}' created.")
        return redirect("inventory:warehouse_detail", pk=loc.warehouse_id)


class StorageLocationDeleteView(OrganizationAccessMixin, View):
    def post(self, request, pk):
        org = request.organization
        loc = get_object_or_404(StorageLocation, pk=pk, organization=org)
        wh_id = loc.warehouse_id
        loc.delete()
        messages.success(request, "Storage location deleted.")
        return redirect("inventory:warehouse_detail", pk=wh_id)


# =====================================================================
# STOCK ITEM / INVENTORY LEVEL VIEWS
# =====================================================================

class StockItemListView(OrganizationAccessMixin, ListView):
    model = StockItem
    template_name = "inventory/stock_list.html"
    context_object_name = "stock_items"
    paginate_by = 30

    def get_queryset(self):
        org = self.request.organization
        if not org:
            return StockItem.objects.none()
        qs = StockItem.objects.filter(organization=org).select_related("product", "warehouse", "location")

        wh_id = self.request.GET.get("warehouse")
        if wh_id:
            qs = qs.filter(warehouse_id=wh_id)

        search = self.request.GET.get("q")
        if search:
            qs = qs.filter(
                Q(product__name__icontains=search)
                | Q(product__sku__icontains=search)
                | Q(warehouse__name__icontains=search)
                | Q(location__code__icontains=search)
            )

        alert = self.request.GET.get("alert")
        if alert == "reorder":
            qs = qs.filter(quantity_on_hand__lte=F("reorder_point"))
        elif alert == "safety":
            qs = qs.filter(quantity_on_hand__lte=F("safety_stock"))

        return qs.order_by("product__name", "warehouse__code")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        org = self.request.organization
        ctx["warehouses"] = Warehouse.objects.filter(organization=org, is_active=True)
        ctx["current_warehouse"] = self.request.GET.get("warehouse", "")
        ctx["current_alert"] = self.request.GET.get("alert", "")
        ctx["search_query"] = self.request.GET.get("q", "")
        return ctx


class StockItemDetailView(OrganizationAccessMixin, DetailView):
    model = StockItem
    template_name = "inventory/stock_detail.html"
    context_object_name = "stock_item"

    def get_queryset(self):
        org = self.request.organization
        if not org:
            return StockItem.objects.none()
        return StockItem.objects.filter(organization=org).select_related("product", "warehouse", "location")


class StockItemCreateView(OrganizationAccessMixin, CreateView):
    model = StockItem
    form_class = StockItemForm
    template_name = "inventory/stock_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.request.organization
        return kwargs

    def form_valid(self, form):
        form.instance.organization = self.request.organization
        messages.success(self.request, f"Inventory level for '{form.instance.product.name}' recorded.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("inventory:stock_list")


class StockItemUpdateView(OrganizationAccessMixin, UpdateView):
    model = StockItem
    form_class = StockItemForm
    template_name = "inventory/stock_form.html"

    def get_queryset(self):
        org = self.request.organization
        return StockItem.objects.filter(organization=org)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.request.organization
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, f"Inventory level for '{form.instance.product.name}' updated.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("inventory:stock_list")
