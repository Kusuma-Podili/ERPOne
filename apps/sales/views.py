"""
EnterpriseOne Sales Views.
Handles Product Catalog, Categories, UOMs, Price Books, and Tiered Discounts.
"""
from decimal import Decimal
from django.contrib import messages
from django.db.models import Q, Count, Sum
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
    Product,
    ProductCategory,
    UnitOfMeasure,
    PriceBook,
    PriceBookEntry,
    TieredDiscount,
    Quote,
    QuoteLineItem,
    QuoteApproval,
    QuoteStatus,
    SalesOrder,
    OrderLineItem,
    OrderStatusHistory,
    OrderStatus,
)
from .forms import (
    ProductForm,
    ProductCategoryForm,
    PriceBookForm,
    PriceBookEntryForm,
    TieredDiscountForm,
    QuoteForm,
    QuoteLineItemForm,
    QuoteApprovalActionForm,
    SalesOrderForm,
    OrderLineItemForm,
    QuoteConvertForm,
)
from .services import (
    PricingEngineService,
    QuoteCalculationService,
    QuoteApprovalService,
    OrderStateMachineService,
    QuoteToOrderConversionService,
)


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


# =====================================================================
# QUOTE & WORKFLOW VIEWS
# =====================================================================

class QuoteListView(OrganizationAccessMixin, ListView):
    model = Quote
    template_name = "sales/quote_list.html"
    context_object_name = "quotes"
    paginate_by = 25

    def get_queryset(self):
        org = self.request.organization
        if not org:
            return Quote.objects.none()
        qs = Quote.objects.filter(organization=org).select_related("account", "contact", "deal", "created_by")
        search = self.request.GET.get("q")
        if search:
            qs = qs.filter(
                Q(quote_number__icontains=search)
                | Q(title__icontains=search)
                | Q(account__name__icontains=search)
            )
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = QuoteStatus.choices
        ctx["current_status"] = self.request.GET.get("status", "")
        ctx["search_query"] = self.request.GET.get("q", "")
        return ctx


