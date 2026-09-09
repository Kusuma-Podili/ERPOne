"""
EnterpriseOne Integration Tests — Replenishment Automation & Operations Dashboard (Milestone 5.4).
Validates automated threshold evaluation, purchase demand requisition creation, approval state machines,
executive inventory KPI aggregation, and multi-tenant authenticated views.
"""
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from apps.accounts.models import User
from apps.organizations.models import Organization, OrganizationMember
from apps.sales.models import Product, ProductCategory, UnitOfMeasure
from apps.inventory.models import (
    Warehouse,
    StorageZone,
    StorageLocation,
    StockItem,
    ReorderRule,
    RequisitionStatus,
    RequisitionPriority,
    PurchaseRequisition,
    PurchaseRequisitionLine,
)
from apps.inventory.services import (
    WarehouseHierarchyService,
    StockLevelService,
    ReplenishmentService,
    InventoryAnalyticsService,
)


class ReplenishmentAndDashboardIntegrationTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="vp.supplychain@enterpriseone.com",
            password="StrongPassword123!",
            first_name="Victor",
            last_name="Procurement",
        )
        self.org = Organization.objects.create(
            name="Apex Precision Motors",
            code="APX-MOT",
            slug="apex-precision-motors",
            currency="USD",
        )
        OrganizationMember.objects.create(
            organization=self.org,
            user=self.user,
            is_org_admin=True,
            status="ACTIVE",
        )

        self.other_org = Organization.objects.create(
            name="Rival Propulsion Systems",
            code="RIV-PROP",
            slug="rival-propulsion",
            currency="USD",
        )

        self.category = ProductCategory.objects.create(
            organization=self.org,
            name="Brushless DC Motors",
            code="MOT-BLDC",
        )
        self.uom = UnitOfMeasure.objects.create(
            organization=self.org,
            name="Motor",
            code="MTR",
            category="unit",
            is_base_unit=True,
            ratio_to_base=Decimal("1.0000"),
        )
        self.product = Product.objects.create(
            organization=self.org,
            category=self.category,
            uom=self.uom,
            name="Brushless DC Motor 48V 1000W",
            sku="MTR-BLDC-48V",
            cost_price=Decimal("120.00"),
            list_price=Decimal("249.00"),
        )

        prov = WarehouseHierarchyService.provision_standard_warehouse(
            organization=self.org,
            name="Motor Assembly Center",
            code="MAC-01",
            is_primary=True,
            manager=self.user,
        )
        self.warehouse = prov["warehouse"]
        self.location = prov["locations"][0]

    def test_automated_replenishment_evaluation(self):
        # Initial stock item: 15 on hand (below rule min of 25)
        stock_item = StockItem.objects.create(
            organization=self.org,
            product=self.product,
            warehouse=self.warehouse,
            location=self.location,
            quantity_on_hand=Decimal("15.00"),
            safety_stock=Decimal("10.00"),
            reorder_point=Decimal("25.00"),
            reorder_quantity=Decimal("60.00"),
        )

        # Establish reorder policy
        ReorderRule.objects.create(
            organization=self.org,
            warehouse=self.warehouse,
            product=self.product,
            min_quantity=Decimal("25.00"),
            max_quantity=Decimal("150.00"),
            reorder_quantity=Decimal("60.00"),
            auto_reorder_enabled=True,
        )

        # Trigger replenishment scan
        created_reqs = ReplenishmentService.evaluate_reorder_triggers(
            organization=self.org,
            warehouse=self.warehouse,
            requested_by=self.user,
        )

        self.assertEqual(len(created_reqs), 1)
        req = created_reqs[0]
        self.assertEqual(req.warehouse, self.warehouse)
        self.assertEqual(req.status, RequisitionStatus.DRAFT)
        self.assertEqual(req.total_items_count, 1)

        line = req.lines.first()
        self.assertEqual(line.product, self.product)
        self.assertEqual(line.quantity_requested, Decimal("60.00"))
        self.assertEqual(line.estimated_extended_cost, Decimal("7200.00"))

    def test_requisition_approval_and_cancellation(self):
        req = ReplenishmentService.create_requisition(
            organization=self.org,
            warehouse=self.warehouse,
            priority=RequisitionPriority.HIGH,
            lines_data=[
                {
                    "product": self.product,
                    "quantity_requested": Decimal("30.00"),
                    "estimated_unit_cost": Decimal("120.00"),
                }
            ],
            requested_by=self.user,
            justification="Assembly buffer replenishment",
        )
        self.assertEqual(req.status, RequisitionStatus.DRAFT)
        self.assertTrue(req.can_approve)

        # Approve
        approved = ReplenishmentService.approve_requisition(req, approved_by=self.user)
        self.assertEqual(approved.status, RequisitionStatus.APPROVED)
        self.assertEqual(approved.approved_by, self.user)
        self.assertIsNotNone(approved.approved_at)

        # Cannot approve again
        with self.assertRaises(ValidationError):
            ReplenishmentService.approve_requisition(approved, approved_by=self.user)

        # Cancel approved requisition
        cancelled = ReplenishmentService.cancel_requisition(approved, cancelled_by=self.user, reason="Design spec change")
        self.assertEqual(cancelled.status, RequisitionStatus.CANCELLED)
        self.assertIn("Design spec change", cancelled.justification)

    def test_inventory_analytics_kpis(self):
        # Create stock items
        StockItem.objects.create(
            organization=self.org,
            product=self.product,
            warehouse=self.warehouse,
            location=self.location,
            quantity_on_hand=Decimal("50.00"),
        )

        kpis = InventoryAnalyticsService.get_inventory_kpis(self.org)
        # 50 * 120.00 = 6000.00
        self.assertEqual(kpis["total_valuation"], Decimal("6000.00"))
        self.assertEqual(kpis["total_distinct_products"], 1)
        self.assertEqual(kpis["total_stock_items_count"], 1)
        self.assertEqual(kpis["stockout_count"], 0)
        self.assertEqual(kpis["total_warehouses"], 1)
        self.assertEqual(len(kpis["top_valued_holdings"]), 1)
        self.assertEqual(kpis["top_valued_holdings"][0]["sku"], "MTR-BLDC-48V")

    def test_dashboard_and_requisition_views(self):
        self.client.force_login(self.user)

        # Dashboard View
        res_dash = self.client.get(reverse("inventory:dashboard"))
        self.assertEqual(res_dash.status_code, 200)
        self.assertContains(res_dash, "Inventory & Logistics Command Center")

        # Replenishment Scan Trigger POST View
        res_scan = self.client.post(reverse("inventory:replenishment_scan"), {"warehouse_id": str(self.warehouse.id)})
        self.assertEqual(res_scan.status_code, 302)

        # Reorder Rules List View
        res_rules = self.client.get(reverse("inventory:reorder_rule_list"))
        self.assertEqual(res_rules.status_code, 200)

        # Requisitions List View
        res_reqs = self.client.get(reverse("inventory:requisition_list"))
        self.assertEqual(res_reqs.status_code, 200)
