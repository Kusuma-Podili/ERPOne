"""
EnterpriseOne Inventory & Warehouse Management Domain Services.
Provides warehouse spatial hierarchy automation, location coordinate resolution,
and real-time stock allocation/reservation logic.
"""
from decimal import Decimal
from typing import Optional, List, Dict
from django.db import transaction
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
