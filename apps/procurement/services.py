"""
EnterpriseOne Procurement & Supplier Domain Services (Milestone 6.1).
Provides vendor lifecycle management, preferred vendor sourcing resolution, and supplier performance tracking.
"""
from decimal import Decimal
from typing import Optional, List, Dict
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.organizations.models import Organization
from apps.sales.models import Product
from .models import (
    Supplier,
    SupplierType,
    PaymentTerms,
    SupplierStatus,
    SupplierContact,
    SupplierProduct,
)


class SupplierService:
    """
    Governs supplier registration, commercial catalog relationships, and optimal sourcing resolutions.
    """

    @classmethod
    def create_supplier(
        cls,
        organization: Organization,
        name: str,
        code: str,
        supplier_type: str = SupplierType.DISTRIBUTOR,
        payment_terms: str = PaymentTerms.NET30,
        currency: str = "USD",
        tax_id: str = "",
        email: str = "",
        phone: str = "",
        website: str = "",
        address: str = "",
        city: str = "",
        state_province: str = "",
        postal_code: str = "",
        country: str = "USA",
        lead_time_rating: Decimal = Decimal("5.0"),
        quality_rating: Decimal = Decimal("5.0"),
        notes: str = "",
    ) -> Supplier:
        """
        Creates and registers an enterprise supplier master record.
        """
        supplier = Supplier(
            organization=organization,
            name=name.strip(),
            code=code.strip().upper(),
            supplier_type=supplier_type,
            payment_terms=payment_terms,
            currency=currency,
            tax_id=tax_id.strip(),
            email=email.strip(),
            phone=phone.strip(),
            website=website.strip(),
            address=address.strip(),
            city=city.strip(),
            state_province=state_province.strip(),
            postal_code=postal_code.strip(),
            country=country.strip(),
            lead_time_rating=lead_time_rating,
            quality_rating=quality_rating,
            notes=notes.strip(),
        )
        supplier.full_clean()
        supplier.save()
        return supplier

    @classmethod
    def add_contact(
        cls,
        supplier: Supplier,
        name: str,
        email: str,
        title: str = "",
        phone: str = "",
        is_primary: bool = False,
        notes: str = "",
    ) -> SupplierContact:
        """
        Attaches a liaison contact person to a supplier profile.
        """
        if is_primary:
            # Set other contacts to non-primary
            supplier.contacts.filter(is_primary=True).update(is_primary=False)

        contact = SupplierContact(
            supplier=supplier,
            name=name.strip(),
            email=email.strip(),
            title=title.strip(),
            phone=phone.strip(),
            is_primary=is_primary,
            notes=notes.strip(),
        )
        contact.full_clean()
        contact.save()
        return contact

    @classmethod
    @transaction.atomic
    def link_product(
        cls,
        supplier: Supplier,
        product: Product,
        unit_price: Decimal,
        supplier_sku: str = "",
        currency: str = "USD",
        minimum_order_quantity: Decimal = Decimal("1.00"),
        lead_time_days: int = 7,
        is_preferred: bool = False,
    ) -> SupplierProduct:
        """
        Registers or updates a vendor catalog offering for a product SKU.
        """
        if is_preferred:
            # Demote existing preferred supplier offerings for this product in the same organization
            SupplierProduct.objects.filter(
                organization=supplier.organization,
                product=product,
                is_preferred=True,
            ).exclude(supplier=supplier).update(is_preferred=False)

        offering, created = SupplierProduct.objects.update_or_create(
            organization=supplier.organization,
            supplier=supplier,
            product=product,
            defaults={
                "supplier_sku": supplier_sku.strip(),
                "unit_price": unit_price,
                "currency": currency,
                "minimum_order_quantity": minimum_order_quantity,
                "lead_time_days": lead_time_days,
                "is_preferred": is_preferred,
                "is_active": True,
            },
        )
        return offering

    @classmethod
    def get_preferred_supplier_offering(
        cls,
        product: Product,
    ) -> Optional[SupplierProduct]:
        """
        Resolves the optimal supplier offering for a product:
        1. Checks for explicitly designated preferred supplier offering
        2. Falls back to active supplier offering with lowest unit price
        """
        offerings = SupplierProduct.objects.filter(
            product=product,
            is_active=True,
            supplier__is_active=True,
            supplier__status=SupplierStatus.ACTIVE,
        ).select_related("supplier")

        preferred = offerings.filter(is_preferred=True).first()
        if preferred:
            return preferred

        return offerings.order_by("unit_price").first()


