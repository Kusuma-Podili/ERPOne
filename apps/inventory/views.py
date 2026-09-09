"""
EnterpriseOne Inventory Views.
Implements views for Warehouse management, Storage Zones, Storage Locations, and Stock Level tracking.
"""
from decimal import Decimal
from django.contrib import messages
from django.db.models import Q, Count, Sum, F
from django.shortcuts import get_object_or_404, redirect, render
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
from apps.sales.models import Product
from .models import (
    Warehouse,
    WarehouseType,
    StorageZone,
    StorageZoneType,
    StorageLocation,
    StockItem,
    StockMovement,
    StockMovementType,
    StockMovementStatus,
    StockMovementLine,
    QCStatus,
    SerialStatus,
    LotBatch,
    SerialNumber,
    ReorderRule,
    RequisitionStatus,
    RequisitionPriority,
    PurchaseRequisition,
    PurchaseRequisitionLine,
)
from .forms import (
    WarehouseForm,
    StorageZoneForm,
    StorageLocationForm,
    StockItemForm,
    StockMovementForm,
    StockMovementLineFormSet,
    StockQuickAdjustmentForm,
    LotBatchForm,
    LotBatchQCUpdateForm,
    SerialNumberForm,
    SerialNumberBulkCreateForm,
    ReorderRuleForm,
    PurchaseRequisitionForm,
    PurchaseRequisitionLineFormSet,
)
from .services import (
    WarehouseHierarchyService,
    StockLevelService,
    StockMovementService,
    LotSerialTrackingService,
    ReplenishmentService,
    InventoryAnalyticsService,
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


# ==============================================================================
# STOCK MOVEMENT LEDGER & ADJUSTMENT VIEWS (Milestone 5.2)
# ==============================================================================

class StockMovementListView(OrganizationAccessMixin, ListView):
    model = StockMovement
    template_name = "inventory/movement_list.html"
    context_object_name = "movements"
    paginate_by = 20

    def get_queryset(self):
        org = self.request.organization
        if not org:
            return StockMovement.objects.none()

        qs = StockMovement.objects.filter(organization=org).select_related(
            "source_warehouse",
            "destination_warehouse",
            "created_by",
            "posted_by",
        ).prefetch_related("lines__product")

        # Filtering
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(movement_number__icontains=q) |
                Q(reference_document__icontains=q) |
                Q(notes__icontains=q)
            )

        movement_type = self.request.GET.get("type", "").strip()
        if movement_type:
            qs = qs.filter(movement_type=movement_type)

        status = self.request.GET.get("status", "").strip()
        if status:
            qs = qs.filter(status=status)

        warehouse_id = self.request.GET.get("warehouse", "").strip()
        if warehouse_id:
            qs = qs.filter(
                Q(source_warehouse_id=warehouse_id) |
                Q(destination_warehouse_id=warehouse_id)
            )

        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        org = self.request.organization
        context["movement_types"] = StockMovementType.choices
        context["movement_statuses"] = StockMovementStatus.choices
        context["warehouses"] = Warehouse.objects.filter(organization=org, is_active=True) if org else []
        context["current_q"] = self.request.GET.get("q", "")
        context["current_type"] = self.request.GET.get("type", "")
        context["current_status"] = self.request.GET.get("status", "")
        context["current_warehouse"] = self.request.GET.get("warehouse", "")
        return context


class StockMovementDetailView(OrganizationAccessMixin, DetailView):
    model = StockMovement
    template_name = "inventory/movement_detail.html"
    context_object_name = "movement"

    def get_queryset(self):
        org = self.request.organization
        if not org:
            return StockMovement.objects.none()
        return StockMovement.objects.filter(organization=org).select_related(
            "source_warehouse",
            "destination_warehouse",
            "created_by",
            "posted_by",
        ).prefetch_related(
            "lines__product",
            "lines__source_location",
            "lines__destination_location",
        )


