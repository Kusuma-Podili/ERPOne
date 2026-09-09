# Organizational Hierarchy & Reporting Lines

## 1. Departmental Tree Hierarchy
Departments support recursive parent-child associations (`parent_department` self-referencing foreign key):
- Root departments (e.g. `Operations & Logistics`, `Executive Leadership`) have `parent_department = None`.
- Child departments (e.g. `Warehouse Management`, `Inventory Auditing`) reference their parent.
- Helper `full_department_path` outputs breadcrumb-style division paths (`Operations & Logistics > Warehouse Management > Inventory Auditing`).
- Visualized dynamically in the UI via `HierarchyService.build_department_tree()`.

---

## 2. Managerial Reporting Lines & Cycle Detection
Employees link to their direct supervisors through `OrganizationMember.reports_to`:
- Top executives report directly to the Board of Directors or Managing Director (`reports_to = None`).
- All other staff members reference their supervising manager.

### Cycle Detection Algorithm
To prevent circular reporting paradoxes (e.g., Alice reports to Bob, Bob reports to Charlie, and an administrator tries to assign Charlie to report to Alice):
`HierarchyService.validate_reporting_chain(member, new_manager)` traverses up the reporting chain of `new_manager` to ensure `member` is never encountered upstream.
If a loop is detected, a `ValidationError` is raised and rejected before database persistence.
