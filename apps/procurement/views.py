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


from .models import (
    RFQStatus,
    RequestForQuotation,
    RFQLine,
    RFQVendorInvitation,
    VendorBid,
    VendorBidLine,
)
from .forms import (
    RFQForm,
    RFQLineFormSet,
    RFQInviteVendorForm,
    VendorBidForm,
    VendorBidLineFormSet,
    AwardBidForm,
)
from .services import RFQService


class RFQListView(OrganizationAccessMixin, ListView):
    model = RequestForQuotation
    template_name = "procurement/rfq_list.html"
    context_object_name = "rfqs"
    paginate_by = 25

    def get_queryset(self):
        org = self.request.organization
        if not org:
            return RequestForQuotation.objects.none()

        qs = RequestForQuotation.objects.filter(organization=org).select_related("created_by")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(rfq_number__icontains=q) |
                Q(title__icontains=q) |
                Q(notes__icontains=q)
            )

        status = self.request.GET.get("status", "").strip()
        if status:
            qs = qs.filter(status=status)

        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["rfq_statuses"] = RFQStatus.choices
        context["current_q"] = self.request.GET.get("q", "")
        context["current_status"] = self.request.GET.get("status", "")
        return context


class RFQDetailView(OrganizationAccessMixin, DetailView):
    model = RequestForQuotation
    template_name = "procurement/rfq_detail.html"
    context_object_name = "rfq"

    def get_queryset(self):
        org = self.request.organization
        if not org:
            return RequestForQuotation.objects.none()
        return RequestForQuotation.objects.filter(organization=org).prefetch_related(
            "lines__product",
            "lines__uom",
            "invitations__supplier",
            "bids__supplier",
            "bids__lines__rfq_line",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["invite_form"] = RFQInviteVendorForm(organization=self.request.organization, rfq=self.object)
        context["award_form"] = AwardBidForm()
        return context


class RFQCreateView(OrganizationAccessMixin, View):
    def get(self, request, *args, **kwargs):
        form = RFQForm()
        formset = RFQLineFormSet(form_kwargs={"organization": request.organization})
        return render(request, "procurement/rfq_form.html", {
            "form": form,
            "formset": formset,
            "title": "Create Request for Quotation (RFQ)",
        })

    def post(self, request, *args, **kwargs):
        form = RFQForm(request.POST)
        formset = RFQLineFormSet(request.POST, form_kwargs={"organization": request.organization})

        if form.is_valid() and formset.is_valid():
            rfq = form.save(commit=False)
            rfq.organization = request.organization
            rfq.rfq_number = RequestForQuotation.generate_rfq_number(request.organization)
            rfq.created_by = request.user
            rfq.save()

            lines = formset.save(commit=False)
            for idx, line in enumerate(lines, start=1):
                line.rfq = rfq
                line.line_number = idx
                line.save()

            messages.success(request, f"RFQ '{rfq.rfq_number}' drafted successfully.")
            return redirect("procurement:rfq_detail", pk=rfq.pk)

        return render(request, "procurement/rfq_form.html", {
            "form": form,
            "formset": formset,
            "title": "Create Request for Quotation (RFQ)",
        })


class RFQUpdateView(OrganizationAccessMixin, View):
    def dispatch(self, request, *args, **kwargs):
        self.rfq = get_object_or_404(RequestForQuotation, pk=kwargs["pk"], organization=request.organization)
        if self.rfq.status != RFQStatus.DRAFT:
            messages.error(request, "Only draft RFQs can be edited.")
            return redirect("procurement:rfq_detail", pk=self.rfq.pk)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = RFQForm(instance=self.rfq)
        formset = RFQLineFormSet(instance=self.rfq, form_kwargs={"organization": request.organization})
        return render(request, "procurement/rfq_form.html", {
            "form": form,
            "formset": formset,
            "rfq": self.rfq,
            "title": f"Edit {self.rfq.rfq_number}",
        })

    def post(self, request, *args, **kwargs):
        form = RFQForm(request.POST, instance=self.rfq)
        formset = RFQLineFormSet(request.POST, instance=self.rfq, form_kwargs={"organization": request.organization})

        if form.is_valid() and formset.is_valid():
            rfq = form.save()
            lines = formset.save(commit=False)
            for idx, line in enumerate(lines, start=1):
                line.rfq = rfq
                line.line_number = idx
                line.save()
            for obj in formset.deleted_objects:
                obj.delete()

            messages.success(request, f"RFQ '{rfq.rfq_number}' updated.")
            return redirect("procurement:rfq_detail", pk=rfq.pk)

        return render(request, "procurement/rfq_form.html", {
            "form": form,
            "formset": formset,
            "rfq": self.rfq,
            "title": f"Edit {self.rfq.rfq_number}",
        })


class RFQPublishView(OrganizationAccessMixin, View):
    def post(self, request, *args, **kwargs):
        rfq = get_object_or_404(RequestForQuotation, pk=kwargs["pk"], organization=request.organization)
        try:
            RFQService.publish_rfq(rfq)
            messages.success(request, f"RFQ '{rfq.rfq_number}' published and open for bids.")
        except ValidationError as e:
            messages.error(request, f"Cannot publish RFQ: {e.message if hasattr(e, 'message') else e}")
        return redirect("procurement:rfq_detail", pk=rfq.pk)


class RFQInviteView(OrganizationAccessMixin, View):
    def post(self, request, *args, **kwargs):
        rfq = get_object_or_404(RequestForQuotation, pk=kwargs["pk"], organization=request.organization)
        form = RFQInviteVendorForm(request.POST, organization=request.organization, rfq=rfq)
        if form.is_valid():
            suppliers = form.cleaned_data["suppliers"]
            invitations = RFQService.invite_vendors(rfq, suppliers, invited_by=request.user)
            messages.success(request, f"Sent bidding invitations to {len(invitations)} suppliers.")
        else:
            messages.error(request, "No suppliers selected or invalid selection.")
        return redirect("procurement:rfq_detail", pk=rfq.pk)


class VendorBidCreateView(OrganizationAccessMixin, View):
    def dispatch(self, request, *args, **kwargs):
        self.rfq = get_object_or_404(RequestForQuotation, pk=kwargs["rfq_pk"], organization=request.organization)
        if not self.rfq.can_submit_bids:
            messages.error(request, "This RFQ is not currently accepting bids.")
            return redirect("procurement:rfq_detail", pk=self.rfq.pk)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = VendorBidForm(organization=request.organization, rfq=self.rfq)
        lines = self.rfq.lines.all().order_by("line_number")
        return render(request, "procurement/vendor_bid_form.html", {
            "rfq": self.rfq,
            "form": form,
            "rfq_lines": lines,
        })

    def post(self, request, *args, **kwargs):
        form = VendorBidForm(request.POST, organization=request.organization, rfq=self.rfq)
        lines = self.rfq.lines.all().order_by("line_number")

        if form.is_valid():
            # Process lines
            lines_data = []
            for line in lines:
                price_key = f"price_{line.id}"
                qty_key = f"qty_{line.id}"
                lead_key = f"lead_{line.id}"
                notes_key = f"notes_{line.id}"

                price_val = request.POST.get(price_key)
                if price_val:
                    lines_data.append({
                        "rfq_line": line,
                        "offered_unit_price": Decimal(price_val),
                        "offered_quantity": Decimal(request.POST.get(qty_key, line.target_quantity)),
                        "lead_time_days": int(request.POST.get(lead_key, form.cleaned_data["lead_time_days"])),
                        "notes": request.POST.get(notes_key, ""),
                    })

            try:
                bid = RFQService.submit_vendor_bid(
                    rfq=self.rfq,
                    supplier=form.cleaned_data["supplier"],
                    bid_reference=form.cleaned_data["bid_reference"],
                    valid_until=form.cleaned_data["valid_until"],
                    payment_terms=form.cleaned_data["payment_terms"],
                    lead_time_days=form.cleaned_data["lead_time_days"],
                    shipping_cost=form.cleaned_data["shipping_cost"],
                    currency=form.cleaned_data["currency"],
                    notes=form.cleaned_data["notes"],
                    lines_data=lines_data,
                )
                messages.success(request, f"Vendor proposal from '{bid.supplier.name}' logged successfully.")
                return redirect("procurement:rfq_detail", pk=self.rfq.pk)
            except ValidationError as e:
                messages.error(request, f"Error saving bid: {e.message if hasattr(e, 'message') else e}")

        return render(request, "procurement/vendor_bid_form.html", {
            "rfq": self.rfq,
            "form": form,
            "rfq_lines": lines,
        })


class RFQBidComparisonView(OrganizationAccessMixin, DetailView):
    model = RequestForQuotation
    template_name = "procurement/rfq_comparison.html"
    context_object_name = "rfq"

    def get_queryset(self):
        org = self.request.organization
        return RequestForQuotation.objects.filter(organization=org)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["matrix"] = RFQService.compare_bids(self.object)
        context["award_form"] = AwardBidForm()
        return context


class RFQAwardBidView(OrganizationAccessMixin, View):
    def post(self, request, *args, **kwargs):
        rfq = get_object_or_404(RequestForQuotation, pk=kwargs["pk"], organization=request.organization)
        form = AwardBidForm(request.POST)
        if form.is_valid():
            bid = get_object_or_404(VendorBid, pk=form.cleaned_data["bid_id"], rfq=rfq)
            RFQService.award_bid(rfq, bid, form.cleaned_data["award_reason"], user=request.user)
            messages.success(request, f"Contract awarded to '{bid.supplier.name}'! RFQ is now marked as AWARDED.")
        else:
            messages.error(request, "Invalid award form submission.")
        return redirect("procurement:rfq_detail", pk=rfq.pk)


class RFQPrintView(OrganizationAccessMixin, DetailView):
    model = RequestForQuotation
    template_name = "procurement/rfq_print.html"
    context_object_name = "rfq"

    def get_queryset(self):
        org = self.request.organization
        return RequestForQuotation.objects.filter(organization=org).prefetch_related(
            "lines__product",
            "lines__uom",
        )


from .models import (
    POStatus,
    ApprovalTier,
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseOrderApproval,
)
from .forms import (
    PurchaseOrderForm,
    PurchaseOrderLineForm,
    POLineFormSet,
    POApprovalDecisionForm,
)
from .services import PurchaseOrderService


class POListView(OrganizationAccessMixin, ListView):
    model = PurchaseOrder
    template_name = "procurement/po_list.html"
    context_object_name = "orders"
    paginate_by = 25

    def get_queryset(self):
        org = self.request.organization
        if not org:
            return PurchaseOrder.objects.none()

        qs = PurchaseOrder.objects.filter(organization=org).select_related("supplier", "created_by")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(po_number__icontains=q) |
                Q(supplier__name__icontains=q) |
                Q(notes__icontains=q)
            )

        status = self.request.GET.get("status", "").strip()
        if status:
            qs = qs.filter(status=status)

        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["po_statuses"] = POStatus.choices
        context["current_q"] = self.request.GET.get("q", "")
        context["current_status"] = self.request.GET.get("status", "")
        return context