class StockMovementCreateView(OrganizationAccessMixin, CreateView):
    model = StockMovement
    form_class = StockMovementForm
    template_name = "inventory/movement_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.request.organization
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        org = self.request.organization
        if self.request.POST:
            context["formset"] = StockMovementLineFormSet(self.request.POST)
        else:
            context["formset"] = StockMovementLineFormSet()
            # Bound queryset for products in formset
            for line_form in context["formset"].forms:
                line_form.fields["product"].queryset = Product.objects.filter(organization=org, is_active=True)
                line_form.fields["source_location"].queryset = StorageLocation.objects.filter(organization=org, is_active=True)
                line_form.fields["destination_location"].queryset = StorageLocation.objects.filter(organization=org, is_active=True)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context["formset"]

        if formset.is_valid():
            form.instance.organization = self.request.organization
            form.instance.created_by = self.request.user
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            messages.success(self.request, f"Stock movement draft '{self.object.movement_number}' created.")
            return redirect("inventory:movement_detail", pk=self.object.pk)
        else:
            return self.form_invalid(form)


class StockMovementPostView(OrganizationAccessMixin, View):
    def post(self, request, pk, *args, **kwargs):
        org = request.organization
        movement = get_object_or_404(StockMovement, pk=pk, organization=org)
        from django.core.exceptions import ValidationError
        try:
            StockMovementService.post_movement(movement, posted_by=request.user)
            messages.success(request, f"Stock movement '{movement.movement_number}' posted successfully. Inventory balances updated.")
        except ValidationError as e:
            messages.error(request, f"Cannot post movement: {e.message if hasattr(e, 'message') else e}")
        return redirect("inventory:movement_detail", pk=movement.pk)


class StockMovementCancelView(OrganizationAccessMixin, View):
    def post(self, request, pk, *args, **kwargs):
        org = request.organization
        movement = get_object_or_404(StockMovement, pk=pk, organization=org)
        reason = request.POST.get("reason", "Cancelled by user.")
        from django.core.exceptions import ValidationError
        try:
            StockMovementService.cancel_movement(movement, cancelled_by=request.user, reason=reason)
            messages.info(request, f"Stock movement '{movement.movement_number}' cancelled.")
        except ValidationError as e:
            messages.error(request, f"Cannot cancel movement: {e.message if hasattr(e, 'message') else e}")
        return redirect("inventory:movement_detail", pk=movement.pk)


class StockMovementPrintView(OrganizationAccessMixin, DetailView):
    model = StockMovement
    template_name = "inventory/movement_print.html"
    context_object_name = "movement"

    def get_queryset(self):
        org = self.request.organization
        if not org:
            return StockMovement.objects.none()
        return StockMovement.objects.filter(organization=org).select_related(
            "organization",
            "source_warehouse",
            "destination_warehouse",
            "created_by",
            "posted_by",
        ).prefetch_related(
            "lines__product",
            "lines__source_location",
            "lines__destination_location",
        )