from .models import (
    RFQStatus,
    RequestForQuotation,
    RFQLine,
    RFQVendorInvitation,
    VendorBid,
    VendorBidLine,
)


class RFQService:
    """
    Coordinates Request for Quotation (RFQ) authoring, vendor invitations, competitive bidding,
    side-by-side evaluation matrices, and contract bid awards.
    """

    @classmethod
    @transaction.atomic
    def create_rfq(
        cls,
        organization: Organization,
        title: str,
        submission_deadline,
        created_by=None,
        delivery_deadline=None,
        notes: str = "",
        lines_data: Optional[List[Dict]] = None,
    ) -> RequestForQuotation:
        """
        Creates an RFQ in DRAFT status with optional line items.
        """
        rfq_number = RequestForQuotation.generate_rfq_number(organization)
        rfq = RequestForQuotation.objects.create(
            organization=organization,
            rfq_number=rfq_number,
            title=title.strip(),
            status=RFQStatus.DRAFT,
            submission_deadline=submission_deadline,
            delivery_deadline=delivery_deadline,
            notes=notes.strip(),
            created_by=created_by,
        )

        if lines_data:
            for idx, item in enumerate(lines_data, start=1):
                RFQLine.objects.create(
                    rfq=rfq,
                    line_number=idx,
                    product=item["product"],
                    target_quantity=item["target_quantity"],
                    uom=item.get("uom") or item["product"].uom,
                    target_delivery_date=item.get("target_delivery_date"),
                    specifications=item.get("specifications", "").strip(),
                )

        return rfq

    @classmethod
    def invite_vendors(
        cls,
        rfq: RequestForQuotation,
        suppliers: List[Supplier],
        invited_by=None,
    ) -> List[RFQVendorInvitation]:
        """
        Dispatches bidding invitations to suppliers.
        """
        invitations = []
        for supplier in suppliers:
            inv, created = RFQVendorInvitation.objects.get_or_create(
                rfq=rfq,
                supplier=supplier,
                defaults={"invited_by": invited_by},
            )
            invitations.append(inv)
        return invitations

    @classmethod
    def publish_rfq(cls, rfq: RequestForQuotation) -> RequestForQuotation:
        """
        Transitions RFQ to PUBLISHED status, making it open to vendor bids.
        """
        if not rfq.lines.exists():
            raise ValidationError("Cannot publish an RFQ without line items.")
        if rfq.is_expired:
            raise ValidationError("Cannot publish an RFQ whose submission deadline has already passed.")

        rfq.status = RFQStatus.PUBLISHED
        rfq.save(update_fields=["status", "updated_at"])
        return rfq

    @classmethod
    @transaction.atomic
    def submit_vendor_bid(
        cls,
        rfq: RequestForQuotation,
        supplier: Supplier,
        bid_reference: str,
        valid_until,
        payment_terms: str = PaymentTerms.NET30,
        lead_time_days: int = 7,
        shipping_cost: Decimal = Decimal("0.00"),
        currency: str = "USD",
        notes: str = "",
        lines_data: Optional[List[Dict]] = None,
    ) -> VendorBid:
        """
        Records a supplier bid proposal with line item unit pricing.
        """
        if rfq.status != RFQStatus.PUBLISHED:
            raise ValidationError("Bids can only be submitted for PUBLISHED RFQs.")
        if rfq.is_expired:
            raise ValidationError("Bid submission deadline has expired.")

        bid, created = VendorBid.objects.update_or_create(
            rfq=rfq,
            supplier=supplier,
            defaults={
                "bid_reference": bid_reference.strip(),
                "valid_until": valid_until,
                "payment_terms": payment_terms,
                "lead_time_days": lead_time_days,
                "shipping_cost": shipping_cost,
                "currency": currency,
                "notes": notes.strip(),
            },
        )

        if lines_data:
            for item in lines_data:
                rfq_line = item["rfq_line"]
                VendorBidLine.objects.update_or_create(
                    bid=bid,
                    rfq_line=rfq_line,
                    defaults={
                        "offered_unit_price": item["offered_unit_price"],
                        "offered_quantity": item.get("offered_quantity", rfq_line.target_quantity),
                        "lead_time_days": item.get("lead_time_days", lead_time_days),
                        "notes": item.get("notes", "").strip(),
                    },
                )

        # Mark invitation responded if exists
        RFQVendorInvitation.objects.filter(rfq=rfq, supplier=supplier).update(responded_at=timezone.now())

        return bid

    @classmethod
    def compare_bids(cls, rfq: RequestForQuotation) -> Dict:
        """
        Generates a side-by-side comparative matrix of all submitted vendor bids.
        """
        bids = list(rfq.bids.select_related("supplier").prefetch_related("lines__rfq_line__product"))
        lines = list(rfq.lines.select_related("product", "uom").order_by("line_number"))

        matrix = {
            "rfq": rfq,
            "bids": bids,
            "lines": [],
            "summary": [],
        }

        for line in lines:
            line_comparison = {
                "line": line,
                "bids": {},
                "lowest_price": None,
                "lowest_bidder": None,
            }
            min_price = None

            for bid in bids:
                bid_line = bid.lines.filter(rfq_line=line).first()
                if bid_line:
                    line_comparison["bids"][bid.id] = bid_line
                    if min_price is None or bid_line.offered_unit_price < min_price:
                        min_price = bid_line.offered_unit_price
                        line_comparison["lowest_price"] = min_price
                        line_comparison["lowest_bidder"] = bid.supplier
                else:
                    line_comparison["bids"][bid.id] = None

            matrix["lines"].append(line_comparison)

        for bid in bids:
            matrix["summary"].append({
                "bid": bid,
                "supplier": bid.supplier,
                "total_amount": bid.total_amount,
                "shipping_cost": bid.shipping_cost,
                "lead_time_days": bid.lead_time_days,
                "rating": bid.supplier.overall_rating,
                "is_winner": bid.is_winning_bid,
            })

        matrix["summary"].sort(key=lambda s: s["total_amount"])
        return matrix

    @classmethod
    @transaction.atomic
    def award_bid(
        cls,
        rfq: RequestForQuotation,
        winning_bid: VendorBid,
        award_reason: str,
        user=None,
    ) -> VendorBid:
        """
        Selects winning proposal, stamps justification audit, and closes the RFQ.
        """
        if winning_bid.rfq != rfq:
            raise ValidationError("Winning bid does not belong to this RFQ.")

        # Demote any previously marked winning bid
        rfq.bids.filter(is_winning_bid=True).update(is_winning_bid=False, awarded_at=None, awarded_by=None)

        winning_bid.is_winning_bid = True
        winning_bid.award_reason = award_reason.strip()
        winning_bid.awarded_at = timezone.now()
        winning_bid.awarded_by = user
        winning_bid.save()

        rfq.status = RFQStatus.AWARDED
        rfq.save(update_fields=["status", "updated_at"])

        return winning_bid


