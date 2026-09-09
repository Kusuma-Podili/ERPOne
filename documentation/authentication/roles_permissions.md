# Role-Based Access Control (RBAC) Architecture

## Enterprise Roles Specification
EnterpriseOne implements an 11-role operational hierarchy:

| Role Code | Name | Priority | Scope & Operational Authority |
|---|---|---|---|
| `SUPER_ADMIN` | Super Administrator | 100 | Platform-wide root authority across all tenants and modules |
| `ORG_ADMIN` | Organization Administrator | 90 | Organization-level authority over users, billing, and settings |
| `MANAGER` | Manager | 70 | Oversight of teams, workflows, and cross-departmental approvals |
| `EMPLOYEE` | Employee | 10 | General enterprise member with self-service profile and tasks |
| `SALES_USER` | Sales User | 30 | Access to CRM, leads, pipelines, quotations, and orders |
| `FINANCE_USER` | Finance User | 40 | Financial ledger, invoices, payments, accounts payable/receivable |
| `HR_USER` | HR User | 40 | Personnel management, recruitment, attendance, and payroll |
| `INVENTORY_USER` | Inventory User | 30 | Warehouse stock tracking, transfers, adjustments, and audits |
| `PROCUREMENT_USER` | Procurement User | 30 | Purchase orders, supplier evaluations, and requisitions |
| `SUPPORT_USER` | Support User | 30 | Help desk tickets, SLA workflows, customer satisfaction |
| `ANALYST` | Analyst | 25 | Read-only analytics, BI exploration, and exportable reports |

---

## Access Control Enforcement
1. **View Decorators**:
   - `@require_role(["SUPER_ADMIN", "ORG_ADMIN"])`
   - `@require_permission(["accounts.user.export"])`
2. **Class-Based View Mixins**:
   - `RoleRequiredMixin` with `required_roles = [...]`
   - `EnterprisePermissionRequiredMixin` with `required_permissions = [...]`
3. **Template Directives & Context**:
   - `user_display_role`
   - `is_super_admin`
   - `is_org_admin`
   - `is_manager`
   - `user_permissions` (set of active permission strings)