class StockLedgerView(OrganizationAccessMixin, ListView):
    template_name = "inventory/stock_ledger.html"
    context_object_name = "ledger_entries"
    paginate_by = 30

    def get_queryset(self):
        org = self.request.organization
        if not org:
            return StockMovementLine.objects.none()

        product_id = self.request.GET.get("product")
        warehouse_id = self.request.GET.get("warehouse")
        product = Product.objects.filter(id=product_id, organization=org).first() if product_id else None
        warehouse = Warehouse.objects.filter(id=warehouse_id, organization=org).first() if warehouse_id else None

        return StockMovementService.get_ledger_history(
            organization=org,
            product=product,
            warehouse=warehouse,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        org = self.request.organization
        context["products"] = Product.objects.filter(organization=org, is_active=True).order_by("name") if org else []
        context["warehouses"] = Warehouse.objects.filter(organization=org, is_active=True).order_by("name") if org else []
        context["selected_product"] = self.request.GET.get("product", "")
        context["selected_warehouse"] = self.request.GET.get("warehouse", "")
        return context


# ==============================================================================
# LOT / BATCH & SERIAL NUMBER VIEWS (Milestone 5.3)
# ==============================================================================

class LotBatchListView(OrganizationAccessMixin, ListView):
    model = LotBatch
    template_name = "inventory/lot_list.html"
    context_object_name = "lots"
    paginate_by = 25

    def get_queryset(self):
        org = self.request.organization
        if not org:
            return LotBatch.objects.none()

        qs = LotBatch.objects.filter(organization=org).select_related("product", "qc_inspected_by")

        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(batch_number__icontains=q) |
                Q(supplier_lot_number__icontains=q) |
                Q(product__name__icontains=q) |
                Q(product__sku__icontains=q)
            )

        qc = self.request.GET.get("qc", "").strip()
        if qc:
            qs = qs.filter(qc_status=qc)

        prod_id = self.request.GET.get("product", "").strip()
        if prod_id:
            qs = qs.filter(product_id=prod_id)

        return qs.order_by("expiration_date", "-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        org = self.request.organization
        context["qc_statuses"] = QCStatus.choices
        context["products"] = Product.objects.filter(organization=org, is_active=True).order_by("name") if org else []
        context["current_q"] = self.request.GET.get("q", "")
        context["current_qc"] = self.request.GET.get("qc", "")
        context["current_product"] = self.request.GET.get("product", "")
        return context


class LotBatchDetailView(OrganizationAccessMixin, DetailView):
    model = LotBatch
    template_name = "inventory/lot_detail.html"
    context_object_name = "lot"

    def get_queryset(self):
        org = self.request.organization
        if not org:
            return LotBatch.objects.none()
        return LotBatch.objects.filter(organization=org).select_related("product", "qc_inspected_by").prefetch_related("serials")


class LotBatchCreateView(OrganizationAccessMixin, CreateView):
    model = LotBatch
    form_class = LotBatchForm
    template_name = "inventory/lot_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.request.organization
        return kwargs

    def form_valid(self, form):
        form.instance.organization = self.request.organization
        form.instance.current_quantity = form.cleaned_data.get("initial_quantity", Decimal("0.00"))
        messages.success(self.request, f"Lot/Batch '{form.instance.batch_number}' registered successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("inventory:lot_detail", kwargs={"pk": self.object.pk})


class LotBatchQCUpdateView(OrganizationAccessMixin, UpdateView):
    model = LotBatch
    form_class = LotBatchQCUpdateForm
    template_name = "inventory/lot_qc_form.html"

    def get_queryset(self):
        org = self.request.organization
        return LotBatch.objects.filter(organization=org)

    def form_valid(self, form):
        lot = form.instance
        LotSerialTrackingService.update_qc_status(
            lot=lot,
            new_status=form.cleaned_data["qc_status"],
            inspected_by=self.request.user,
            qc_notes=form.cleaned_data.get("qc_notes", ""),
        )
        messages.success(self.request, f"QC Status for Lot '{lot.batch_number}' updated to '{lot.get_qc_status_display()}'.")
        return redirect("inventory:lot_detail", pk=lot.pk)


class SerialNumberListView(OrganizationAccessMixin, ListView):
    model = SerialNumber
    template_name = "inventory/serial_list.html"
    context_object_name = "serials"
    paginate_by = 30

    def get_queryset(self):
        org = self.request.organization
        if not org:
            return SerialNumber.objects.none()

        qs = SerialNumber.objects.filter(organization=org).select_related(
            "product", "lot", "warehouse", "location"
        )

        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(serial_number__icontains=q) |
                Q(product__sku__icontains=q) |
                Q(product__name__icontains=q) |
                Q(lot__batch_number__icontains=q)
            )

        status = self.request.GET.get("status", "").strip()
        if status:
            qs = qs.filter(status=status)

        wh_id = self.request.GET.get("warehouse", "").strip()
        if wh_id:
            qs = qs.filter(warehouse_id=wh_id)

        return qs.order_by("product__name", "serial_number")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        org = self.request.organization
        context["serial_statuses"] = SerialStatus.choices
        context["warehouses"] = Warehouse.objects.filter(organization=org, is_active=True) if org else []
        context["current_q"] = self.request.GET.get("q", "")
        context["current_status"] = self.request.GET.get("status", "")
        context["current_warehouse"] = self.request.GET.get("warehouse", "")
        return context


class SerialNumberDetailView(OrganizationAccessMixin, DetailView):
    model = SerialNumber
    template_name = "inventory/serial_detail.html"
    context_object_name = "serial"

    def get_queryset(self):
        org = self.request.organization
        if not org:
            return SerialNumber.objects.none()
        return SerialNumber.objects.filter(organization=org).select_related(
            "product", "lot", "warehouse", "location"
        )


class SerialNumberBulkCreateView(OrganizationAccessMixin, View):
    template_name = "inventory/serial_bulk_form.html"

    def get(self, request, *args, **kwargs):
        form = SerialNumberBulkCreateForm(organization=request.organization)
        return render(request, self.template_name, {"form": form})

    def post(self, request, *args, **kwargs):
        form = SerialNumberBulkCreateForm(request.POST, organization=request.organization)
        if form.is_valid():
            lines = form.cleaned_data["serial_numbers_text"].splitlines()
            created_serials = LotSerialTrackingService.bulk_register_serials(
                organization=request.organization,
                product=form.cleaned_data["product"],
                serial_numbers_list=lines,
                lot=form.cleaned_data.get("lot"),
                warehouse=form.cleaned_data.get("warehouse"),
                location=form.cleaned_data.get("location"),
                warranty_start_date=form.cleaned_data.get("warranty_start_date"),
                warranty_end_date=form.cleaned_data.get("warranty_end_date"),
            )
            messages.success(request, f"Successfully registered {len(created_serials)} serial numbers.")
            return redirect("inventory:serial_list")
        return render(request, self.template_name, {"form": form})


class ExpiringStockReportView(OrganizationAccessMixin, TemplateView):
    template_name = "inventory/expiring_stock.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        org = self.request.organization
        days = int(self.request.GET.get("days", 30))
        prod_id = self.request.GET.get("product", "")
        product = Product.objects.filter(id=prod_id, organization=org).first() if prod_id else None

        context["days"] = days
        context["expiring_lots"] = LotSerialTrackingService.get_expiring_batches(
            organization=org,
            days_threshold=days,
            product=product,
        ) if org else []
        context["products"] = Product.objects.filter(organization=org, is_active=True).order_by("name") if org else []
        context["selected_product"] = prod_id
        return context


# ==============================================================================
# INVENTORY DASHBOARD, REORDER RULES & REQUISITIONS (Milestone 5.4)
# ==============================================================================

class InventoryDashboardView(OrganizationAccessMixin, TemplateView):
    template_name = "inventory/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        org = self.request.organization
        if not org:
            return context

        context["kpis"] = InventoryAnalyticsService.get_inventory_kpis(org)
        context["recent_movements"] = StockMovement.objects.filter(
            organization=org
        ).select_related("source_warehouse", "destination_warehouse")[:6]
        context["low_stock_items"] = StockLevelService.get_reorder_alerts(org)[:6]
        context["expiring_lots"] = LotSerialTrackingService.get_expiring_batches(org, days_threshold=30)[:5]
        context["warehouses"] = Warehouse.objects.filter(organization=org, is_active=True)
        return context


class ReplenishmentScanTriggerView(OrganizationAccessMixin, View):
    def post(self, request, *args, **kwargs):
        org = request.organization
        warehouse_id = request.POST.get("warehouse_id")
        warehouse = Warehouse.objects.filter(id=warehouse_id, organization=org).first() if warehouse_id else None

        created_reqs = ReplenishmentService.evaluate_reorder_triggers(
            organization=org,
            warehouse=warehouse,
            requested_by=request.user,
        )
        if created_reqs:
            messages.success(
                request,
                f"Automated scan completed: Generated {len(created_reqs)} purchase replenishment requisition(s)."
            )
        else:
            messages.info(request, "Replenishment scan completed: All stock levels are currently above minimum safety thresholds.")

        return redirect("inventory:requisition_list")


class ReorderRuleListView(OrganizationAccessMixin, ListView):
    model = ReorderRule
    template_name = "inventory/reorder_rule_list.html"
    context_object_name = "rules"
    paginate_by = 25

    def get_queryset(self):
        org = self.request.organization
        if not org:
            return ReorderRule.objects.none()
        return ReorderRule.objects.filter(organization=org).select_related("warehouse", "product")


class ReorderRuleCreateView(OrganizationAccessMixin, CreateView):
    model = ReorderRule
    form_class = ReorderRuleForm
    template_name = "inventory/reorder_rule_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.request.organization
        return kwargs

    def form_valid(self, form):
        form.instance.organization = self.request.organization
        messages.success(self.request, f"Reorder policy for '{form.instance.product.name}' saved.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("inventory:reorder_rule_list")


class ReorderRuleUpdateView(OrganizationAccessMixin, UpdateView):
    model = ReorderRule
    form_class = ReorderRuleForm
    template_name = "inventory/reorder_rule_form.html"

    def get_queryset(self):
        org = self.request.organization
        return ReorderRule.objects.filter(organization=org)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.request.organization
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, f"Reorder policy for '{form.instance.product.name}' updated.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("inventory:reorder_rule_list")


class PurchaseRequisitionListView(OrganizationAccessMixin, ListView):
    model = PurchaseRequisition
    template_name = "inventory/requisition_list.html"
    context_object_name = "requisitions"
    paginate_by = 20

    def get_queryset(self):
        org = self.request.organization
        if not org:
            return PurchaseRequisition.objects.none()

        qs = PurchaseRequisition.objects.filter(organization=org).select_related(
            "warehouse", "requested_by", "approved_by"
        )
        status = self.request.GET.get("status", "").strip()
        if status:
            qs = qs.filter(status=status)
        priority = self.request.GET.get("priority", "").strip()
        if priority:
            qs = qs.filter(priority=priority)
        wh = self.request.GET.get("warehouse", "").strip()
        if wh:
            qs = qs.filter(warehouse_id=wh)
        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        org = self.request.organization
        context["statuses"] = RequisitionStatus.choices
        context["priorities"] = RequisitionPriority.choices
        context["warehouses"] = Warehouse.objects.filter(organization=org, is_active=True) if org else []
        context["current_status"] = self.request.GET.get("status", "")
        context["current_priority"] = self.request.GET.get("priority", "")
        context["current_warehouse"] = self.request.GET.get("warehouse", "")
        return context


class PurchaseRequisitionDetailView(OrganizationAccessMixin, DetailView):
    model = PurchaseRequisition
    template_name = "inventory/requisition_detail.html"
    context_object_name = "requisition"

    def get_queryset(self):
        org = self.request.organization
        if not org:
            return PurchaseRequisition.objects.none()
        return PurchaseRequisition.objects.filter(organization=org).select_related(
            "warehouse", "requested_by", "approved_by"
        ).prefetch_related("lines__product")


class PurchaseRequisitionCreateView(OrganizationAccessMixin, CreateView):
    model = PurchaseRequisition
    form_class = PurchaseRequisitionForm
    template_name = "inventory/requisition_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.request.organization
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        org = self.request.organization
        if self.request.POST:
            context["formset"] = PurchaseRequisitionLineFormSet(self.request.POST)
        else:
            context["formset"] = PurchaseRequisitionLineFormSet()
            for form in context["formset"].forms:
                form.fields["product"].queryset = Product.objects.filter(organization=org, is_active=True)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context["formset"]
        if formset.is_valid():
            form.instance.organization = self.request.organization
            form.instance.requested_by = self.request.user
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            messages.success(self.request, f"Requisition '{self.object.requisition_number}' created.")
            return redirect("inventory:requisition_detail", pk=self.object.pk)
        return self.form_invalid(form)


class PurchaseRequisitionApproveView(OrganizationAccessMixin, View):
    def post(self, request, pk, *args, **kwargs):
        org = request.organization
        req = get_object_or_404(PurchaseRequisition, pk=pk, organization=org)
        try:
            ReplenishmentService.approve_requisition(req, approved_by=request.user)
            messages.success(request, f"Purchase requisition '{req.requisition_number}' approved.")
        except ValidationError as e:
            messages.error(request, f"Cannot approve requisition: {e.message if hasattr(e, 'message') else e}")
        return redirect("inventory:requisition_detail", pk=req.pk)


class PurchaseRequisitionCancelView(OrganizationAccessMixin, View):
    def post(self, request, pk, *args, **kwargs):
        org = request.organization
        req = get_object_or_404(PurchaseRequisition, pk=pk, organization=org)
        reason = request.POST.get("reason", "Cancelled by user.")
        try:
            ReplenishmentService.cancel_requisition(req, cancelled_by=request.user, reason=reason)
            messages.info(request, f"Requisition '{req.requisition_number}' cancelled.")
        except ValidationError as e:
            messages.error(request, f"Cannot cancel requisition: {e.message if hasattr(e, 'message') else e}")
        return redirect("inventory:requisition_detail", pk=req.pk)