from .models import (
    POStatus,
    ApprovalTier,
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseOrderApproval,
)


class PurchaseOrderService:
    """
    Governs Purchase Order lifecycle, RFQ conversion, multi-tier financial approvals,
    and issuance to vendors.
    """

    @classmethod
    @transaction.atomic
    def create_po(
        cls,
        organization: Organization,
        supplier: Supplier,
        order_date,
        expected_delivery_date=None,
        payment_terms: str = PaymentTerms.NET30,
        shipping_cost: Decimal = Decimal("0.00"),
        currency: str = "USD",
        shipping_address: str = "",
        billing_address: str = "",
        notes: str = "",
        lines_data: Optional[List[Dict]] = None,
        created_by=None,
        rfq: Optional[RequestForQuotation] = None,
    ) -> PurchaseOrder:
        """
        Creates a new Purchase Order in DRAFT status with lines and computed totals.
        """
        po_number = PurchaseOrder.generate_po_number(organization)
        po = PurchaseOrder.objects.create(
            organization=organization,
            po_number=po_number,
            supplier=supplier,
            rfq=rfq,
            status=POStatus.DRAFT,
            order_date=order_date,
            expected_delivery_date=expected_delivery_date,
            payment_terms=payment_terms,
            shipping_cost=shipping_cost,
            currency=currency,
            shipping_address=shipping_address.strip(),
            billing_address=billing_address.strip(),
            notes=notes.strip(),
            created_by=created_by,
        )

        if lines_data:
            for idx, item in enumerate(lines_data, start=1):
                PurchaseOrderLine.objects.create(
                    purchase_order=po,
                    line_number=idx,
                    product=item["product"],
                    ordered_quantity=item["ordered_quantity"],
                    uom=item.get("uom") or item["product"].uom,
                    unit_price=item["unit_price"],
                    tax_rate=item.get("tax_rate", Decimal("0.00")),
                    notes=item.get("notes", "").strip(),
                )

        po.recalculate_totals()
        return po

    @classmethod
    @transaction.atomic
    def convert_rfq_to_po(cls, rfq: RequestForQuotation, created_by=None) -> PurchaseOrder:
        """
        Converts the winning bid of an awarded RFQ into a formalized commercial Purchase Order.
        """
        winning_bid = rfq.winning_bid
        if not winning_bid:
            raise ValidationError("RFQ has no awarded winning bid to convert into a Purchase Order.")

        lines_data = []
        for b_line in winning_bid.lines.select_related("rfq_line__product", "rfq_line__uom"):
            lines_data.append({
                "product": b_line.rfq_line.product,
                "ordered_quantity": b_line.offered_quantity,
                "uom": b_line.rfq_line.uom,
                "unit_price": b_line.offered_unit_price,
                "tax_rate": Decimal("0.00"),
                "notes": f"Awarded from {rfq.rfq_number} Line #{b_line.rfq_line.line_number}",
            })

        expected_date = None
        if winning_bid.lead_time_days:
            expected_date = (timezone.now() + timezone.timedelta(days=winning_bid.lead_time_days)).date()

        po = cls.create_po(
            organization=rfq.organization,
            supplier=winning_bid.supplier,
            order_date=timezone.now().date(),
            expected_delivery_date=expected_date,
            payment_terms=winning_bid.payment_terms,
            shipping_cost=winning_bid.shipping_cost,
            currency=winning_bid.currency,
            notes=f"Generated from competitive bidding on {rfq.rfq_number}: {rfq.title}\n{winning_bid.notes}",
            lines_data=lines_data,
            created_by=created_by,
            rfq=rfq,
        )
        return po

    @classmethod
    @transaction.atomic
    def submit_for_approval(cls, po: PurchaseOrder, submitted_by=None) -> PurchaseOrder:
        """
        Validates PO requirements and sets up required approval gates based on financial thresholds.
        """
        if not po.can_submit_for_approval:
            raise ValidationError("PO must be in draft status with at least one line item.")

        po.recalculate_totals()
        po.status = POStatus.PENDING_APPROVAL
        po.save(update_fields=["status", "updated_at"])

        # Determine approval tiers based on total amount
        # Tier 1 (All POs): Manager
        PurchaseOrderApproval.objects.create(
            purchase_order=po,
            tier=ApprovalTier.TIER_1_MANAGER,
            threshold_amount=Decimal("10000.00"),
            status="pending",
        )

        if po.total_amount > Decimal("10000.00"):
            PurchaseOrderApproval.objects.create(
                purchase_order=po,
                tier=ApprovalTier.TIER_2_DIRECTOR,
                threshold_amount=Decimal("50000.00"),
                status="pending",
            )

        if po.total_amount > Decimal("50000.00"):
            PurchaseOrderApproval.objects.create(
                purchase_order=po,
                tier=ApprovalTier.TIER_3_EXECUTIVE,
                threshold_amount=Decimal("999999999.00"),
                status="pending",
            )

        return po

    @classmethod
    @transaction.atomic
    def approve_po(cls, po: PurchaseOrder, approver, comments: str = "") -> PurchaseOrder:
        """
        Records an approver's authorization decision and promotes the PO to APPROVED
        once all required tier gates are satisfied.
        """
        if po.status != POStatus.PENDING_APPROVAL:
            raise ValidationError("PO is not currently pending approval.")

        pending_gate = po.approvals.filter(status="pending").order_by("tier").first()
        if not pending_gate:
            # All gates already satisfied
            po.status = POStatus.APPROVED
            po.approved_by = approver
            po.approved_at = timezone.now()
            po.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
            return po

        pending_gate.status = "approved"
        pending_gate.approver = approver
        pending_gate.comments = comments.strip()
        pending_gate.decided_at = timezone.now()
        pending_gate.save()

        # Check if more gates remain
        remaining = po.approvals.filter(status="pending").exists()
        if not remaining:
            po.status = POStatus.APPROVED
            po.approved_by = approver
            po.approved_at = timezone.now()
            po.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])

        return po

    @classmethod
    @transaction.atomic
    def reject_po(cls, po: PurchaseOrder, rejector, comments: str) -> PurchaseOrder:
        """
        Rejects the purchase order and records reviewer comments.
        """
        if po.status != POStatus.PENDING_APPROVAL:
            raise ValidationError("PO is not currently pending approval.")

        pending_gate = po.approvals.filter(status="pending").first()
        if pending_gate:
            pending_gate.status = "rejected"
            pending_gate.approver = rejector
            pending_gate.comments = comments.strip()
            pending_gate.decided_at = timezone.now()
            pending_gate.save()

        po.status = POStatus.REJECTED
        po.save(update_fields=["status", "updated_at"])
        return po

    @classmethod
    def issue_po(cls, po: PurchaseOrder, issued_by=None) -> PurchaseOrder:
        """
        Marks approved PO as officially issued to the vendor.
        """
        if po.status != POStatus.APPROVED:
            raise ValidationError("Only APPROVED purchase orders can be issued to vendors.")

        po.status = POStatus.ISSUED
        po.issued_at = timezone.now()
        po.save(update_fields=["status", "issued_at", "updated_at"])
        return po


