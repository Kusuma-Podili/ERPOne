"""
EnterpriseOne Inventory & Warehouse Management Domain Services.
Provides warehouse spatial hierarchy automation, location coordinate resolution,
and real-time stock allocation/reservation logic.
"""
from decimal import Decimal
from datetime import timedelta
from typing import Optional, List, Dict
from django.db import transaction, models
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.organizations.models import Organization
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


class WarehouseHierarchyService:
    """
    Automates warehouse provisioning, zone setup, coordinate addressing, and location capacity management.
    """

    @classmethod
    @transaction.atomic
    def provision_standard_warehouse(
        cls,
        organization: Organization,
        name: str,
        code: str,
        warehouse_type: str = WarehouseType.DISTRIBUTION_CENTER,
        address: str = "",
        city: str = "",
        state_province: str = "",
        postal_code: str = "",
        country: str = "USA",
        is_primary: bool = False,
        manager=None,
    ) -> Dict:
        """
        Provisions a complete logistics facility with industry-standard functional zones
        and default high-density storage locations.
        """
        warehouse = Warehouse.objects.create(
            organization=organization,
            name=name,
            code=code.upper(),
            warehouse_type=warehouse_type,
            address=address,
            city=city,
            state_province=state_province,
            postal_code=postal_code,
            country=country,
            is_primary=is_primary,
            manager=manager,
        )

        # Standard functional operational zones
        standard_zones = [
            ("Receiving Dock", "Z-REC", StorageZoneType.RECEIVING, False, None),
            ("General Storage", "Z-GEN", StorageZoneType.GENERAL, False, None),
            ("Fast-Pick Forward Area", "Z-PICK", StorageZoneType.PICKING, False, None),
            ("Outbound Staging & Shipping", "Z-SHIP", StorageZoneType.SHIPPING, False, None),
            ("Quality Quarantine", "Z-QUAR", StorageZoneType.QUARANTINE, False, None),
        ]

        created_zones = []
        for z_name, z_code, z_type, temp_ctl, temp_val in standard_zones:
            zone = StorageZone.objects.create(
                organization=organization,
                warehouse=warehouse,
                name=z_name,
                code=z_code,
                zone_type=z_type,
                temperature_controlled=temp_ctl,
                target_temp_celsius=temp_val,
            )
            created_zones.append(zone)

        # Provision initial storage bins in General Storage (Aisle 01, Rack 01, Shelf 01..03, Bin 01..04)
        gen_zone = next(z for z in created_zones if z.code == "Z-GEN")
        created_locations = []
        for shelf_num in ["01", "02"]:
            for bin_num in ["01", "02", "03", "04"]:
                loc = StorageLocation.objects.create(
                    organization=organization,
                    warehouse=warehouse,
                    zone=gen_zone,
                    aisle="01",
                    rack="01",
                    shelf=shelf_num,
                    bin=bin_num,
                )
                created_locations.append(loc)

        return {
            "warehouse": warehouse,
            "zones": created_zones,
            "locations": created_locations,
        }

    @classmethod
    def create_location(
        cls,
        warehouse: Warehouse,
        zone: StorageZone,
        aisle: str,
        rack: str,
        shelf: str,
        bin: str,
        max_weight_kg: Optional[Decimal] = None,
        max_volume_cbm: Optional[Decimal] = None,
    ) -> StorageLocation:
        """
        Creates a validated storage location within a designated warehouse zone.
        """
        if zone.warehouse_id != warehouse.id:
            raise ValidationError("Storage zone does not belong to the target warehouse.")

        kwargs = {
            "organization": warehouse.organization,
            "warehouse": warehouse,
            "zone": zone,
            "aisle": str(aisle).zfill(2),
            "rack": str(rack).zfill(2),
            "shelf": str(shelf).zfill(2),
            "bin": str(bin).zfill(2),
        }
        if max_weight_kg is not None:
            kwargs["max_weight_kg"] = max_weight_kg
        if max_volume_cbm is not None:
            kwargs["max_volume_cbm"] = max_volume_cbm

        loc = StorageLocation(**kwargs)
        loc.code = loc.generate_location_code()
        loc.save()
        return loc

    @classmethod
    def lock_location(cls, location: StorageLocation, reason: str = "") -> StorageLocation:
        """Locks a location to prevent putaway and pick activities."""
        location.is_locked = True
        location.lock_reason = reason or "Maintenance / Cycle Count Lock"
        location.save(update_fields=["is_locked", "lock_reason", "updated_at"])
        return location

    @classmethod
    def unlock_location(cls, location: StorageLocation) -> StorageLocation:
        """Unlocks a storage location for active warehousing operations."""
        location.is_locked = False
        location.lock_reason = ""
        location.save(update_fields=["is_locked", "lock_reason", "updated_at"])
        return location