class QuoteDetailView(OrganizationAccessMixin, DetailView):
    model = Quote
    template_name = "sales/quote_detail.html"
    context_object_name = "quote"

    def get_queryset(self):
        org = self.request.organization
        if not org:
            return Quote.objects.none()
        return Quote.objects.filter(organization=org).select_related(
            "account", "contact", "deal", "price_book", "approved_by", "created_by"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        quote = self.object
        ctx["line_items"] = quote.line_items.select_related("product", "product__uom").order_by("line_number")
        ctx["line_form"] = QuoteLineItemForm(organization=self.request.organization)
        ctx["approvals"] = quote.approvals.select_related("requested_by", "approver").order_by("-requested_at")
        ctx["approval_form"] = QuoteApprovalActionForm()
        return ctx


class QuoteCreateView(OrganizationAccessMixin, CreateView):
    model = Quote
    form_class = QuoteForm
    template_name = "sales/quote_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.request.organization
        return kwargs

    def form_valid(self, form):
        form.instance.organization = self.request.organization
        form.instance.created_by = self.request.user
        messages.success(self.request, "Quotation created successfully. Now add line items below.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("sales:quote_detail", kwargs={"pk": self.object.pk})


class QuoteUpdateView(OrganizationAccessMixin, UpdateView):
    model = Quote
    form_class = QuoteForm
    template_name = "sales/quote_form.html"

    def get_queryset(self):
        org = self.request.organization
        return Quote.objects.filter(organization=org)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.request.organization
        return kwargs

    def form_valid(self, form):
        if not form.instance.can_edit:
            messages.error(self.request, "This quotation cannot be modified in its current status.")
            return redirect("sales:quote_detail", pk=form.instance.pk)
        messages.success(self.request, "Quotation updated successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("sales:quote_detail", kwargs={"pk": self.object.pk})


class QuoteDeleteView(OrganizationAccessMixin, DeleteView):
    model = Quote
    template_name = "sales/quote_confirm_delete.html"
    success_url = reverse_lazy("sales:quote_list")

    def get_queryset(self):
        org = self.request.organization
        return Quote.objects.filter(organization=org, status=QuoteStatus.DRAFT)


class QuoteLineItemCreateView(OrganizationAccessMixin, View):
    """Adds a product line to the quotation."""
    def post(self, request, pk):
        org = request.organization
        quote = get_object_or_404(Quote, pk=pk, organization=org)
        if not quote.can_edit:
            messages.error(request, "Cannot modify items on this quotation.")
            return redirect("sales:quote_detail", pk=quote.pk)

        form = QuoteLineItemForm(request.POST, organization=org)
        if form.is_valid():
            line = form.save(commit=False)
            line.organization = org
            line.quote = quote
            line.line_number = quote.line_items.count() + 1
            line.calculate_amounts()
            line.save()
            QuoteCalculationService.recalculate_quote(quote)
            messages.success(request, f"Added line item {line.product.name}.")
        else:
            messages.error(request, "Failed to add line item. Please verify fields.")
        return redirect("sales:quote_detail", pk=quote.pk)


class QuoteLineItemDeleteView(OrganizationAccessMixin, View):
    """Deletes a product line from the quotation."""
    def post(self, request, pk):
        org = request.organization
        line = get_object_or_404(QuoteLineItem, pk=pk, organization=org)
        quote = line.quote
        if not quote.can_edit:
            messages.error(request, "Cannot modify items on this quotation.")
            return redirect("sales:quote_detail", pk=quote.pk)

        line.delete()
        QuoteCalculationService.recalculate_quote(quote)
        messages.success(request, "Line item removed.")
        return redirect("sales:quote_detail", pk=quote.pk)


class QuoteSubmitApprovalView(OrganizationAccessMixin, View):
    """Submits quotation for approval."""
    def post(self, request, pk):
        org = request.organization
        quote = get_object_or_404(Quote, pk=pk, organization=org)
        try:
            QuoteApprovalService.submit_for_approval(quote, request.user)
            if quote.status == QuoteStatus.PENDING_APPROVAL:
                messages.warning(request, f"Quote {quote.quote_number} requires managerial approval due to high discount.")
            else:
                messages.success(request, f"Quote {quote.quote_number} automatically approved.")
        except Exception as e:
            messages.error(request, str(e))
        return redirect("sales:quote_detail", pk=quote.pk)


class QuoteApproveView(OrganizationAccessMixin, View):
    """Manager approves quotation."""
    def post(self, request, pk):
        org = request.organization
        quote = get_object_or_404(Quote, pk=pk, organization=org)
        notes = request.POST.get("notes", "")
        try:
            QuoteApprovalService.approve_quote(quote, request.user, notes=notes)
            messages.success(request, f"Quote {quote.quote_number} has been approved.")
        except Exception as e:
            messages.error(request, str(e))
        return redirect("sales:quote_detail", pk=quote.pk)


class QuoteRejectView(OrganizationAccessMixin, View):
    """Manager rejects quotation."""
    def post(self, request, pk):
        org = request.organization
        quote = get_object_or_404(Quote, pk=pk, organization=org)
        notes = request.POST.get("notes", "")
        try:
            QuoteApprovalService.reject_quote(quote, request.user, reason=notes)
            messages.warning(request, f"Quote {quote.quote_number} was rejected.")
        except Exception as e:
            messages.error(request, str(e))
        return redirect("sales:quote_detail", pk=quote.pk)


class QuotePresentView(OrganizationAccessMixin, View):
    """Marks quotation presented to customer."""
    def post(self, request, pk):
        org = request.organization
        quote = get_object_or_404(Quote, pk=pk, organization=org)
        try:
            QuoteApprovalService.present_quote(quote, request.user)
            messages.success(request, f"Quote {quote.quote_number} marked as presented to customer.")
        except Exception as e:
            messages.error(request, str(e))
        return redirect("sales:quote_detail", pk=quote.pk)


class QuoteAcceptView(OrganizationAccessMixin, View):
    """Marks quotation accepted by customer."""
    def post(self, request, pk):
        org = request.organization
        quote = get_object_or_404(Quote, pk=pk, organization=org)
        try:
            QuoteApprovalService.accept_quote(quote, request.user)
            messages.success(request, f"Quote {quote.quote_number} accepted! Ready to convert to Sales Order.")
        except Exception as e:
            messages.error(request, str(e))
        return redirect("sales:quote_detail", pk=quote.pk)


# =====================================================================
# SALES ORDER & FULFILLMENT VIEWS
# =====================================================================

class OrderListView(OrganizationAccessMixin, ListView):
    model = SalesOrder
    template_name = "sales/order_list.html"
    context_object_name = "orders"
    paginate_by = 25

    def get_queryset(self):
        org = self.request.organization
        if not org:
            return SalesOrder.objects.none()
        qs = SalesOrder.objects.filter(organization=org).select_related("account", "contact", "deal", "created_by")
        search = self.request.GET.get("q")
        if search:
            qs = qs.filter(
                Q(order_number__icontains=search)
                | Q(account__name__icontains=search)
                | Q(customer_notes__icontains=search)
            )
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = OrderStatus.choices
        ctx["current_status"] = self.request.GET.get("status", "")
        ctx["search_query"] = self.request.GET.get("q", "")
        return ctx


class OrderDetailView(OrganizationAccessMixin, DetailView):
    model = SalesOrder
    template_name = "sales/order_detail.html"
    context_object_name = "order"

    def get_queryset(self):
        org = self.request.organization
        if not org:
            return SalesOrder.objects.none()
        return SalesOrder.objects.filter(organization=org).select_related(
            "account", "contact", "deal", "quote", "created_by"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        order = self.object
        ctx["line_items"] = order.line_items.select_related("product", "product__uom").order_by("line_number")
        ctx["status_history"] = order.status_history.select_related("changed_by").order_by("-timestamp")
        ctx["line_form"] = OrderLineItemForm(organization=self.request.organization)
        ctx["next_allowed_statuses"] = OrderStateMachineService.PERMISSIBLE_TRANSITIONS.get(order.status, [])
        return ctx


class OrderCreateView(OrganizationAccessMixin, CreateView):
    model = SalesOrder
    form_class = SalesOrderForm
    template_name = "sales/order_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.request.organization
        return kwargs

    def form_valid(self, form):
        form.instance.organization = self.request.organization
        form.instance.created_by = self.request.user
        form.instance.status = OrderStatus.DRAFT
        messages.success(self.request, "Sales order created successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("sales:order_detail", kwargs={"pk": self.object.pk})


class OrderUpdateView(OrganizationAccessMixin, UpdateView):
    model = SalesOrder
    form_class = SalesOrderForm
    template_name = "sales/order_form.html"

    def get_queryset(self):
        org = self.request.organization
        return SalesOrder.objects.filter(organization=org)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.request.organization
        return kwargs

    def form_valid(self, form):
        if form.instance.status not in [OrderStatus.DRAFT, OrderStatus.CONFIRMED]:
            messages.error(self.request, "Cannot modify an order that is already processing or fulfilled.")
            return redirect("sales:order_detail", pk=form.instance.pk)
        messages.success(self.request, "Sales order updated.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("sales:order_detail", kwargs={"pk": self.object.pk})


class OrderLineItemCreateView(OrganizationAccessMixin, View):
    """Adds a line item to a draft or confirmed sales order."""
    def post(self, request, pk):
        org = request.organization
        order = get_object_or_404(SalesOrder, pk=pk, organization=org)
        if order.status not in [OrderStatus.DRAFT, OrderStatus.CONFIRMED]:
            messages.error(request, "Cannot modify items on this order.")
            return redirect("sales:order_detail", pk=order.pk)

        form = OrderLineItemForm(request.POST, organization=org)
        if form.is_valid():
            line = form.save(commit=False)
            line.organization = org
            line.order = order
            line.line_number = order.line_items.count() + 1
            line.calculate_amounts()
            line.save()
            order.recalculate_totals()
            messages.success(request, f"Added line item {line.product.name}.")
        else:
            messages.error(request, "Failed to add line item.")
        return redirect("sales:order_detail", pk=order.pk)


class OrderLineItemDeleteView(OrganizationAccessMixin, View):
    """Removes a line item from a draft or confirmed sales order."""
    def post(self, request, pk):
        org = request.organization
        line = get_object_or_404(OrderLineItem, pk=pk, organization=org)
        order = line.order
        if order.status not in [OrderStatus.DRAFT, OrderStatus.CONFIRMED]:
            messages.error(request, "Cannot modify items on this order.")
            return redirect("sales:order_detail", pk=order.pk)

        line.delete()
        order.recalculate_totals()
        messages.success(request, "Line item removed.")
        return redirect("sales:order_detail", pk=order.pk)


class OrderStatusTransitionView(OrganizationAccessMixin, View):
    """Executes state machine status transition for a sales order."""
    def post(self, request, pk):
        org = request.organization
        order = get_object_or_404(SalesOrder, pk=pk, organization=org)
        target_status = request.POST.get("target_status")
        notes = request.POST.get("notes", "")
        try:
            OrderStateMachineService.transition_order(order, target_status, request.user, notes=notes)
            messages.success(request, f"Order status updated to '{order.get_status_display()}'.")
        except Exception as e:
            messages.error(request, str(e))
        return redirect("sales:order_detail", pk=order.pk)


class OrderFulfillView(OrganizationAccessMixin, View):
    """Fulfills item quantities on a sales order."""
    def post(self, request, pk):
        org = request.organization
        order = get_object_or_404(SalesOrder, pk=pk, organization=org)
        fulfillment_map = {}
        for key, val in request.POST.items():
            if key.startswith("fulfill_line_"):
                line_id = key.replace("fulfill_line_", "")
                try:
                    qty = int(val)
                    if qty > 0:
                        fulfillment_map[line_id] = qty
                except ValueError:
                    pass

        notes = request.POST.get("fulfillment_notes", "")
        try:
            OrderStateMachineService.fulfill_line_items(order, fulfillment_map, request.user, notes=notes)
            messages.success(request, f"Order fulfillment updated ({order.fulfillment_percentage}% complete).")
        except Exception as e:
            messages.error(request, str(e))
        return redirect("sales:order_detail", pk=order.pk)


class QuoteConvertToOrderView(OrganizationAccessMixin, View):
    """Promotes an accepted quotation into a binding Sales Order."""
    def post(self, request, pk):
        org = request.organization
        quote = get_object_or_404(Quote, pk=pk, organization=org)
        form = QuoteConvertForm(request.POST)
        if form.is_valid():
            try:
                order = QuoteToOrderConversionService.convert_quote_to_order(
                    quote=quote,
                    user=request.user,
                    required_date=form.cleaned_data.get("required_date"),
                    shipping_address=form.cleaned_data.get("shipping_address", ""),
                    billing_address=form.cleaned_data.get("billing_address", ""),
                )
                messages.success(request, f"Quotation {quote.quote_number} successfully converted to Sales Order {order.order_number}!")
                return redirect("sales:order_detail", pk=order.pk)
            except Exception as e:
                messages.error(request, str(e))
        else:
            messages.error(request, "Invalid order conversion parameters.")
        return redirect("sales:quote_detail", pk=quote.pk)


# =====================================================================
# SALES DASHBOARD & PRINT READY VIEWS (Milestone 4.4)
# =====================================================================

class SalesDashboardView(OrganizationAccessMixin, TemplateView):
    """
    Executive Sales & Order Management overview dashboard.
    Consolidates revenue metrics, quotation conversion rates, order fulfillment pipeline,
    and product catalog distribution.
    """
    template_name = "sales/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        org = self.request.organization
        if not org:
            return ctx

        # Quotes metrics
        quotes_qs = Quote.objects.filter(organization=org)
        total_quotes = quotes_qs.count()
        quotes_draft = quotes_qs.filter(status=QuoteStatus.DRAFT).count()
        quotes_pending = quotes_qs.filter(status=QuoteStatus.PENDING_APPROVAL).count()
        quotes_approved = quotes_qs.filter(status=QuoteStatus.APPROVED).count()
        quotes_presented = quotes_qs.filter(status=QuoteStatus.PRESENTED).count()
        quotes_accepted = quotes_qs.filter(status=QuoteStatus.ACCEPTED).count()
        quotes_converted = quotes_qs.filter(status=QuoteStatus.CONVERTED).count()
        quote_pipeline_value = quotes_qs.aggregate(total=Sum("grand_total"))["total"] or Decimal("0.00")
        accepted_quote_value = quotes_qs.filter(status__in=[QuoteStatus.ACCEPTED, QuoteStatus.CONVERTED]).aggregate(total=Sum("grand_total"))["total"] or Decimal("0.00")

        conversion_rate = 0.0
        if total_quotes > 0:
            conversion_rate = round((quotes_converted / total_quotes) * 100, 1)

        # Sales Orders metrics
        orders_qs = SalesOrder.objects.filter(organization=org)
        total_orders = orders_qs.count()
        orders_draft = orders_qs.filter(status=OrderStatus.DRAFT).count()
        orders_confirmed = orders_qs.filter(status=OrderStatus.CONFIRMED).count()
        orders_processing = orders_qs.filter(status=OrderStatus.PROCESSING).count()
        orders_partially_fulfilled = orders_qs.filter(status=OrderStatus.PARTIALLY_FULFILLED).count()
        orders_fulfilled = orders_qs.filter(status=OrderStatus.FULFILLED).count()
        orders_invoiced = orders_qs.filter(status=OrderStatus.INVOICED).count()
        orders_cancelled = orders_qs.filter(status=OrderStatus.CANCELLED).count()

        pending_fulfillment_count = orders_qs.filter(
            status__in=[OrderStatus.CONFIRMED, OrderStatus.PROCESSING, OrderStatus.PARTIALLY_FULFILLED]
        ).count()

        total_sales_revenue = orders_qs.exclude(status=OrderStatus.CANCELLED).aggregate(total=Sum("grand_total"))["total"] or Decimal("0.00")
        fulfilled_revenue = orders_qs.filter(status__in=[OrderStatus.FULFILLED, OrderStatus.INVOICED]).aggregate(total=Sum("grand_total"))["total"] or Decimal("0.00")

        # Products / Catalog metrics
        products_qs = Product.objects.filter(organization=org)
        active_products_count = products_qs.filter(is_active=True).count()
        total_categories_count = ProductCategory.objects.filter(organization=org).count()
        pricebooks_count = PriceBook.objects.filter(organization=org).count()

        # Top product categories with product count
        top_categories = ProductCategory.objects.filter(organization=org).annotate(
            prod_count=Count("products")
        ).order_by("-prod_count")[:5]

        # Recent records
        recent_quotes = quotes_qs.select_related("account", "created_by").order_by("-created_at")[:5]
        recent_orders = orders_qs.select_related("account", "created_by").order_by("-created_at")[:5]

        ctx.update({
            "total_quotes": total_quotes,
            "quotes_draft": quotes_draft,
            "quotes_pending": quotes_pending,
            "quotes_approved": quotes_approved,
            "quotes_presented": quotes_presented,
            "quotes_accepted": quotes_accepted,
            "quotes_converted": quotes_converted,
            "quote_pipeline_value": quote_pipeline_value,
            "accepted_quote_value": accepted_quote_value,
            "conversion_rate": conversion_rate,

            "total_orders": total_orders,
            "orders_draft": orders_draft,
            "orders_confirmed": orders_confirmed,
            "orders_processing": orders_processing,
            "orders_partially_fulfilled": orders_partially_fulfilled,
            "orders_fulfilled": orders_fulfilled,
            "orders_invoiced": orders_invoiced,
            "orders_cancelled": orders_cancelled,
            "pending_fulfillment_count": pending_fulfillment_count,
            "total_sales_revenue": total_sales_revenue,
            "fulfilled_revenue": fulfilled_revenue,

            "active_products_count": active_products_count,
            "total_categories_count": total_categories_count,
            "pricebooks_count": pricebooks_count,
            "top_categories": top_categories,
            "recent_quotes": recent_quotes,
            "recent_orders": recent_orders,
        })
        return ctx


class QuotePrintView(OrganizationAccessMixin, DetailView):
    """
    Renders print-ready, professional commercial quotation layout.
    """
    model = Quote
    template_name = "sales/quote_print.html"
    context_object_name = "quote"

    def get_queryset(self):
        org = self.request.organization
        if not org:
            return Quote.objects.none()
        return Quote.objects.filter(organization=org).select_related(
            "account", "contact", "deal", "created_by", "approved_by"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["line_items"] = self.object.line_items.select_related("product", "product__uom").order_by("line_number")
        return ctx


class OrderPrintView(OrganizationAccessMixin, DetailView):
    """
    Renders print-ready, professional commercial sales order and packing slip.
    """
    model = SalesOrder
    template_name = "sales/order_print.html"
    context_object_name = "order"

    def get_queryset(self):
        org = self.request.organization
        if not org:
            return SalesOrder.objects.none()
        return SalesOrder.objects.filter(organization=org).select_related(
            "account", "contact", "deal", "quote", "created_by"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["line_items"] = self.object.line_items.select_related("product", "product__uom").order_by("line_number")
        return ctx



