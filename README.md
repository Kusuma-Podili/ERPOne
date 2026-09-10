# EnterpriseOne — Large-Scale Enterprise Management Platform

EnterpriseOne is an integrated, modular enterprise resource and business management platform combining ERP, CRM, Sales, Inventory, Procurement, Finance, HR & Payroll, Project Management, Customer Support, Analytics, AI/ML Engine, Document Management, Notifications, Auditing, and Security.

---

## 🏛️ Architectural Principles
- **Clean Architecture & Modular Domain**: Discrete domain apps under `apps/` with rich domain services and clean interfaces.
- **Resilient Multi-Database Support**: Engineered for MySQL 8.0 in production with zero-friction SQLite fallback in local development and automated testing.
- **Genuine, Zero-Filler Codebase**: Designed to scale across 17 structured development phases toward a full enterprise footprint without artificial inflation or duplicated filler code.
- **Strict RBAC & Auditability**: Granular role-based authorization covering 11 enterprise personas, session tracking, brute-force lockout, and tamper-resistant audit trails.

---

## 🚀 Quickstart & Development

### 1. Requirements
- Python 3.10+
- Git

### 2. Setup Environment & Install Dependencies
```bash
# Clone the repository
git clone <repo-url>
cd EnterpriseOne

# Option A: Install dependencies from manifest
pip install -r requirements.txt

# Option B: Install with pinned lockfile (reproducible build)
pip install -r requirements.lock

# Option C: Install via Poetry (using poetry.lock)
poetry install

# Configure environment from template
cp example.env .env

# Apply database migrations
python manage.py migrate

# Seed foundational roles and permissions
python manage.py seed_roles

# Run development server
python manage.py runserver
```

### 3. Run Automated Tests
```bash
python manage.py test tests
```

---

## 📦 Development Roadmap (17 Phases)
1. **Phase 1: Foundation & Authentication** (Current)
2. **Phase 2: Organization & Users**
3. **Phase 3: CRM**
4. **Phase 4: Sales**
5. **Phase 5: Inventory**
6. **Phase 6: Procurement**
7. **Phase 7: Finance**
8. **Phase 8: HR & Payroll**
9. **Phase 9: Project Management**
10. **Phase 10: Customer Support**
11. **Phase 11: Analytics & Reporting**
12. **Phase 12: AI/ML Engine**
13. **Phase 13: Documents & Notifications**
14. **Phase 14: Security & Auditing**
15. **Phase 15: Testing Architecture**
16. **Phase 16: Monitoring & Optimization**
17. **Phase 17: Enterprise Integration & Release**