class StockLevelService:
    """
    High-precision stock ledger service governing on-hand quantities, order reservations,
    available balances, and replenishment alerts.
    """

    @classmethod
    def get_or_create_stock_item(
        cls,
        product: Product,
        warehouse: Warehouse,
        location: Optional[StorageLocation] = None,
    ) -> StockItem:
        """
        Retrieves or initializes a stock item tracking record for a product at a warehouse/location.
        """
        stock_item, created = StockItem.objects.get_or_create(
            organization=warehouse.organization,
            product=product,
            warehouse=warehouse,
            location=location,
            defaults={
                "quantity_on_hand": Decimal("0.00"),
                "quantity_reserved": Decimal("0.00"),
                "safety_stock": Decimal("10.00"),
                "reorder_point": Decimal("25.00"),
                "reorder_quantity": Decimal("50.00"),
            },
        )
        return stock_item

    @classmethod
    def get_total_available_stock(
        cls,
        product: Product,
        warehouse: Optional[Warehouse] = None,
    ) -> Decimal:
        """
        Calculates aggregate uncommitted available inventory across active warehouse locations.
        """
        qs = StockItem.objects.filter(
            product=product,
            organization=product.organization,
        )
        if warehouse:
            qs = qs.filter(warehouse=warehouse)

        total_available = Decimal("0.00")
        for item in qs:
            total_available += item.quantity_available
        return total_available

    @classmethod
    @transaction.atomic
    def reserve_stock(
        cls,
        product: Product,
        warehouse: Warehouse,
        quantity: Decimal,
        location: Optional[StorageLocation] = None,
    ) -> StockItem:
        """
        Earmarks physical inventory against a confirmed sales order.
        Raises ValidationError if insufficient unreserved stock exists.
        """
        if quantity <= Decimal("0.00"):
            raise ValidationError("Quantity to reserve must be greater than zero.")

        stock_item = cls.get_or_create_stock_item(product, warehouse, location)

        if stock_item.quantity_available < quantity:
            raise ValidationError(
                f"Insufficient available stock for product '{product.name}' in warehouse '{warehouse.code}'. "
                f"Requested: {quantity}, Available: {stock_item.quantity_available}."
            )

        stock_item.quantity_reserved += quantity
        stock_item.save(update_fields=["quantity_reserved", "updated_at"])
        return stock_item

    @classmethod
    @transaction.atomic
    def release_reserved_stock(
        cls,
        product: Product,
        warehouse: Warehouse,
        quantity: Decimal,
        location: Optional[StorageLocation] = None,
    ) -> StockItem:
        """
        Releases reserved stock back into the general uncommitted pool.
        """
        if quantity <= Decimal("0.00"):
            raise ValidationError("Quantity to release must be greater than zero.")

        stock_item = cls.get_or_create_stock_item(product, warehouse, location)

        if stock_item.quantity_reserved < quantity:
            # Clamp to reserved quantity to prevent negative numbers
            actual_release = stock_item.quantity_reserved
        else:
            actual_release = quantity

        stock_item.quantity_reserved -= actual_release
        stock_item.save(update_fields=["quantity_reserved", "updated_at"])
        return stock_item

    @classmethod
    @transaction.atomic
    def adjust_physical_stock(
        cls,
        product: Product,
        warehouse: Warehouse,
        location: Optional[StorageLocation],
        delta_quantity: Decimal,
    ) -> StockItem:
        """
        Increases or decreases physical stock on-hand.
        Enforces non-negative inventory invariants.
        """
        stock_item = cls.get_or_create_stock_item(product, warehouse, location)

        new_on_hand = stock_item.quantity_on_hand + delta_quantity
        if new_on_hand < Decimal("0.00"):
            raise ValidationError(
                f"Stock adjustment would result in negative inventory ({new_on_hand}) "
                f"for '{product.name}' at '{warehouse.code}'."
            )
        if new_on_hand < stock_item.quantity_reserved:
            raise ValidationError(
                f"Cannot reduce stock below current reserved quantity ({stock_item.quantity_reserved})."
            )

        stock_item.quantity_on_hand = new_on_hand
        stock_item.save(update_fields=["quantity_on_hand", "updated_at"])
        return stock_item

    @classmethod
    def get_reorder_alerts(
        cls,
        organization: Organization,
        warehouse: Optional[Warehouse] = None,
    ) -> List[StockItem]:
        """
        Identifies inventory items that have breached safety stock or reorder point thresholds.
        """
        qs = StockItem.objects.filter(organization=organization).select_related("product", "warehouse", "location")
        if warehouse:
            qs = qs.filter(warehouse=warehouse)

        alerts = [item for item in qs if item.needs_reorder]
        return alerts


