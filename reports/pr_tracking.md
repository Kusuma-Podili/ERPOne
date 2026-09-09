# EnterpriseOne Pull Request Tracking Ledger

This document tracks all formal Pull Requests prepared, reviewed, and merged throughout the 17 development phases of EnterpriseOne.

---

## Pull Request Index

| PR # | Branch | Title | Phase | Status | Merged Date |
|---|---|---|---|---|---|
| #1 | `feature/phase1-scaffold` | Project Scaffold, Multi-Env Settings & Enterprise Middleware | Phase 1 | Merged | 2026-09-09 |
| #2 | `feature/phase1-custom-user-rbac` | Custom User Model, RBAC Engine & Audit Models | Phase 1 | Ready | 2026-09-09 |

---

## PR #1 — Project Scaffold, Multi-Env Settings & Enterprise Middleware

- **Branch**: `feature/phase1-scaffold` -> `development`
- **Phase**: Phase 1 — Foundation & Authentication
- **Status**: Merged

### Purpose
Establish the foundational infrastructure of EnterpriseOne: modular multi-environment settings (base, dev, prod, testing) with MySQL and automatic SQLite fallback, core enterprise middleware (security headers, session enforcement, thread-local audit tracking), system constants, and 11-role enterprise definitions.

---

## PR #2 — Custom User Model, RBAC Engine & Audit Models

- **Branch**: `feature/phase1-custom-user-rbac` -> `development`
- **Phase**: Phase 1 — Foundation & Authentication
- **Status**: Ready

### Purpose
Implement the core identity domain: custom `User` model using UUID primary keys and case-insensitive email, `UserProfile`, enterprise RBAC (`Role`, `Permission`, `UserRole`, `RolePermission`), audit logging (`LoginHistory`, `AccountLockoutAudit`), custom authentication backend (`EmailAuthBackend`), domain services (`AuthenticationService`, `LockoutService`, `TokenService`, `RBACService`), and the foundational `seed_roles` management command.

### Implementation Summary
- Created `User` model inheriting `AbstractBaseUser` and `PermissionsMixin` with UUID, lockout tracking, and failed login counters.
- Built custom `UserManager` with email normalization and superuser creation.
- Implemented `Role` supporting all 11 system roles with priority levels, and `Permission` entity.
- Implemented `UserRole` and `RolePermission` models with audit timestamps.
- Implemented `LoginHistory` and `AccountLockoutAudit` tracking models.
- Implemented `EmailAuthBackend` for case-insensitive authentication.
- Built `AuthenticationService`, `LockoutService`, `TokenService`, and `RBACService` domain layer.
- Added `@require_role` and `@require_permission` decorators and CBV mixins.
- Implemented `seed_roles` management command to initialize the 11 roles and default permissions.
- Generated and executed initial database migrations.

### Affected Modules
- `apps/accounts/`
- `enterpriseone/configuration/`

### Potential Risks & Mitigation
- *Risk*: Migration conflicts on custom user model.
  *Mitigation*: Custom user model was established before any user data was created and integrated into `AUTH_USER_MODEL` from day one.

### Review Checklist
- [x] Migrations generated and applied cleanly without warning.
- [x] `seed_roles` executes idempotently and maps default permissions.
- [x] Case-insensitive email lookup works as expected.
- [x] UUID primary keys used for all new models.