class PODetailView(OrganizationAccessMixin, DetailView):
    model = PurchaseOrder
    template_name = "procurement/po_detail.html"
    context_object_name = "po"

    def get_queryset(self):
        org = self.request.organization
        if not org:
            return PurchaseOrder.objects.none()
        return PurchaseOrder.objects.filter(organization=org).select_related(
            "supplier", "created_by", "approved_by", "rfq"
        ).prefetch_related(
            "lines__product",
            "lines__uom",
            "approvals__approver",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["approval_form"] = POApprovalDecisionForm()
        return context


class POCreateView(OrganizationAccessMixin, View):
    def get(self, request, *args, **kwargs):
        form = PurchaseOrderForm(organization=request.organization)
        formset = POLineFormSet(form_kwargs={"organization": request.organization})
        return render(request, "procurement/po_form.html", {
            "form": form,
            "formset": formset,
            "title": "Create Purchase Order",
        })

    def post(self, request, *args, **kwargs):
        form = PurchaseOrderForm(request.POST, organization=request.organization)
        formset = POLineFormSet(request.POST, form_kwargs={"organization": request.organization})

        if form.is_valid() and formset.is_valid():
            po = form.save(commit=False)
            po.organization = request.organization
            po.po_number = PurchaseOrder.generate_po_number(request.organization)
            po.created_by = request.user
            po.status = POStatus.DRAFT
            po.save()

            lines = formset.save(commit=False)
            for idx, line in enumerate(lines, start=1):
                line.purchase_order = po
                line.line_number = idx
                line.save()

            po.recalculate_totals()
            messages.success(request, f"Purchase Order '{po.po_number}' created.")
            return redirect("procurement:po_detail", pk=po.pk)

        return render(request, "procurement/po_form.html", {
            "form": form,
            "formset": formset,
            "title": "Create Purchase Order",
        })


class POUpdateView(OrganizationAccessMixin, View):
    def dispatch(self, request, *args, **kwargs):
        self.po = get_object_or_404(PurchaseOrder, pk=kwargs["pk"], organization=request.organization)
        if self.po.status != POStatus.DRAFT:
            messages.error(request, "Only draft Purchase Orders can be modified.")
            return redirect("procurement:po_detail", pk=self.po.pk)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = PurchaseOrderForm(instance=self.po, organization=request.organization)
        formset = POLineFormSet(instance=self.po, form_kwargs={"organization": request.organization})
        return render(request, "procurement/po_form.html", {
            "form": form,
            "formset": formset,
            "po": self.po,
            "title": f"Edit {self.po.po_number}",
        })

    def post(self, request, *args, **kwargs):
        form = PurchaseOrderForm(request.POST, instance=self.po, organization=request.organization)
        formset = POLineFormSet(request.POST, instance=self.po, form_kwargs={"organization": request.organization})

        if form.is_valid() and formset.is_valid():
            po = form.save()
            lines = formset.save(commit=False)
            for idx, line in enumerate(lines, start=1):
                line.purchase_order = po
                line.line_number = idx
                line.save()
            for obj in formset.deleted_objects:
                obj.delete()

            po.recalculate_totals()
            messages.success(request, f"Purchase Order '{po.po_number}' updated.")
            return redirect("procurement:po_detail", pk=po.pk)

        return render(request, "procurement/po_form.html", {
            "form": form,
            "formset": formset,
            "po": self.po,
            "title": f"Edit {self.po.po_number}",
        })


class POSubmitApprovalView(OrganizationAccessMixin, View):
    def post(self, request, *args, **kwargs):
        po = get_object_or_404(PurchaseOrder, pk=kwargs["pk"], organization=request.organization)
        try:
            PurchaseOrderService.submit_for_approval(po, submitted_by=request.user)
            messages.success(request, f"Purchase Order '{po.po_number}' submitted to financial approval routing.")
        except ValidationError as e:
            messages.error(request, f"Cannot submit for approval: {e.message if hasattr(e, 'message') else e}")
        return redirect("procurement:po_detail", pk=po.pk)


class POApproveView(OrganizationAccessMixin, View):
    def post(self, request, *args, **kwargs):
        po = get_object_or_404(PurchaseOrder, pk=kwargs["pk"], organization=request.organization)
        form = POApprovalDecisionForm(request.POST)
        comments = form.cleaned_data.get("comments", "") if form.is_valid() else ""
        try:
            PurchaseOrderService.approve_po(po, approver=request.user, comments=comments)
            messages.success(request, f"Approval granted for '{po.po_number}'.")
        except ValidationError as e:
            messages.error(request, f"Approval error: {e.message if hasattr(e, 'message') else e}")
        return redirect("procurement:po_detail", pk=po.pk)


class PORejectView(OrganizationAccessMixin, View):
    def post(self, request, *args, **kwargs):
        po = get_object_or_404(PurchaseOrder, pk=kwargs["pk"], organization=request.organization)
        form = POApprovalDecisionForm(request.POST)
        comments = form.cleaned_data.get("comments", "") if form.is_valid() else ""
        try:
            PurchaseOrderService.reject_po(po, rejector=request.user, comments=comments)
            messages.warning(request, f"Purchase Order '{po.po_number}' rejected.")
        except ValidationError as e:
            messages.error(request, f"Rejection error: {e.message if hasattr(e, 'message') else e}")
        return redirect("procurement:po_detail", pk=po.pk)


class POIssueView(OrganizationAccessMixin, View):
    def post(self, request, *args, **kwargs):
        po = get_object_or_404(PurchaseOrder, pk=kwargs["pk"], organization=request.organization)
        try:
            PurchaseOrderService.issue_po(po, issued_by=request.user)
            messages.success(request, f"Purchase Order '{po.po_number}' issued to vendor '{po.supplier.name}'.")
        except ValidationError as e:
            messages.error(request, f"Cannot issue PO: {e.message if hasattr(e, 'message') else e}")
        return redirect("procurement:po_detail", pk=po.pk)


class ConvertRFQToPOView(OrganizationAccessMixin, View):
    def post(self, request, *args, **kwargs):
        rfq = get_object_or_404(RequestForQuotation, pk=kwargs["pk"], organization=request.organization)
        try:
            po = PurchaseOrderService.convert_rfq_to_po(rfq, created_by=request.user)
            messages.success(request, f"Purchase Order '{po.po_number}' generated from awarded RFQ '{rfq.rfq_number}'.")
            return redirect("procurement:po_detail", pk=po.pk)
        except ValidationError as e:
            messages.error(request, f"Cannot convert RFQ: {e.message if hasattr(e, 'message') else e}")
            return redirect("procurement:rfq_detail", pk=rfq.pk)


class POPrintView(OrganizationAccessMixin, DetailView):
    model = PurchaseOrder
    template_name = "procurement/po_print.html"
    context_object_name = "po"

    def get_queryset(self):
        org = self.request.organization
        return PurchaseOrder.objects.filter(organization=org).select_related(
            "supplier", "created_by", "approved_by"
        ).prefetch_related(
            "lines__product",
            "lines__uom",
        )


from .models import (
    BillStatus,
    MatchStatus,
    VendorBill,
    VendorBillLine,
    ThreeWayMatch,
)
from .forms import (
    VendorBillForm,
    VendorBillLineForm,
    VendorBillLineFormSet,
    ThreeWayMatchResolutionForm,
)
from .services import ThreeWayMatchService


class ProcurementDashboardView(OrganizationAccessMixin, TemplateView):
    template_name = "procurement/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        org = self.request.organization
        if org:
            metrics = ThreeWayMatchService.get_procurement_dashboard_metrics(org)
            context.update(metrics)
        return context


class VendorBillListView(OrganizationAccessMixin, ListView):
    model = VendorBill
    template_name = "procurement/bill_list.html"
    context_object_name = "bills"
    paginate_by = 25

    def get_queryset(self):
        org = self.request.organization
        if not org:
            return VendorBill.objects.none()

        qs = VendorBill.objects.filter(organization=org).select_related("supplier", "purchase_order")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(bill_number__icontains=q) |
                Q(supplier__name__icontains=q) |
                Q(purchase_order__po_number__icontains=q)
            )

        status = self.request.GET.get("status", "").strip()
        if status:
            qs = qs.filter(status=status)

        match_status = self.request.GET.get("match_status", "").strip()
        if match_status:
            qs = qs.filter(match_status=match_status)

        return qs.order_by("-bill_date")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["bill_statuses"] = BillStatus.choices
        context["match_statuses"] = MatchStatus.choices
        context["current_q"] = self.request.GET.get("q", "")
        context["current_status"] = self.request.GET.get("status", "")
        context["current_match_status"] = self.request.GET.get("match_status", "")
        return context