class StockMovementService:
    """
    Transactional stock movement service ensuring double-entry balance integrity across warehouses
    and bin locations for receipts, transfers, relocations, and inventory write-offs.
    """

    @classmethod
    @transaction.atomic
    def create_movement(
        cls,
        organization: Organization,
        movement_type: str,
        source_warehouse: Optional[Warehouse] = None,
        destination_warehouse: Optional[Warehouse] = None,
        reference_document: str = "",
        movement_date=None,
        notes: str = "",
        created_by=None,
        lines_data: Optional[List[Dict]] = None,
    ) -> StockMovement:
        """
        Initializes a stock movement header document and optionally attaches line items.
        """
        movement = StockMovement(
            organization=organization,
            movement_type=movement_type,
            source_warehouse=source_warehouse,
            destination_warehouse=destination_warehouse,
            reference_document=reference_document,
            notes=notes,
            created_by=created_by,
        )
        if movement_date:
            movement.movement_date = movement_date
        movement.full_clean()
        movement.save()

        if lines_data:
            for line_item in lines_data:
                cls.add_movement_line(
                    movement=movement,
                    product=line_item["product"],
                    quantity=line_item["quantity"],
                    source_location=line_item.get("source_location"),
                    destination_location=line_item.get("destination_location"),
                    unit_cost=line_item.get("unit_cost", Decimal("0.00")),
                    batch_number=line_item.get("batch_number", ""),
                    serial_number=line_item.get("serial_number", ""),
                    notes=line_item.get("notes", ""),
                )

        return movement

    @classmethod
    def add_movement_line(
        cls,
        movement: StockMovement,
        product: Product,
        quantity: Decimal,
        source_location: Optional[StorageLocation] = None,
        destination_location: Optional[StorageLocation] = None,
        unit_cost: Decimal = Decimal("0.00"),
        batch_number: str = "",
        serial_number: str = "",
        notes: str = "",
    ) -> StockMovementLine:
        """
        Adds a line item to a draft or approved stock movement document.
        """
        if movement.status not in [StockMovementStatus.DRAFT, StockMovementStatus.APPROVED]:
            raise ValidationError("Cannot modify lines on a movement that is not Draft or Approved.")

        if quantity <= Decimal("0.00"):
            raise ValidationError("Quantity moved must be greater than zero.")

        line = StockMovementLine(
            movement=movement,
            product=product,
            source_location=source_location,
            destination_location=destination_location,
            quantity=quantity,
            unit_cost=unit_cost,
            batch_number=batch_number,
            serial_number=serial_number,
            notes=notes,
        )
        line.full_clean()
        line.save()
        return line

    @classmethod
    @transaction.atomic
    def post_movement(
        cls,
        movement: StockMovement,
        posted_by=None,
    ) -> StockMovement:
        """
        Atomically executes the stock movement, debiting and crediting inventory balances.
        """
        if not movement.can_post:
            raise ValidationError(
                f"Movement '{movement.movement_number}' is {movement.get_status_display()} and cannot be posted."
            )

        lines = movement.lines.select_related("product", "source_location", "destination_location").all()
        if not lines.exists():
            raise ValidationError("Cannot post a stock movement document with no line items.")

        # Execute stock ledger balance shifts according to movement type
        for line in lines:
            if movement.movement_type == StockMovementType.RECEIPT:
                # Inbound goods receipt -> Increment destination warehouse
                StockLevelService.adjust_physical_stock(
                    product=line.product,
                    warehouse=movement.destination_warehouse,
                    location=line.destination_location,
                    delta_quantity=line.quantity,
                )

            elif movement.movement_type == StockMovementType.TRANSFER:
                # Inter-warehouse transfer -> Decrement source, Increment destination
                StockLevelService.adjust_physical_stock(
                    product=line.product,
                    warehouse=movement.source_warehouse,
                    location=line.source_location,
                    delta_quantity=-line.quantity,
                )
                StockLevelService.adjust_physical_stock(
                    product=line.product,
                    warehouse=movement.destination_warehouse,
                    location=line.destination_location,
                    delta_quantity=line.quantity,
                )

            elif movement.movement_type == StockMovementType.LOCATION_TRANSFER:
                # Intra-warehouse relocation between bins
                StockLevelService.adjust_physical_stock(
                    product=line.product,
                    warehouse=movement.source_warehouse,
                    location=line.source_location,
                    delta_quantity=-line.quantity,
                )
                StockLevelService.adjust_physical_stock(
                    product=line.product,
                    warehouse=movement.source_warehouse,
                    location=line.destination_location,
                    delta_quantity=line.quantity,
                )

            elif movement.movement_type in [StockMovementType.SCRAP, StockMovementType.ADJUSTMENT]:
                # Negative adjustment / scrap write-off -> Decrement source
                StockLevelService.adjust_physical_stock(
                    product=line.product,
                    warehouse=movement.source_warehouse,
                    location=line.source_location,
                    delta_quantity=-line.quantity,
                )

            elif movement.movement_type == StockMovementType.RETURN:
                # Customer / RMA return -> Increment destination
                StockLevelService.adjust_physical_stock(
                    product=line.product,
                    warehouse=movement.destination_warehouse,
                    location=line.destination_location,
                    delta_quantity=line.quantity,
                )

        movement.status = StockMovementStatus.COMPLETED
        movement.posted_at = timezone.now()
        movement.posted_by = posted_by
        movement.save(update_fields=["status", "posted_at", "posted_by", "updated_at"])
        return movement

    @classmethod
    @transaction.atomic
    def cancel_movement(
        cls,
        movement: StockMovement,
        cancelled_by=None,
        reason: str = "",
    ) -> StockMovement:
        """
        Cancels an unposted stock movement document.
        """
        if not movement.can_cancel:
            raise ValidationError(
                f"Movement '{movement.movement_number}' is already {movement.get_status_display()} and cannot be cancelled."
            )

        movement.status = StockMovementStatus.CANCELLED
        if reason:
            movement.notes = (movement.notes + f"\n[Cancelled: {reason}]").strip()
        movement.save(update_fields=["status", "notes", "updated_at"])
        return movement

    @classmethod
    def get_ledger_history(
        cls,
        organization: Organization,
        product: Optional[Product] = None,
        warehouse: Optional[Warehouse] = None,
    ):
        """
        Retrieves chronological ledger audit entries for completed stock movements.
        """
        qs = StockMovementLine.objects.filter(
            movement__organization=organization,
            movement__status=StockMovementStatus.COMPLETED,
        ).select_related(
            "movement",
            "product",
            "movement__source_warehouse",
            "movement__destination_warehouse",
            "source_location",
            "destination_location",
            "movement__posted_by",
        ).order_by("-movement__posted_at", "-created_at")

        if product:
            qs = qs.filter(product=product)
        if warehouse:
            qs = qs.filter(
                models.Q(movement__source_warehouse=warehouse) |
                models.Q(movement__destination_warehouse=warehouse)
            )

        return qs


