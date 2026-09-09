# Phase 1 Database Schema

## Entity Relationship Overview
The foundational identity and security subsystem is defined across 8 relational tables:

```text
User (1) <---> (1) UserProfile
User (1) <---> (N) UserRole (N) <---> (1) Role
Role (1) <---> (N) RolePermission (N) <---> (1) Permission
User (1) <---> (N) LoginHistory
User (1) <---> (N) AccountLockoutAudit
```

---

## Model Specifications

### 1. `accounts_user`
- `id` (UUID, Primary Key)
- `email` (VARCHAR(255), Unique, Indexed)
- `password` (VARCHAR(128))
- `first_name` (VARCHAR(150))
- `last_name` (VARCHAR(150))
- `phone` (VARCHAR(30))
- `job_title` (VARCHAR(100))
- `avatar` (VARCHAR(100), Nullable)
- `account_status` (VARCHAR(30), Indexed)
- `is_active` (BOOLEAN, Default True)
- `is_staff` (BOOLEAN, Default False)
- `is_superuser` (BOOLEAN, Default False)
- `is_verified` (BOOLEAN, Default False)
- `failed_login_attempts` (INT UNSIGNED, Default 0)
- `locked_until` (DATETIME, Nullable, Indexed)
- `last_password_change` (DATETIME)
- `force_password_change` (BOOLEAN)
- `created_at` (DATETIME, Indexed)
- `updated_at` (DATETIME)

### 2. `accounts_userprofile`
- `id` (UUID, Primary Key)
- `user_id` (UUID, One-to-One Foreign Key -> `accounts_user.id`)
- `timezone` (VARCHAR(50), Default 'UTC')
- `language` (VARCHAR(10), Default 'en')
- `theme` (VARCHAR(20), Default 'system')
- `bio` (TEXT)
- `department_name` (VARCHAR(100))
- `notification_email` (BOOLEAN)
- `notification_inapp` (BOOLEAN)

### 3. `accounts_role`
- `id` (UUID, Primary Key)
- `code` (VARCHAR(50), Unique, Indexed)
- `name` (VARCHAR(100))
- `description` (TEXT)
- `priority` (INT UNSIGNED, Default 10)
- `is_system_role` (BOOLEAN)

### 4. `accounts_permission`
- `id` (UUID, Primary Key)
- `code` (VARCHAR(100), Unique, Indexed)
- `name` (VARCHAR(150))
- `module` (VARCHAR(50), Indexed)
- `action` (VARCHAR(50))
- `description` (TEXT)

### 5. `accounts_userrole`
- `id` (UUID, Primary Key)
- `user_id` (UUID, Foreign Key -> `accounts_user.id`)
- `role_id` (UUID, Foreign Key -> `accounts_role.id`)
- `assigned_by_id` (UUID, Foreign Key -> `accounts_user.id`, Nullable)
- `assigned_at` (DATETIME)
- *Constraint*: `UNIQUE(user_id, role_id)`

### 6. `accounts_rolepermission`
- `id` (UUID, Primary Key)
- `role_id` (UUID, Foreign Key -> `accounts_role.id`)
- `permission_id` (UUID, Foreign Key -> `accounts_permission.id`)
- `granted_at` (DATETIME)
- *Constraint*: `UNIQUE(role_id, permission_id)`

### 7. `accounts_loginhistory`
- `id` (UUID, Primary Key)
- `user_id` (UUID, Foreign Key -> `accounts_user.id`, Nullable)
- `email_attempted` (VARCHAR(255), Indexed)
- `status` (VARCHAR(50))
- `ip_address` (CHAR(39), Nullable)
- `user_agent` (VARCHAR(500))
- `failure_reason` (VARCHAR(255))
- `timestamp` (DATETIME, Indexed)

### 8. `accounts_accountlockoutaudit`
- `id` (UUID, Primary Key)
- `user_id` (UUID, Foreign Key -> `accounts_user.id`)
- `locked_at` (DATETIME, Indexed)
- `unlocked_at` (DATETIME, Nullable)
- `duration_minutes` (INT UNSIGNED)
- `reason` (VARCHAR(255))
- `ip_address` (CHAR(39), Nullable)
- `unlocked_by_id` (UUID, Foreign Key -> `accounts_user.id`, Nullable)
