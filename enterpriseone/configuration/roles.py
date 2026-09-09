"""
EnterpriseOne Role Definitions and Hierarchy.
Defines the 11 enterprise roles, hierarchy levels, and default permission mappings.
"""

class SystemRole:
    SUPER_ADMIN = "SUPER_ADMIN"
    ORG_ADMIN = "ORG_ADMIN"
    MANAGER = "MANAGER"
    EMPLOYEE = "EMPLOYEE"
    SALES_USER = "SALES_USER"
    FINANCE_USER = "FINANCE_USER"
    HR_USER = "HR_USER"
    INVENTORY_USER = "INVENTORY_USER"
    PROCUREMENT_USER = "PROCUREMENT_USER"
    SUPPORT_USER = "SUPPORT_USER"
    ANALYST = "ANALYST"

    CHOICES = [
        (SUPER_ADMIN, "Super Administrator"),
        (ORG_ADMIN, "Organization Administrator"),
        (MANAGER, "Manager"),
        (EMPLOYEE, "Employee"),
        (SALES_USER, "Sales User"),
        (FINANCE_USER, "Finance User"),
        (HR_USER, "HR User"),
        (INVENTORY_USER, "Inventory User"),
        (PROCUREMENT_USER, "Procurement User"),
        (SUPPORT_USER, "Support User"),
        (ANALYST, "Analyst"),
    ]

# Priority level determines administrative hierarchy (higher integer = higher authority)
ROLE_METADATA = {
    SystemRole.SUPER_ADMIN: {
        "name": "Super Administrator",
        "description": "Full platform-level administrative privileges across all organizations and modules.",
        "priority": 100,
        "is_system_role": True,
    },
    SystemRole.ORG_ADMIN: {
        "name": "Organization Administrator",
        "description": "Full management authority within an organization including users, settings, and billing.",
        "priority": 90,
        "is_system_role": True,
    },
    SystemRole.MANAGER: {
        "name": "Manager",
        "description": "Operational manager with oversight of teams, workflows, approvals, and performance.",
        "priority": 70,
        "is_system_role": True,
    },
    SystemRole.EMPLOYEE: {
        "name": "Employee",
        "description": "Standard enterprise employee with self-service portal, profile, and task access.",
        "priority": 10,
        "is_system_role": True,
    },
    SystemRole.SALES_USER: {
        "name": "Sales User",
        "description": "Sales representative handling leads, deals, customers, quotations, and orders.",
        "priority": 30,
        "is_system_role": True,
    },
    SystemRole.FINANCE_USER: {
        "name": "Finance User",
        "description": "Financial officer managing general ledger, invoices, payments, and accounts.",
        "priority": 40,
        "is_system_role": True,
    },
    SystemRole.HR_USER: {
        "name": "HR User",
        "description": "Human resources administrator managing staff records, recruitment, leave, and payroll.",
        "priority": 40,
        "is_system_role": True,
    },
    SystemRole.INVENTORY_USER: {
        "name": "Inventory User",
        "description": "Warehouse and stock manager tracking inventory levels, movements, and audits.",
        "priority": 30,
        "is_system_role": True,
    },
    SystemRole.PROCUREMENT_USER: {
        "name": "Procurement User",
        "description": "Procurement specialist handling purchase requisitions, POs, and supplier management.",
        "priority": 30,
        "is_system_role": True,
    },
    SystemRole.SUPPORT_USER: {
        "name": "Support User",
        "description": "Support desk agent handling customer tickets, escalation, and SLA tracking.",
        "priority": 30,
        "is_system_role": True,
    },
    SystemRole.ANALYST: {
        "name": "Analyst",
        "description": "Business intelligence analyst with read-only reporting and data exploration access.",
        "priority": 25,
        "is_system_role": True,
    },
}

# Foundational Phase 1 Permissions
DEFAULT_FOUNDATIONAL_PERMISSIONS = [
    # Accounts & User Management
    {"code": "accounts.user.view", "name": "View Users", "module": "accounts", "action": "view"},
    {"code": "accounts.user.create", "name": "Create User", "module": "accounts", "action": "create"},
    {"code": "accounts.user.edit", "name": "Edit User", "module": "accounts", "action": "edit"},
    {"code": "accounts.user.delete", "name": "Delete User", "module": "accounts", "action": "delete"},
    {"code": "accounts.role.manage", "name": "Manage Roles & Permissions", "module": "accounts", "action": "manage"},
    {"code": "accounts.audit.view", "name": "View Audit & Login History", "module": "accounts", "action": "view"},
    {"code": "accounts.lockout.unlock", "name": "Unlock Locked Accounts", "module": "accounts", "action": "unlock"},
    
    # Dashboard & General
    {"code": "dashboard.view", "name": "Access Enterprise Dashboard", "module": "dashboard", "action": "view"},
    {"code": "settings.system.view", "name": "View System Configuration", "module": "settings", "action": "view"},
    {"code": "settings.system.edit", "name": "Edit System Configuration", "module": "settings", "action": "edit"},
]