from .models import (
    BillStatus,
    MatchStatus,
    VendorBill,
    VendorBillLine,
    ThreeWayMatch,
)


class ThreeWayMatchService:
    """
    Automated Three-Way Matching engine reconciling Purchase Orders, Warehouse Goods Receipts,
    and Vendor Invoices to ensure commercial integrity before disbursements.
    """

    @classmethod
    @transaction.atomic
    def create_vendor_bill(
        cls,
        organization: Organization,
        supplier: Supplier,
        bill_number: str,
        bill_date,
        due_date,
        purchase_order: Optional[PurchaseOrder] = None,
        currency: str = "USD",
        notes: str = "",
        lines_data: Optional[List[Dict]] = None,
        created_by=None,
    ) -> VendorBill:
        """
        Creates a vendor bill with priced lines.
        """
        bill = VendorBill.objects.create(
            organization=organization,
            supplier=supplier,
            purchase_order=purchase_order,
            bill_number=bill_number.strip(),
            status=BillStatus.PENDING_MATCH if purchase_order else BillStatus.DRAFT,
            bill_date=bill_date,
            due_date=due_date,
            currency=currency,
            notes=notes.strip(),
            created_by=created_by,
        )

        if lines_data:
            for item in lines_data:
                VendorBillLine.objects.create(
                    bill=bill,
                    po_line=item.get("po_line"),
                    product=item["product"],
                    billed_quantity=item["billed_quantity"],
                    unit_price=item["unit_price"],
                    tax_rate=item.get("tax_rate", Decimal("0.00")),
                    notes=item.get("notes", "").strip(),
                )

        bill.recalculate_totals()
        return bill

    @classmethod
    @transaction.atomic
    def execute_three_way_match(
        cls,
        purchase_order: PurchaseOrder,
        vendor_bill: VendorBill,
        tolerance_amount: Decimal = Decimal("50.00"),
    ) -> ThreeWayMatch:
        """
        Performs 3-Way Match evaluation across PO lines, Goods Receipts, and Invoiced quantities.
        """
        po_total_qty = sum((line.ordered_quantity for line in purchase_order.lines.all()), Decimal("0.00"))
        # In a real warehouse flow, received_quantity is updated via goods receipts; fallback to ordered if already issued/received
        warehouse_received_qty = sum((line.received_quantity for line in purchase_order.lines.all()), Decimal("0.00"))
        if warehouse_received_qty == Decimal("0.00") and purchase_order.status in (POStatus.ISSUED, POStatus.COMPLETED):
            warehouse_received_qty = po_total_qty

        invoice_billed_qty = sum((line.billed_quantity for line in vendor_bill.lines.all()), Decimal("0.00"))
        qty_variance = invoice_billed_qty - warehouse_received_qty

        po_amount = purchase_order.total_amount
        billed_amount = vendor_bill.total_amount
        price_var_amount = billed_amount - po_amount

        # Evaluate match status
        is_exact = (qty_variance == Decimal("0.00") and price_var_amount == Decimal("0.00"))
        within_tolerance = abs(price_var_amount) <= tolerance_amount and qty_variance <= Decimal("0.00")

        if is_exact:
            match_outcome = MatchStatus.MATCHED
            bill_status = BillStatus.MATCHED
        elif within_tolerance:
            match_outcome = MatchStatus.TOLERANCE_ACCEPTED
            bill_status = BillStatus.MATCHED
        elif qty_variance != Decimal("0.00"):
            match_outcome = MatchStatus.QUANTITY_VARIANCE
            bill_status = BillStatus.DISPUTED
        else:
            match_outcome = MatchStatus.PRICE_VARIANCE
            bill_status = BillStatus.DISPUTED

        match_record = ThreeWayMatch.objects.create(
            organization=purchase_order.organization,
            purchase_order=purchase_order,
            vendor_bill=vendor_bill,
            status=match_outcome,
            po_total_ordered=po_total_qty,
            warehouse_received=warehouse_received_qty,
            invoice_billed=invoice_billed_qty,
            quantity_variance=qty_variance,
            po_amount=po_amount,
            billed_amount=billed_amount,
            price_variance_amount=price_var_amount,
            is_within_tolerance=within_tolerance,
            dispute_reason="" if is_exact or within_tolerance else f"Variance detected: Qty variance {qty_variance}, Financial variance ${price_var_amount}",
        )

        vendor_bill.match_status = match_outcome
        vendor_bill.status = bill_status
        vendor_bill.save(update_fields=["match_status", "status", "updated_at"])

        return match_record

    @classmethod
    @transaction.atomic
    def resolve_match_dispute(
        cls,
        match_record: ThreeWayMatch,
        user,
        resolution_notes: str,
    ) -> ThreeWayMatch:
        """
        Authorizes variance override or applies dispute settlement.
        """
        match_record.status = MatchStatus.RESOLVED
        match_record.resolution_notes = resolution_notes.strip()
        match_record.resolved_by = user
        match_record.resolved_at = timezone.now()
        match_record.save()

        match_record.vendor_bill.match_status = MatchStatus.RESOLVED
        match_record.vendor_bill.status = BillStatus.MATCHED
        match_record.vendor_bill.save(update_fields=["match_status", "status", "updated_at"])

        return match_record

    @classmethod
    def get_procurement_dashboard_metrics(cls, organization: Organization) -> Dict:
        """
        Computes executive procurement KPIs and sourcing performance analytics.
        """
        from django.db.models import Sum, Count

        total_suppliers = Supplier.objects.filter(organization=organization, is_active=True).count()
        open_rfqs = RequestForQuotation.objects.filter(organization=organization, status=RFQStatus.PUBLISHED).count()

        active_pos_qs = PurchaseOrder.objects.filter(
            organization=organization,
            status__in=[POStatus.APPROVED, POStatus.ISSUED, POStatus.PARTIALLY_RECEIVED],
        )
        total_active_pos = active_pos_qs.count()
        total_committed_spend = active_pos_qs.aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")

        bills_qs = VendorBill.objects.filter(organization=organization)
        total_bills = bills_qs.count()
        matched_bills = bills_qs.filter(match_status__in=[MatchStatus.MATCHED, MatchStatus.TOLERANCE_ACCEPTED, MatchStatus.RESOLVED]).count()
        disputed_bills = bills_qs.filter(status=BillStatus.DISPUTED).count()

        if total_bills > 0:
            match_accuracy = round((matched_bills / total_bills) * 100, 1)
        else:
            match_accuracy = 100.0

        recent_rfqs = RequestForQuotation.objects.filter(organization=organization).order_by("-created_at")[:5]
        recent_pos = PurchaseOrder.objects.filter(organization=organization).select_related("supplier").order_by("-created_at")[:5]
        recent_bills = VendorBill.objects.filter(organization=organization).select_related("supplier", "purchase_order").order_by("-created_at")[:5]

        top_suppliers = (
            Supplier.objects.filter(organization=organization, is_active=True)
            .annotate(total_spend=Sum("purchase_orders__total_amount"))
            .filter(total_spend__gt=Decimal("0.00"))
            .order_by("-total_spend")[:5]
        )

        return {
            "total_suppliers": total_suppliers,
            "open_rfqs": open_rfqs,
            "total_active_pos": total_active_pos,
            "total_committed_spend": total_committed_spend,
            "total_bills": total_bills,
            "matched_bills": matched_bills,
            "disputed_bills": disputed_bills,
            "match_accuracy": match_accuracy,
            "recent_rfqs": recent_rfqs,
            "recent_pos": recent_pos,
            "recent_bills": recent_bills,
            "top_suppliers": top_suppliers,
        }
