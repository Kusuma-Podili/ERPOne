"""
Seed Roles & Permissions Management Command.
Populates the 11 enterprise roles and foundational system permissions.
"""
from django.core.management.base import BaseCommand
from apps.accounts.models import Role, Permission, RolePermission
from enterpriseone.configuration.roles import (
    SystemRole,
    ROLE_METADATA,
    DEFAULT_FOUNDATIONAL_PERMISSIONS,
)


class Command(BaseCommand):
    help = "Seeds foundational enterprise roles, permissions, and default role-permission mappings."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding EnterpriseOne foundational roles and permissions..."))

        # 1. Seed Permissions
        created_perms = 0
        perm_map = {}
        for perm_def in DEFAULT_FOUNDATIONAL_PERMISSIONS:
            perm, created = Permission.objects.update_or_create(
                code=perm_def["code"],
                defaults={
                    "name": perm_def["name"],
                    "module": perm_def["module"],
                    "action": perm_def["action"],
                    "description": f"Permission to {perm_def['action']} {perm_def['module']}",
                },
            )
            perm_map[perm.code] = perm
            if created:
                created_perms += 1

        self.stdout.write(self.style.SUCCESS(f"  [+] Permissions processed ({created_perms} new, {len(perm_map)} total)"))

        # 2. Seed Roles
        created_roles = 0
        role_map = {}
        for role_code, meta in ROLE_METADATA.items():
            role, created = Role.objects.update_or_create(
                code=role_code,
                defaults={
                    "name": meta["name"],
                    "description": meta["description"],
                    "priority": meta["priority"],
                    "is_system_role": meta["is_system_role"],
                },
            )
            role_map[role.code] = role
            if created:
                created_roles += 1

        self.stdout.write(self.style.SUCCESS(f"  [+] Roles processed ({created_roles} new, {len(role_map)} total)"))

        # 3. Map Default Foundational Permissions
        # Super Admin gets all permissions
        super_admin_role = role_map.get(SystemRole.SUPER_ADMIN)
        if super_admin_role:
            for perm in perm_map.values():
                RolePermission.objects.get_or_create(role=super_admin_role, permission=perm)

        # Org Admin gets user management and dashboard
        org_admin_role = role_map.get(SystemRole.ORG_ADMIN)
        if org_admin_role:
            for code in ["accounts.user.view", "accounts.user.create", "accounts.user.edit", "accounts.audit.view", "accounts.lockout.unlock", "dashboard.view"]:
                if code in perm_map:
                    RolePermission.objects.get_or_create(role=org_admin_role, permission=perm_map[code])

        # Manager gets dashboard and view users
        manager_role = role_map.get(SystemRole.MANAGER)
        if manager_role:
            for code in ["accounts.user.view", "dashboard.view"]:
                if code in perm_map:
                    RolePermission.objects.get_or_create(role=manager_role, permission=perm_map[code])

        # Standard roles get dashboard
        for code, role in role_map.items():
            if code not in [SystemRole.SUPER_ADMIN, SystemRole.ORG_ADMIN, SystemRole.MANAGER]:
                if "dashboard.view" in perm_map:
                    RolePermission.objects.get_or_create(role=role, permission=perm_map["dashboard.view"])

        self.stdout.write(self.style.SUCCESS("EnterpriseOne roles and permissions seeding completed successfully!"))