class VendorBillDetailView(OrganizationAccessMixin, DetailView):
    model = VendorBill
    template_name = "procurement/bill_detail.html"
    context_object_name = "bill"

    def get_queryset(self):
        org = self.request.organization
        if not org:
            return VendorBill.objects.none()
        return VendorBill.objects.filter(organization=org).select_related(
            "supplier", "purchase_order", "created_by"
        ).prefetch_related(
            "lines__product",
            "lines__po_line",
            "three_way_matches",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["latest_match"] = self.object.three_way_matches.order_by("-created_at").first()
        context["resolve_form"] = ThreeWayMatchResolutionForm()
        return context


class VendorBillCreateView(OrganizationAccessMixin, View):
    def get(self, request, *args, **kwargs):
        form = VendorBillForm(organization=request.organization)
        formset = VendorBillLineFormSet(form_kwargs={"organization": request.organization})
        return render(request, "procurement/bill_form.html", {
            "form": form,
            "formset": formset,
            "title": "Register Vendor Invoice / Bill",
        })

    def post(self, request, *args, **kwargs):
        form = VendorBillForm(request.POST, organization=request.organization)
        formset = VendorBillLineFormSet(request.POST, form_kwargs={"organization": request.organization})

        if form.is_valid() and formset.is_valid():
            bill = form.save(commit=False)
            bill.organization = request.organization
            bill.created_by = request.user
            bill.save()

            lines = formset.save(commit=False)
            for line in lines:
                line.bill = bill
                line.save()

            bill.recalculate_totals()
            messages.success(request, f"Vendor Bill '{bill.bill_number}' registered.")

            # Automatically run 3-way match if linked to a purchase order
            if bill.purchase_order:
                ThreeWayMatchService.execute_three_way_match(bill.purchase_order, bill)
                messages.info(request, "Automated 3-Way Match executed against linked Purchase Order.")

            return redirect("procurement:bill_detail", pk=bill.pk)

        return render(request, "procurement/bill_form.html", {
            "form": form,
            "formset": formset,
            "title": "Register Vendor Invoice / Bill",
        })


class ThreeWayMatchExecuteView(OrganizationAccessMixin, View):
    def post(self, request, *args, **kwargs):
        bill = get_object_or_404(VendorBill, pk=kwargs["bill_pk"], organization=request.organization)
        if not bill.purchase_order:
            messages.error(request, "Cannot run 3-Way Match without an associated Purchase Order.")
            return redirect("procurement:bill_detail", pk=bill.pk)

        match_record = ThreeWayMatchService.execute_three_way_match(bill.purchase_order, bill)
        if match_record.status == MatchStatus.MATCHED:
            messages.success(request, "3-Way Match verified! Perfect alignment across PO, Receipts, and Bill.")
        elif match_record.status == MatchStatus.TOLERANCE_ACCEPTED:
            messages.info(request, "3-Way Match verified within acceptable commercial price tolerance.")
        else:
            messages.warning(request, f"Variance detected during 3-Way Match: {match_record.dispute_reason}")

        return redirect("procurement:bill_detail", pk=bill.pk)


class ThreeWayMatchDetailView(OrganizationAccessMixin, DetailView):
    model = ThreeWayMatch
    template_name = "procurement/three_way_match_detail.html"
    context_object_name = "match"

    def get_queryset(self):
        org = self.request.organization
        return ThreeWayMatch.objects.filter(organization=org).select_related(
            "purchase_order__supplier", "vendor_bill__supplier", "resolved_by"
        )


class ThreeWayMatchResolveView(OrganizationAccessMixin, View):
    def post(self, request, *args, **kwargs):
        match_record = get_object_or_404(ThreeWayMatch, pk=kwargs["pk"], organization=request.organization)
        form = ThreeWayMatchResolutionForm(request.POST)
        if form.is_valid():
            ThreeWayMatchService.resolve_match_dispute(
                match_record,
                user=request.user,
                resolution_notes=form.cleaned_data["resolution_notes"],
            )
            messages.success(request, "Dispute resolved and invoice authorized for payment.")
        else:
            messages.error(request, "Resolution justification is required.")
        return redirect("procurement:bill_detail", pk=match_record.vendor_bill.pk)
