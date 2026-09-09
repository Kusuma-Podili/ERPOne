"""
Seed Enterprise Data Management Command.
Populates realistic Indian enterprise data in INR (₹) across Phase 1 to Phase 17:
- Organization (EnterpriseOne Global Ltd., INR, Asia/Kolkata)
- Roles & Foundational Permissions
- 1 Admin User (admin@enterpriseone.com / AdminPassword123!)
- 6 Employee Users (sales.exec, inventory.lead, finance.lead, hr.lead, devops.lead, support.agent / Password123!)
- 3 Customer Users (customer.tata, customer.reliance, customer.infosys / Password123!)
- Departments (Sales, Supply Chain, Corporate Finance, Human Resources, Engineering, Customer Support)
- CRM Accounts (TCS, Reliance, Infosys, Mahindra, HDFC Bank), Contacts, Leads, Pipeline Stages, Deals
- Sales UOM, Categories, Products, PriceBook, and Orders in ₹
- Inventory Warehouses (Mumbai, Bengaluru, Delhi), Zones, Locations, StockItems
- Finance Fiscal Year, Fiscal Periods, GL Accounts, Journal Entries in ₹
- HR & Payroll Shifts, Leave Policies, Leave Balances, Attendance Records in ₹
- Projects & Tasks assigned to Employees
- Support Categories, Teams, Tickets, Messages assigned to Customers and Support Agent
- Document Categories, Documents, Shares for Customers
"""
import decimal
from datetime import date, datetime, timedelta
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import User, AppRole, Role, UserRole
from apps.organizations.models import Organization, OrganizationMember, Department
from enterpriseone.configuration.roles import SystemRole