class LotSerialTrackingService:
    """
    Quality control, batch expiry tracking, FEFO (First-Expired, First-Out) picking allocation,
    and individual asset serialization service.
    """

    @classmethod
    def register_lot(
        cls,
        organization: Organization,
        product: Product,
        batch_number: str,
        manufacturing_date=None,
        expiration_date=None,
        supplier_lot_number: str = "",
        initial_quantity: Decimal = Decimal("0.00"),
        qc_status: str = QCStatus.APPROVED,
        qc_notes: str = "",
        certificate_of_analysis: str = "",
    ) -> LotBatch:
        """
        Registers a production batch or supplier lot.
        """
        lot = LotBatch(
            organization=organization,
            product=product,
            batch_number=batch_number.strip().upper(),
            manufacturing_date=manufacturing_date,
            expiration_date=expiration_date,
            supplier_lot_number=supplier_lot_number.strip(),
            initial_quantity=initial_quantity,
            current_quantity=initial_quantity,
            qc_status=qc_status,
            qc_notes=qc_notes,
            certificate_of_analysis=certificate_of_analysis,
        )
        lot.full_clean()
        lot.save()
        return lot

    @classmethod
    def update_qc_status(
        cls,
        lot: LotBatch,
        new_status: str,
        inspected_by=None,
        qc_notes: str = "",
    ) -> LotBatch:
        """
        Transitions a lot through QC quarantine, approval, rejection, or expiration.
        """
        if new_status not in QCStatus.values:
            raise ValidationError(f"Invalid QC status: '{new_status}'.")

        lot.qc_status = new_status
        lot.qc_inspected_by = inspected_by
        lot.qc_inspected_at = timezone.now()
        if qc_notes:
            lot.qc_notes = (lot.qc_notes + f"\n[{timezone.now().strftime('%Y-%m-%d %H:%M')}] {qc_notes}").strip()
        lot.save(update_fields=["qc_status", "qc_inspected_by", "qc_inspected_at", "qc_notes", "updated_at"])
        return lot

    @classmethod
    def adjust_lot_quantity(cls, lot: LotBatch, delta_quantity: Decimal) -> LotBatch:
        """
        Updates running physical on-hand quantity for a tracked lot.
        """
        new_qty = lot.current_quantity + delta_quantity
        if new_qty < Decimal("0.00"):
            raise ValidationError(
                f"Lot quantity adjustment cannot reduce current quantity below zero (Current: {lot.current_quantity}, Delta: {delta_quantity})."
            )
        lot.current_quantity = new_qty
        lot.save(update_fields=["current_quantity", "updated_at"])
        return lot

    @classmethod
    def register_serial(
        cls,
        organization: Organization,
        product: Product,
        serial_number: str,
        lot: Optional[LotBatch] = None,
        warehouse: Optional[Warehouse] = None,
        location: Optional[StorageLocation] = None,
        warranty_start_date=None,
        warranty_end_date=None,
        notes: str = "",
    ) -> SerialNumber:
        """
        Enrolls an individually tracked serialized unit into the inventory system.
        """
        serial = SerialNumber(
            organization=organization,
            product=product,
            serial_number=serial_number.strip().upper(),
            lot=lot,
            warehouse=warehouse,
            location=location,
            status=SerialStatus.IN_STOCK,
            warranty_start_date=warranty_start_date,
            warranty_end_date=warranty_end_date,
            notes=notes,
        )
        serial.full_clean()
        serial.save()
        return serial

    @classmethod
    @transaction.atomic
    def bulk_register_serials(
        cls,
        organization: Organization,
        product: Product,
        serial_numbers_list: List[str],
        lot: Optional[LotBatch] = None,
        warehouse: Optional[Warehouse] = None,
        location: Optional[StorageLocation] = None,
        warranty_start_date=None,
        warranty_end_date=None,
    ) -> List[SerialNumber]:
        """
        High-performance bulk registration of serialized goods.
        """
        created_objects = []
        for raw_sn in serial_numbers_list:
            sn_cleaned = raw_sn.strip().upper()
            if not sn_cleaned:
                continue
            serial = SerialNumber(
                organization=organization,
                product=product,
                serial_number=sn_cleaned,
                lot=lot,
                warehouse=warehouse,
                location=location,
                status=SerialStatus.IN_STOCK,
                warranty_start_date=warranty_start_date,
                warranty_end_date=warranty_end_date,
            )
            serial.full_clean()
            serial.save()
            created_objects.append(serial)
        return created_objects

    @classmethod
    def update_serial_status(
        cls,
        serial: SerialNumber,
        new_status: str,
        warehouse: Optional[Warehouse] = None,
        location: Optional[StorageLocation] = None,
        notes: str = "",
    ) -> SerialNumber:
        """
        Updates unit status and relocation metadata.
        """
        if new_status not in SerialStatus.values:
            raise ValidationError(f"Invalid serial status: '{new_status}'.")

        serial.status = new_status
        if warehouse is not None:
            serial.warehouse = warehouse
        if location is not None:
            serial.location = location
        if notes:
            serial.notes = (serial.notes + f"\n[{timezone.now().strftime('%Y-%m-%d')}] {notes}").strip()
        serial.save()
        return serial

    @classmethod
    def get_expiring_batches(
        cls,
        organization: Organization,
        days_threshold: int = 30,
        product: Optional[Product] = None,
    ):
        """
        Returns batches expiring within specified threshold or already expired.
        Sorted by expiration date ascending for urgent intervention.
        """
        from datetime import timedelta
        cutoff_date = timezone.now().date() + timedelta(days=days_threshold)
        qs = LotBatch.objects.filter(
            organization=organization,
            is_active=True,
            expiration_date__isnull=False,
            expiration_date__lte=cutoff_date,
        ).select_related("product")

        if product:
            qs = qs.filter(product=product)

        return qs.order_by("expiration_date")

    @classmethod
    def get_fefo_allocation(
        cls,
        organization: Organization,
        product: Product,
        requested_quantity: Decimal,
    ) -> Dict:
        """
        First-Expired, First-Out (FEFO) recommendation algorithm.
        Identifies active, approved lots with the closest expiry date to allocate for picking.
        """
        if requested_quantity <= Decimal("0.00"):
            raise ValidationError("Requested allocation quantity must be greater than zero.")

        usable_lots = LotBatch.objects.filter(
            organization=organization,
            product=product,
            is_active=True,
            qc_status=QCStatus.APPROVED,
            current_quantity__gt=Decimal("0.00"),
        ).order_by("expiration_date", "created_at")

        allocations = []
        remaining_needed = requested_quantity

        for lot in usable_lots:
            if remaining_needed <= Decimal("0.00"):
                break
            alloc_qty = min(lot.current_quantity, remaining_needed)
            allocations.append({
                "lot": lot,
                "batch_number": lot.batch_number,
                "expiration_date": lot.expiration_date,
                "allocated_quantity": alloc_qty,
                "lot_available_before": lot.current_quantity,
            })
            remaining_needed -= alloc_qty

        return {
            "requested_quantity": requested_quantity,
            "allocated_quantity": requested_quantity - remaining_needed,
            "unallocated_quantity": remaining_needed,
            "is_fully_allocated": remaining_needed == Decimal("0.00"),
            "allocations": allocations,
        }


