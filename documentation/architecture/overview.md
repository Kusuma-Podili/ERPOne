# EnterpriseOne Architecture Overview

## Platform Summary
EnterpriseOne is a high-performance, modular enterprise business platform designed to integrate ERP, CRM, Sales, Inventory, Procurement, Finance, HR & Payroll, Project Management, Customer Support, Analytics, and AI/ML capabilities.

---

## Architectural Principles
1. **Clean Architecture & Separation of Concerns**:
   - Presentation: Responsive HTML5/CSS3/JavaScript components and Class-Based Views.
   - Domain Services Layer: Encapsulates pure business logic (`AuthenticationService`, `LockoutService`, `TokenService`, `RBACService`).
   - Domain Model: Normalised relational entities using UUID primary keys and database-level constraints.
   - Infrastructure & Configuration: 12-factor environment configuration via `python-dotenv`.
2. **Database Agility**:
   - Primary: MySQL 8.0 with InnoDB and strict transactional guarantees.
   - Development/Testing: Transparent auto-fallback to SQLite when MySQL is unreachable or during CI automated testing.
3. **Security-First Tenets**:
   - Case-insensitive email authentication.
   - Brute-force mitigation with configurable lockout thresholds.
   - Granular Role-Based Access Control (RBAC) across 11 enterprise personas.
   - Tamper-resistant HMAC-SHA256 tokens with short expiration windows.
   - Comprehensive audit logging for all authentication events.