class Command(BaseCommand):
    help = "Seeds comprehensive Indian enterprise data in INR (INR) across all EnterpriseOne modules."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("=================================================="))
        self.stdout.write(self.style.NOTICE("  EnterpriseOne Indian Enterprise Data Seeding    "))
        self.stdout.write(self.style.NOTICE("=================================================="))

        # 1. Organization
        org, _ = Organization.objects.update_or_create(
            code="E1-GLOBAL",
            defaults={
                "name": "EnterpriseOne Global Ltd.",
                "registration_number": "CIN-U72200MH2026PTC123456",
                "tax_id": "27AAAAA0000A1Z5",
                "slug": "enterpriseone-global",
                "currency": "INR",
                "fiscal_year_start_month": 4,
                "is_active": True,
            },
        )
        self.stdout.write(self.style.SUCCESS(f"  [+] Organization: {org.name} ({org.currency})"))

        # 2. Roles and Permissions
        self.stdout.write("  [*] Seeding foundational roles and permissions...")
        call_command("seed_roles")

        # Helper to create/update user
        def get_or_create_user(email, password, first_name, last_name, role, is_staff=False, is_superuser=False):
            user, _ = User.objects.update_or_create(
                email=email.lower().strip(),
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "role": role,
                    "is_staff": is_staff,
                    "is_superuser": is_superuser,
                    "is_active": True,
                },
            )
            user.set_password(password)
            user.save()
            return user

        # 3. Admin User
        admin_user = get_or_create_user(
            email="admin@enterpriseone.com",
            password="AdminPassword123!",
            first_name="Vikram",
            last_name="Sharma",
            role=AppRole.ADMIN,
            is_staff=True,
            is_superuser=True,
        )
        OrganizationMember.objects.update_or_create(
            organization=org,
            user=admin_user,
            defaults={"is_org_admin": True, "status": "ACTIVE", "job_title": "Chief Executive & Enterprise Administrator"},
        )
        admin_role = Role.objects.filter(code=SystemRole.SUPER_ADMIN).first()
        if admin_role:
            UserRole.objects.get_or_create(user=admin_user, role=admin_role)
        self.stdout.write(self.style.SUCCESS(f"  [+] Admin User: {admin_user.email} (Password: AdminPassword123!)"))

        # 4. Departments
        departments_data = [
            ("DEP-SALES", "Sales & Business Development"),
            ("DEP-SCM", "Supply Chain & Fulfillment"),
            ("DEP-FIN", "Corporate Finance"),
            ("DEP-HR", "Human Resources"),
            ("DEP-ENG", "Engineering & Platform"),
            ("DEP-SUPP", "Customer Success & Support"),
        ]
        dept_map = {}
        for d_code, d_name in departments_data:
            d, _ = Department.objects.update_or_create(
                organization=org,
                code=d_code,
                defaults={"name": d_name, "is_active": True},
            )
            dept_map[d_code] = d

        # 5. Employee Users
        employees_data = [
            {
                "email": "sales.exec@enterpriseone.com",
                "first_name": "Rahul",
                "last_name": "Verma",
                "role_code": SystemRole.SALES_USER,
                "dept_code": "DEP-SALES",
                "pos_code": "POS-SALES-01",
                "pos_title": "Senior Enterprise Sales Executive",
            },
            {
                "email": "inventory.lead@enterpriseone.com",
                "first_name": "Pooja",
                "last_name": "Nair",
                "role_code": SystemRole.INVENTORY_USER,
                "dept_code": "DEP-SCM",
                "pos_code": "POS-INV-01",
                "pos_title": "Warehouse & Inventory Operations Lead",
            },
            {
                "email": "finance.lead@enterpriseone.com",
                "first_name": "Amit",
                "last_name": "Patel",
                "role_code": SystemRole.FINANCE_USER,
                "dept_code": "DEP-FIN",
                "pos_code": "POS-FIN-01",
                "pos_title": "Senior Financial Controller",
            },
            {
                "email": "hr.lead@enterpriseone.com",
                "first_name": "Sneha",
                "last_name": "Kulkarni",
                "role_code": SystemRole.HR_USER,
                "dept_code": "DEP-HR",
                "pos_code": "POS-HR-01",
                "pos_title": "Enterprise HR Manager",
            },
            {
                "email": "devops.lead@enterpriseone.com",
                "first_name": "Arjun",
                "last_name": "Rao",
                "role_code": SystemRole.ORG_ADMIN,
                "dept_code": "DEP-ENG",
                "pos_code": "POS-ENG-01",
                "pos_title": "Principal DevOps & Platform Engineer",
            },
            {
                "email": "support.agent@enterpriseone.com",
                "first_name": "Priya",
                "last_name": "Singh",
                "role_code": SystemRole.SUPPORT_USER,
                "dept_code": "DEP-SUPP",
                "pos_code": "POS-SUPP-01",
                "pos_title": "Senior Technical Support Specialist",
            },
        ]

        employee_users = {}
        for ed in employees_data:
            emp_user = get_or_create_user(
                email=ed["email"],
                password="Password123!",
                first_name=ed["first_name"],
                last_name=ed["last_name"],
                role=AppRole.EMPLOYEE,
            )
            dept = dept_map[ed["dept_code"]]
            OrganizationMember.objects.update_or_create(
                organization=org,
                user=emp_user,
                defaults={"department": dept, "job_title": ed["pos_title"], "status": "ACTIVE"},
            )
            role_obj = Role.objects.filter(code=ed["role_code"]).first()
            if role_obj:
                UserRole.objects.get_or_create(user=emp_user, role=role_obj)
            employee_users[ed["email"]] = emp_user

        self.stdout.write(self.style.SUCCESS(f"  [+] {len(employee_users)} Employee Users Created (Password: Password123!)"))

        # 6. Customer Users
        customers_data = [
            {
                "email": "customer.tata@enterpriseone.com",
                "first_name": "Ratan",
                "last_name": "Tata",
                "company": "Tata Consultancy Services",
                "acc_num": "ACC-TCS-001",
                "industry": "Information Technology",
                "phone": "+91 22 6778 9999",
                "city": "Mumbai",
                "state": "Maharashtra",
            },
            {
                "email": "customer.reliance@enterpriseone.com",
                "first_name": "Mukesh",
                "last_name": "Ambani",
                "company": "Reliance Industries Ltd",
                "acc_num": "ACC-RIL-002",
                "industry": "Energy & Telecom",
                "phone": "+91 22 3555 5000",
                "city": "Mumbai",
                "state": "Maharashtra",
            },
            {
                "email": "customer.infosys@enterpriseone.com",
                "first_name": "Narayan",
                "last_name": "Murthy",
                "company": "Infosys Technologies",
                "acc_num": "ACC-INF-003",
                "industry": "IT & Cloud Services",
                "phone": "+91 80 2852 0261",
                "city": "Bengaluru",
                "state": "Karnataka",
            },
        ]

        customer_users = {}
        for cd in customers_data:
            cust_user = get_or_create_user(
                email=cd["email"],
                password="Password123!",
                first_name=cd["first_name"],
                last_name=cd["last_name"],
                role=AppRole.CUSTOMER,
            )
            cust_role = Role.objects.filter(code=SystemRole.CUSTOMER).first()
            if cust_role:
                UserRole.objects.get_or_create(user=cust_user, role=cust_role)
            customer_users[cd["email"]] = cust_user

        self.stdout.write(self.style.SUCCESS(f"  [+] {len(customer_users)} Customer Users Created (Password: Password123!)"))

        # 7. CRM Module Seeding
        from apps.crm.models import Account, Contact, Lead, Deal, PipelineStage

        # CRM Accounts
        crm_accounts = {}
        for cd in customers_data:
            acc, _ = Account.objects.update_or_create(
                organization=org,
                name=cd["company"],
                defaults={
                    "account_number": cd["acc_num"],
                    "industry": cd["industry"],
                    "phone": cd["phone"],
                    "billing_city": cd["city"],
                    "billing_state": cd["state"],
                    "billing_country": "India",
                    "status": "ACTIVE",
                },
            )
            crm_accounts[cd["email"]] = acc

        # Additional Accounts
        for extra_name, acc_n, ind, city, state in [
            ("Mahindra & Mahindra Ltd", "ACC-MM-004", "Automotive & Manufacturing", "Pune", "Maharashtra"),
            ("HDFC Bank Ltd", "ACC-HDFC-005", "Banking & Financial Services", "Mumbai", "Maharashtra"),
        ]:
            Account.objects.update_or_create(
                organization=org,
                name=extra_name,
                defaults={
                    "account_number": acc_n,
                    "industry": ind,
                    "billing_city": city,
                    "billing_state": state,
                    "billing_country": "India",
                    "status": "ACTIVE",
                },
            )

        # CRM Contacts linked to Customer Users
        customer_contacts = {}
        for cd in customers_data:
            cust_user = customer_users[cd["email"]]
            acc = crm_accounts[cd["email"]]
            contact, _ = Contact.objects.update_or_create(
                organization=org,
                email=cd["email"],
                defaults={
                    "account": acc,
                    "first_name": cd["first_name"],
                    "last_name": cd["last_name"],
                    "phone": cd["phone"],
                    "user": cust_user,
                    "is_primary_contact": True,
                },
            )
            customer_contacts[cd["email"]] = contact

        # Pipeline Stages
        stages_data = [
            ("Prospecting", "PROSPECTING", 1, 10),
            ("Qualification", "QUALIFICATION", 2, 25),
            ("Proposal / Quote", "PROPOSAL", 3, 50),
            ("Negotiation", "NEGOTIATION", 4, 80),
            ("Closed Won", "CLOSED_WON", 5, 100),
            ("Closed Lost", "CLOSED_LOST", 6, 0),
        ]
        stages_map = {}
        for name, code, order, prob in stages_data:
            stage, _ = PipelineStage.objects.update_or_create(
                organization=org,
                code=code,
                defaults={"name": name, "order": order, "default_probability": prob},
            )
            stages_map[code] = stage

        # CRM Leads in INR
        leads_data = [
            ("Cloud Migration & ERP 2.0", "Anand", "Mahindra", "Mahindra Motors", "anand@mahindra.example.com", 4500000),
            ("Retail Supply Chain Digitization", "Isha", "Ambani", "Reliance Retail", "isha@reliance.example.com", 6500000),
            ("Enterprise AI Copilot Rollout", "Rishad", "Premji", "Wipro Technologies", "rishad@wipro.example.com", 3200000),
            ("Core Banking Integration Gateway", "Uday", "Kotak", "Kotak Mahindra Bank", "uday@kotak.example.com", 2850000),
            ("Automated Payroll & Attendance", "Gopal", "Vittal", "Bharti Airtel", "gopal@airtel.example.com", 1800000),
        ]
        for title, fn, ln, comp, em, val in leads_data:
            Lead.objects.update_or_create(
                organization=org,
                email=em,
                defaults={
                    "first_name": fn,
                    "last_name": ln,
                    "company_name": comp,
                    "job_title": title,
                    "estimated_value": decimal.Decimal(val),
                    "status": "NEW",
                },
            )

        # CRM Deals in INR
        deals_data = [
            ("TCS Global ERP Modernization", "DEAL-2026-001", crm_accounts["customer.tata@enterpriseone.com"], stages_map["PROPOSAL"], 8500000),
            ("Jio Platform 5G OSS Integration", "DEAL-2026-002", crm_accounts["customer.reliance@enterpriseone.com"], stages_map["NEGOTIATION"], 12000000),
            ("Infosys Finacle Cloud Add-on", "DEAL-2026-003", crm_accounts["customer.infosys@enterpriseone.com"], stages_map["CLOSED_WON"], 4800000),
        ]
        for name, dnum, acc, stage, amt in deals_data:
            Deal.objects.update_or_create(
                organization=org,
                deal_number=dnum,
                defaults={
                    "account": acc,
                    "name": name,
                    "stage": stage,
                    "amount": decimal.Decimal(amt),
                    "expected_close_date": date.today() + timedelta(days=60),
                },
            )
        self.stdout.write(self.style.SUCCESS("  [+] CRM Accounts, Contacts, Leads, Stages, and Deals seeded."))

        # 8. Sales Module Seeding
        from apps.sales.models import (
            UnitOfMeasure, ProductCategory, Product, PriceBook, PriceBookEntry,
            SalesOrder, OrderLineItem
        )

        uom_unit, _ = UnitOfMeasure.objects.update_or_create(
            organization=org, code="EA", defaults={"name": "Each", "category": "unit", "is_base_unit": True}
        )
        uom_year, _ = UnitOfMeasure.objects.update_or_create(
            organization=org, code="YR", defaults={"name": "Yearly License", "category": "time", "is_base_unit": False}
        )

        cat_software, _ = ProductCategory.objects.update_or_create(
            organization=org, code="CAT-SW", defaults={"name": "Enterprise Cloud Software"}
        )
        cat_support, _ = ProductCategory.objects.update_or_create(
            organization=org, code="CAT-SUP", defaults={"name": "Enterprise Support & SLA"}
        )

        products_data = [
            ("EnterpriseOne Cloud Suite - Annual Enterprise", "PROD-E1-ENT", uom_year, cat_software, 250000, 80000),
            ("Financial Accounting & GST Ledger Module", "PROD-FIN-GST", uom_year, cat_software, 120000, 35000),
            ("Automated Payroll & Compliance Pack", "PROD-PAY-PRO", uom_year, cat_software, 85000, 25000),
            ("AI Automation & Predictive Forecasting Engine", "PROD-AI-AUTO", uom_year, cat_software, 95000, 30000),
            ("24/7 Dedicated Platinum SLA Support", "PROD-SLA-PLAT", uom_year, cat_support, 60000, 15000),
        ]
        products_map = {}
        for name, sku, uom, cat, list_p, cost_p in products_data:
            prod, _ = Product.objects.update_or_create(
                organization=org,
                sku=sku,
                defaults={
                    "name": name,
                    "uom": uom,
                    "category": cat,
                    "list_price": decimal.Decimal(list_p),
                    "cost_price": decimal.Decimal(cost_p),
                    "currency": "INR",
                    "is_active": True,
                },
            )
            products_map[sku] = prod

        price_book, _ = PriceBook.objects.update_or_create(
            organization=org,
            code="PB-INR-2026",
            defaults={"name": "Standard Enterprise India INR Pricebook", "currency": "INR", "is_active": True},
        )
        for sku, prod in products_map.items():
            PriceBookEntry.objects.update_or_create(
                organization=org,
                price_book=price_book,
                product=prod,
                defaults={"unit_price": prod.list_price, "is_active": True},
            )

        # Sales Orders for Customers in INR
        orders_spec = [
            {
                "num": "ORD-2026-001",
                "customer_email": "customer.tata@enterpriseone.com",
                "status": "fulfilled",
                "items": [("PROD-E1-ENT", 1), ("PROD-SLA-PLAT", 1)],
            },
            {
                "num": "ORD-2026-002",
                "customer_email": "customer.reliance@enterpriseone.com",
                "status": "confirmed",
                "items": [("PROD-E1-ENT", 1), ("PROD-FIN-GST", 1), ("PROD-AI-AUTO", 1)],
            },
            {
                "num": "ORD-2026-003",
                "customer_email": "customer.infosys@enterpriseone.com",
                "status": "processing",
                "items": [("PROD-E1-ENT", 1), ("PROD-PAY-PRO", 1)],
            },
        ]

        for ospec in orders_spec:
            acc = crm_accounts[ospec["customer_email"]]
            cont = customer_contacts[ospec["customer_email"]]
            order, _ = SalesOrder.objects.update_or_create(
                organization=org,
                order_number=ospec["num"],
                defaults={
                    "account": acc,
                    "contact": cont,
                    "status": ospec["status"],
                    "currency": "INR",
                    "order_date": date.today(),
                },
            )
            total_amt = decimal.Decimal("0.00")
            for idx, (sku, qty) in enumerate(ospec["items"], start=1):
                p = products_map[sku]
                line_tot = p.list_price * qty
                total_amt += line_tot
                OrderLineItem.objects.update_or_create(
                    organization=org,
                    order=order,
                    line_number=idx,
                    defaults={
                        "product": p,
                        "quantity_ordered": decimal.Decimal(qty),
                        "unit_price": p.list_price,
                        "subtotal": line_tot,
                        "total_price": line_tot,
                    },
                )
            order.subtotal_amount = total_amt
            order.tax_amount = total_amt * decimal.Decimal("0.18")  # 18% GST
            order.grand_total = total_amt + order.tax_amount
            order.save()

        self.stdout.write(self.style.SUCCESS("  [+] Sales Products, Pricebook, and Customer Orders in INR seeded."))

        # 9. Inventory Module Seeding
        from apps.inventory.models import Warehouse, StorageZone, StorageLocation, StockItem

        warehouses_data = [
            ("Bhiwandi Central Fulfillment Hub", "WH-MUM-01", "Bhiwandi, Mumbai", "Maharashtra"),
            ("Electronic City Logistics Depot", "WH-BLR-01", "Electronic City, Bengaluru", "Karnataka"),
            ("Gurugram Tech Distribution Hub", "WH-DEL-01", "Udyog Vihar, Gurugram", "Haryana"),
        ]
        warehouses_map = {}
        for name, code, addr, state in warehouses_data:
            wh, _ = Warehouse.objects.update_or_create(
                organization=org,
                code=code,
                defaults={"name": name, "city": addr, "state_province": state, "country": "India", "is_active": True},
            )
            warehouses_map[code] = wh

            zone, _ = StorageZone.objects.update_or_create(
                organization=org, warehouse=wh, code=f"ZN-{code}", defaults={"name": f"High Density Zone {code}", "is_active": True}
            )
            StorageLocation.objects.update_or_create(
                organization=org, warehouse=wh, zone=zone, code=f"LOC-{code}-A1", defaults={"is_active": True}
            )

        # Stock items
        for prod in products_map.values():
            wh = warehouses_map["WH-MUM-01"]
            StockItem.objects.update_or_create(
                organization=org,
                product=prod,
                warehouse=wh,
                defaults={
                    "quantity_on_hand": decimal.Decimal("500.00"),
                    "quantity_reserved": decimal.Decimal("25.00"),
                    "reorder_point": decimal.Decimal("50.00"),
                },
            )
        self.stdout.write(self.style.SUCCESS("  [+] Inventory Warehouses, Locations, and StockItems seeded."))

        # 10. Finance Module Seeding
        from apps.finance.models import FiscalYear, FiscalPeriod, GLAccount, JournalEntry, JournalEntryLine

        fy, _ = FiscalYear.objects.update_or_create(
            organization=org,
            code="FY2026",
            defaults={
                "name": "FY 2026-27",
                "start_date": date(2026, 4, 1),
                "end_date": date(2027, 3, 31),
                "is_closed": False,
            },
        )

        fp_q2, _ = FiscalPeriod.objects.update_or_create(
            organization=org,
            fiscal_year=fy,
            period_number=2,
            defaults={
                "name": "FY26-Q2 (July - Sept 2026)",
                "start_date": date(2026, 7, 1),
                "end_date": date(2026, 9, 30),
                "is_closed": False,
            },
        )

        gl_accounts_data = [
            ("1010", "HDFC Bank Operating Account", "asset", "bank", "debit"),
            ("1020", "State Bank of India Corporate Account", "asset", "bank", "debit"),
            ("1100", "Accounts Receivable - Domestic Customers", "asset", "receivable", "debit"),
            ("2000", "Accounts Payable - Vendors & Suppliers", "liability", "payable", "credit"),
            ("2100", "GST & Statutory Withholding Taxes Payable", "liability", "tax_payable", "credit"),
            ("3000", "Retained Earnings & Share Capital", "equity", "retained_earnings", "credit"),
            ("4000", "Enterprise Cloud Software License Revenue", "revenue", "operating_revenue", "credit"),
            ("5000", "Cloud Datacenter Infrastructure Costs", "expense", "cogs", "debit"),
            ("6000", "Employee Compensation & Salaries", "expense", "payroll_expense", "debit"),
        ]
        gl_map = {}
        for code, name, cat, sub, nb in gl_accounts_data:
            gl, _ = GLAccount.objects.update_or_create(
                organization=org,
                code=code,
                defaults={
                    "name": name,
                    "category": cat,
                    "subtype": sub,
                    "normal_balance": nb,
                    "currency": "INR",
                    "is_active": True,
                },
            )
            gl_map[code] = gl

        # Balanced Journal Entry in INR
        je_amt = decimal.Decimal("1500000.00")
        je, _ = JournalEntry.objects.update_or_create(
            organization=org,
            entry_number="JE-2026-001",
            defaults={
                "fiscal_period": fp_q2,
                "entry_date": date.today(),
                "posting_date": date.today(),
                "narration": "Subscription revenue recognition for enterprise cloud customers",
                "status": "posted",
                "total_debit": je_amt,
                "total_credit": je_amt,
                "is_balanced": True,
            },
        )
        JournalEntryLine.objects.update_or_create(
            journal_entry=je,
            line_number=1,
            defaults={"account": gl_map["1010"], "debit": je_amt, "credit": decimal.Decimal("0.00"), "narration": "Bank receipt from client licensing"},
        )
        JournalEntryLine.objects.update_or_create(
            journal_entry=je,
            line_number=2,
            defaults={"account": gl_map["4000"], "debit": decimal.Decimal("0.00"), "credit": je_amt, "narration": "Revenue recognized for licensing"},
        )
        self.stdout.write(self.style.SUCCESS("  [+] Finance Fiscal Year, GL Accounts, and Balanced Journal Entry in INR seeded."))

        # 11. HR & Payroll Module Seeding
        from apps.hr.models import (
            JobPosition, Employee, Shift, LeavePolicy, LeaveBalance, AttendanceRecord
        )

        shift, _ = Shift.objects.update_or_create(
            organization=org,
            code="SHIFT-GEN",
            defaults={
                "name": "General Day Shift (09:30 - 18:30 IST)",
                "start_time": datetime.strptime("09:30", "%H:%M").time(),
                "end_time": datetime.strptime("18:30", "%H:%M").time(),
            },
        )

        pol_pl, _ = LeavePolicy.objects.update_or_create(
            organization=org,
            code="POL-PL",
            defaults={"name": "Privilege / Earned Leave (PL)", "annual_entitlement": 18, "is_active": True},
        )
        pol_cl, _ = LeavePolicy.objects.update_or_create(
            organization=org,
            code="POL-CL",
            defaults={"name": "Casual & Sick Leave (CL/SL)", "annual_entitlement": 12, "is_active": True},
        )

        for idx, ed in enumerate(employees_data, start=1):
            emp_user = employee_users[ed["email"]]
            dept = dept_map[ed["dept_code"]]
            pos, _ = JobPosition.objects.update_or_create(
                organization=org,
                code=ed["pos_code"],
                defaults={"title": ed["pos_title"], "department": dept, "is_active": True},
            )
            hr_emp, _ = Employee.objects.update_or_create(
                organization=org,
                employee_number=f"EMP-2026-{idx:03d}",
                defaults={
                    "user": emp_user,
                    "first_name": ed["first_name"],
                    "last_name": ed["last_name"],
                    "work_email": ed["email"],
                    "department": dept,
                    "position": pos,
                    "employment_status": "active",
                    "employment_type": "full_time",
                    "hire_date": date(2025, 4, 1),
                },
            )

            # Leave balances
            LeaveBalance.objects.update_or_create(
                employee=hr_emp,
                policy=pol_pl,
                year=2026,
                defaults={"opening_balance": 18, "accrued": 9, "used": 2, "adjustment": 0},
            )
            LeaveBalance.objects.update_or_create(
                employee=hr_emp,
                policy=pol_cl,
                year=2026,
                defaults={"opening_balance": 12, "accrued": 6, "used": 1, "adjustment": 0},
            )

            # Attendance records for recent days
            for d_offset in range(5):
                rec_date = date.today() - timedelta(days=d_offset)
                if rec_date.weekday() < 5:  # Monday to Friday
                    AttendanceRecord.objects.update_or_create(
                        employee=hr_emp,
                        work_date=rec_date,
                        defaults={
                            "shift": shift,
                            "status": "present",
                            "worked_minutes": 540,
                            "notes": "Punched in via Biometric & Mobile App",
                        },
                    )
        self.stdout.write(self.style.SUCCESS("  [+] HR Positions, Employees, Leaves, and Attendance seeded."))

        # 12. Projects & Tasks
        from apps.projects.models import Project, ProjectTask

        project, _ = Project.objects.update_or_create(
            organization=org,
            code="PRJ-E1-01",
            defaults={
                "name": "EnterpriseOne NextGen Digital Platform Transformation",
                "description": "Multi-tenant cloud ERP release and integration milestone",
                "status": "active",
                "project_manager": admin_user,
                "created_by": admin_user,
            },
        )

        tasks_data = [
            ("Complete Q3 Financial Audits and GST Filing", employee_users["finance.lead@enterpriseone.com"], "in_progress", "high"),
            ("Review Bhiwandi Warehouse Stock Replenishment", employee_users["inventory.lead@enterpriseone.com"], "in_progress", "normal"),
            ("Negotiate Enterprise SLA Expansion with Reliance Jio", employee_users["sales.exec@enterpriseone.com"], "in_progress", "urgent"),
            ("Run Employee Annual Performance & Appraisal Cycles", employee_users["hr.lead@enterpriseone.com"], "todo", "normal"),
            ("Deploy High-Availability Kubernetes Cluster in Mumbai Datacenter", employee_users["devops.lead@enterpriseone.com"], "in_progress", "critical"),
            ("Resolve Tata Consultancy Services API Latency Ticket", employee_users["support.agent@enterpriseone.com"], "in_progress", "high"),
        ]
        for idx, (title, assignee, status, prio) in enumerate(tasks_data, start=1):
            ProjectTask.objects.update_or_create(
                project=project,
                task_key=f"E1-TSK-{idx:03d}",
                defaults={
                    "title": title,
                    "assignee": assignee,
                    "status": status,
                    "priority": prio,
                    "due_date": date.today() + timedelta(days=14),
                },
            )
        self.stdout.write(self.style.SUCCESS("  [+] Projects and Tasks assigned to Employees seeded."))

        # 13. Support Tickets Module
        from apps.support.models import SupportCategory, SupportTeam, SupportTicket, TicketMessage

        supp_cat, _ = SupportCategory.objects.update_or_create(
            organization=org,
            code="SUPP-TECH",
            defaults={"name": "Enterprise Technical Support"},
        )
        supp_team, _ = SupportTeam.objects.update_or_create(
            organization=org,
            code="TEAM-OPS",
            defaults={"name": "Tier-2 Operations Desk"},
        )

        support_agent = employee_users["support.agent@enterpriseone.com"]
        tickets_spec = [
            {
                "num": "TCK-2026-001",
                "cust_email": "customer.tata@enterpriseone.com",
                "subject": "API Webhook Latency in Mumbai Cloud Region",
                "desc": "We have observed periodic response spikes on batch sync API. Requesting telemetry review.",
                "priority": "high",
                "status": "open",
            },
            {
                "num": "TCK-2026-002",
                "cust_email": "customer.reliance@enterpriseone.com",
                "subject": "GST Invoice E-Way Bill Reconciliation Assistance",
                "desc": "Need verification for automated e-Way bill JSON export for interstate shipments.",
                "priority": "normal",
                "status": "in_progress",
            },
            {
                "num": "TCK-2026-003",
                "cust_email": "customer.infosys@enterpriseone.com",
                "subject": "SSO SAML Identity Provider Configuration",
                "desc": "Requesting metadata exchange for Okta SAML 2.0 integration on enterprise portal.",
                "priority": "normal",
                "status": "waiting",
            },
        ]

        for tspec in tickets_spec:
            cust_u = customer_users[tspec["cust_email"]]
            acc = crm_accounts[tspec["cust_email"]]
            tck, _ = SupportTicket.objects.update_or_create(
                organization=org,
                number=tspec["num"],
                defaults={
                    "subject": tspec["subject"],
                    "description": tspec["desc"],
                    "customer": acc,
                    "requester": cust_u,
                    "assignee": support_agent,
                    "category": supp_cat,
                    "team": supp_team,
                    "status": tspec["status"],
                    "priority": tspec["priority"],
                },
            )
            TicketMessage.objects.get_or_create(
                ticket=tck,
                author=cust_u,
                defaults={"body": tspec["desc"], "is_internal": False},
            )
            TicketMessage.objects.get_or_create(
                ticket=tck,
                author=support_agent,
                defaults={"body": "Hello! Thank you for contacting Enterprise Support. Our team is actively investigating this.", "is_internal": False},
            )

        self.stdout.write(self.style.SUCCESS("  [+] Support Tickets & Messages for Customers and Support Agent seeded."))

        # 14. Documents Module
        from apps.documents.models import DocumentCategory, Document, DocumentShare

        doc_cat, _ = DocumentCategory.objects.update_or_create(
            organization=org,
            code="DOC-LEGAL",
            defaults={"name": "Enterprise Legal & Master Agreements"},
        )

        docs_spec = [
            ("Enterprise Master Services Agreement - TCS", "DOC-TCS-MSA", "customer.tata@enterpriseone.com"),
            ("Reliance Industries Annual Cloud License Agreement", "DOC-RIL-LIC", "customer.reliance@enterpriseone.com"),
            ("Infosys Implementation Statement of Work", "DOC-INF-SOW", "customer.infosys@enterpriseone.com"),
            ("EnterpriseOne Cloud Security & ISO 27001 Whitepaper", "DOC-SEC-ISO", None),
        ]

        for title, doc_num, target_cust_email in docs_spec:
            doc, _ = Document.objects.update_or_create(
                organization=org,
                document_number=doc_num,
                defaults={
                    "title": title,
                    "category": doc_cat,
                    "owner": admin_user,
                    "visibility": "shared",
                    "status": "approved",
                },
            )
            if target_cust_email:
                DocumentShare.objects.get_or_create(
                    document=doc,
                    recipient_email=target_cust_email,
                    defaults={"shared_by": admin_user, "can_download": True},
                )

        self.stdout.write(self.style.SUCCESS("  [+] Documents and Customer Shares seeded."))

        self.stdout.write(self.style.NOTICE("=================================================="))
        self.stdout.write(self.style.SUCCESS("  EnterpriseOne Data Seeding Completed 100% OK!   "))
        self.stdout.write(self.style.NOTICE("=================================================="))