class ReplenishmentService:
    """
    Automated inventory replenishment engine scanning reorder thresholds and provisioning
    purchase demand requisitions.
    """

    @classmethod
    @transaction.atomic
    def evaluate_reorder_triggers(
        cls,
        organization: Organization,
        warehouse: Optional[Warehouse] = None,
        requested_by=None,
    ) -> List[PurchaseRequisition]:
        """
        Scans current inventory balances against established ReorderRule and safety stock thresholds.
        Aggregates items requiring replenishment into draft Purchase Requisitions grouped by warehouse.
        """
        stock_qs = StockItem.objects.filter(organization=organization).select_related("product", "warehouse")
        if warehouse:
            stock_qs = stock_qs.filter(warehouse=warehouse)

        # Map rules by (warehouse_id, product_id)
        rules_qs = ReorderRule.objects.filter(organization=organization, is_active=True)
        if warehouse:
            rules_qs = rules_qs.filter(warehouse=warehouse)
        rules_map = {(r.warehouse_id, r.product_id): r for r in rules_qs}

        warehouse_deficits: Dict[Warehouse, List[Dict]] = {}

        for item in stock_qs:
            rule = rules_map.get((item.warehouse_id, item.product_id))
            min_thresh = rule.min_quantity if rule else item.reorder_point
            reorder_qty = rule.reorder_quantity if rule else item.reorder_quantity

            # Check if threshold is breached
            if item.quantity_on_hand <= min_thresh:
                wh = item.warehouse
                if wh not in warehouse_deficits:
                    warehouse_deficits[wh] = []

                warehouse_deficits[wh].append({
                    "product": item.product,
                    "quantity_requested": reorder_qty,
                    "estimated_unit_cost": item.product.cost_price,
                    "notes": f"Automated replenishment trigger: On-Hand {item.quantity_on_hand} <= Min {min_thresh}",
                })

        created_requisitions = []
        for wh, lines in warehouse_deficits.items():
            if not lines:
                continue
            req = cls.create_requisition(
                organization=organization,
                warehouse=wh,
                priority=RequisitionPriority.MEDIUM,
                lines_data=lines,
                requested_by=requested_by,
                justification=f"System automated stock replenishment evaluation for {wh.name}.",
            )
            created_requisitions.append(req)

        return created_requisitions

    @classmethod
    @transaction.atomic
    def create_requisition(
        cls,
        organization: Organization,
        warehouse: Warehouse,
        priority: str = RequisitionPriority.MEDIUM,
        lines_data: Optional[List[Dict]] = None,
        requested_by=None,
        justification: str = "",
        required_by_date=None,
    ) -> PurchaseRequisition:
        """
        Instantiates a purchase requisition document and records SKU line demands.
        """
        req = PurchaseRequisition(
            organization=organization,
            warehouse=warehouse,
            priority=priority,
            requested_by=requested_by,
            justification=justification,
            required_by_date=required_by_date,
            status=RequisitionStatus.DRAFT,
        )
        req.full_clean()
        req.save()

        if lines_data:
            for line_data in lines_data:
                line = PurchaseRequisitionLine(
                    requisition=req,
                    product=line_data["product"],
                    quantity_requested=line_data["quantity_requested"],
                    estimated_unit_cost=line_data.get("estimated_unit_cost", line_data["product"].cost_price),
                    notes=line_data.get("notes", ""),
                )
                line.full_clean()
                line.save()

        return req

    @classmethod
    def approve_requisition(cls, requisition: PurchaseRequisition, approved_by) -> PurchaseRequisition:
        """
        Transitions requisition from Draft/Pending to Approved.
        """
        if not requisition.can_approve:
            raise ValidationError(
                f"Requisition '{requisition.requisition_number}' is {requisition.get_status_display()} and cannot be approved."
            )
        requisition.status = RequisitionStatus.APPROVED
        requisition.approved_by = approved_by
        requisition.approved_at = timezone.now()
        requisition.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
        return requisition

    @classmethod
    def cancel_requisition(cls, requisition: PurchaseRequisition, cancelled_by=None, reason: str = "") -> PurchaseRequisition:
        """
        Cancels an open purchase requisition.
        """
        if not requisition.can_cancel:
            raise ValidationError(
                f"Requisition '{requisition.requisition_number}' is already {requisition.get_status_display()} and cannot be cancelled."
            )
        requisition.status = RequisitionStatus.CANCELLED
        if reason:
            requisition.justification = (requisition.justification + f"\n[Cancelled: {reason}]").strip()
        requisition.save(update_fields=["status", "justification", "updated_at"])
        return requisition


class InventoryAnalyticsService:
    """
    Real-time inventory intelligence computing executive KPIs, total valuation,
    stockout risks, and facility space utilization.
    """

    @classmethod
    def get_inventory_kpis(cls, organization: Organization) -> Dict:
        """
        Aggregates operational logistics and inventory metrics across all active facilities.
        """
        from django.db.models import Sum, F

        items_qs = StockItem.objects.filter(organization=organization).select_related("product", "warehouse")
        total_valuation = Decimal("0.00")
        stockout_count = 0
        low_stock_count = 0
        product_ids = set()

        for item in items_qs:
            product_ids.add(item.product_id)
            total_valuation += item.quantity_on_hand * item.product.cost_price
            if item.quantity_on_hand <= Decimal("0.00"):
                stockout_count += 1
            if item.needs_reorder:
                low_stock_count += 1

        warehouses_qs = Warehouse.objects.filter(organization=organization, is_active=True)
        total_warehouses = warehouses_qs.count()
        total_capacity_cbm = warehouses_qs.aggregate(tot=Sum("total_capacity_cbm"))["tot"] or Decimal("0.00")

        pending_requisitions = PurchaseRequisition.objects.filter(
            organization=organization,
            status__in=[RequisitionStatus.DRAFT, RequisitionStatus.PENDING],
        ).count()

        cutoff_date = timezone.now().date() + timedelta(days=30)
        expiring_lots_count = LotBatch.objects.filter(
            organization=organization,
            is_active=True,
            expiration_date__lte=cutoff_date,
        ).count()

        # Top 5 highest valued inventory holdings
        top_items = sorted(items_qs, key=lambda x: x.quantity_on_hand * x.product.cost_price, reverse=True)[:5]
        top_valued_holdings = [
            {
                "product_name": item.product.name,
                "sku": item.product.sku,
                "warehouse_code": item.warehouse.code,
                "on_hand": item.quantity_on_hand,
                "unit_cost": item.product.cost_price,
                "total_value": item.quantity_on_hand * item.product.cost_price,
            }
            for item in top_items
        ]

        return {
            "total_valuation": total_valuation,
            "total_distinct_products": len(product_ids),
            "total_stock_items_count": len(items_qs),
            "stockout_count": stockout_count,
            "low_stock_count": low_stock_count,
            "total_warehouses": total_warehouses,
            "total_capacity_cbm": total_capacity_cbm,
            "pending_requisitions": pending_requisitions,
            "expiring_lots_count": expiring_lots_count,
            "top_valued_holdings": top_valued_holdings,
        }
