"""
Integration tests for Finance & General Ledger Engine (Milestone 7.1).
Covers COA provisioning, 12-period generation, double-entry balancing,
posting, balance updates, period locks, reversals, and views.
"""
from datetime import date
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.test import TestCase, Client
from django.urls import reverse

from apps.accounts.models import User
from apps.organizations.models import Organization, OrganizationMember
from apps.finance.models import (
    FiscalYear,
    FiscalPeriod,
    AccountCategory,
    AccountSubtype,
    NormalBalance,
    GLAccount,
    JournalStatus,
    SourceDocumentType,
    JournalEntry,
    JournalEntryLine,
)
from apps.finance.services import (
    FiscalPeriodService,
    GLAccountService,
    JournalEntryService,
)


class GeneralLedgerEngineIntegrationTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Zenith Enterprise Systems",
            code="ZENITH-GL",
            tax_id="US-112233",
        )
        self.user = User.objects.create_user(
            email="controller@zenith.com",
            password="StrongPassword123!",
            first_name="Eleanor",
            last_name="Vance",
        )
        OrganizationMember.objects.create(
            organization=self.org,
            user=self.user,
            is_org_admin=True,
            status="ACTIVE",
        )
        self.client = Client()
        self.client.force_login(self.user)
        session = self.client.session
        session["active_organization_id"] = str(self.org.id)
        session.save()

    def test_standard_coa_provisioning(self):
        # Auto-provision standard chart of accounts
        count = GLAccountService.provision_standard_chart_of_accounts(self.org)
        self.assertGreater(count, 15)

        # Verify key accounts exist
        cash = GLAccount.objects.get(organization=self.org, code="1010")
        self.assertEqual(cash.category, AccountCategory.ASSET)
        self.assertEqual(cash.normal_balance, NormalBalance.DEBIT)
        self.assertTrue(cash.allow_direct_posting)

        ap = GLAccount.objects.get(organization=self.org, code="2010")
        self.assertEqual(ap.category, AccountCategory.LIABILITY)
        self.assertEqual(ap.normal_balance, NormalBalance.CREDIT)
        self.assertTrue(ap.is_reconciliation)

        # Calling again should be idempotent
        second_call = GLAccountService.provision_standard_chart_of_accounts(self.org)
        self.assertEqual(second_call, 0)

    def test_fiscal_year_and_periods_generation(self):
        fy = FiscalPeriodService.create_fiscal_year(
            organization=self.org,
            name="Fiscal Year 2026",
            code="FY2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            auto_create_monthly_periods=True,
        )
        self.assertEqual(fy.periods.count(), 12)
        p1 = fy.periods.get(period_number=1)
        self.assertEqual(p1.start_date, date(2026, 1, 1))
        self.assertEqual(p1.end_date, date(2026, 1, 31))
        self.assertFalse(p1.is_closed)

    def test_journal_entry_posting_and_balance_update_lifecycle(self):
        GLAccountService.provision_standard_chart_of_accounts(self.org)
        fy = FiscalPeriodService.create_fiscal_year(
            organization=self.org,
            name="Fiscal Year 2026",
            code="FY2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        p1 = fy.periods.get(period_number=1)

        cash = GLAccount.objects.get(organization=self.org, code="1010")
        revenue = GLAccount.objects.get(organization=self.org, code="4010")

        # Create balanced journal entry: Debit Cash 1,200, Credit Sales 1,200
        lines_data = [
            {"account": cash, "debit": Decimal("1200.00"), "credit": Decimal("0.00"), "narration": "Direct invoice collection"},
            {"account": revenue, "debit": Decimal("0.00"), "credit": Decimal("1200.00"), "narration": "Consulting service sale"},
        ]
        entry = JournalEntryService.create_journal_entry(
            organization=self.org,
            user=self.user,
            fiscal_period=p1,
            entry_date=date(2026, 1, 10),
            narration="Client initial retainer",
            lines_data=lines_data,
            reference="INV-2026-001",
        )

        self.assertEqual(entry.status, JournalStatus.DRAFT)
        self.assertTrue(entry.entry_number.startswith("JE-2026-"))
        self.assertEqual(entry.total_debit, Decimal("1200.00"))

        # In draft, account current_balance must remain 0.00
        cash.refresh_from_db()
        revenue.refresh_from_db()
        self.assertEqual(cash.current_balance, Decimal("0.00"))
        self.assertEqual(revenue.current_balance, Decimal("0.00"))

        # Post entry to general ledger
        posted_entry = JournalEntryService.post_journal_entry(entry, self.user)
        self.assertEqual(posted_entry.status, JournalStatus.POSTED)
        self.assertIsNotNone(posted_entry.posted_at)
        self.assertEqual(posted_entry.posted_by, self.user)

        # Verify account balances updated according to normal balances:
        # Cash (Normal DEBIT): 1200.00
        cash.refresh_from_db()
        self.assertEqual(cash.current_balance, Decimal("1200.00"))

        # Revenue (Normal CREDIT): 1200.00
        revenue.refresh_from_db()
        self.assertEqual(revenue.current_balance, Decimal("1200.00"))

    def test_unbalanced_journal_entry_rejected(self):
        GLAccountService.provision_standard_chart_of_accounts(self.org)
        fy = FiscalPeriodService.create_fiscal_year(
            organization=self.org,
            name="Fiscal Year 2026",
            code="FY2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        p1 = fy.periods.get(period_number=1)
        cash = GLAccount.objects.get(organization=self.org, code="1010")
        revenue = GLAccount.objects.get(organization=self.org, code="4010")

        # Unbalanced: Debit 500 != Credit 400
        unbalanced_lines = [
            {"account": cash, "debit": Decimal("500.00"), "credit": Decimal("0.00")},
            {"account": revenue, "debit": Decimal("0.00"), "credit": Decimal("400.00")},
        ]
        with self.assertRaises(ValidationError):
            JournalEntryService.create_journal_entry(
                organization=self.org,
                user=self.user,
                fiscal_period=p1,
                entry_date=date(2026, 1, 10),
                narration="Unbalanced test",
                lines_data=unbalanced_lines,
            )

    def test_closed_fiscal_period_prevents_postings(self):
        GLAccountService.provision_standard_chart_of_accounts(self.org)
        fy = FiscalPeriodService.create_fiscal_year(
            organization=self.org,
            name="Fiscal Year 2026",
            code="FY2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        p1 = fy.periods.get(period_number=1)
        cash = GLAccount.objects.get(organization=self.org, code="1010")
        revenue = GLAccount.objects.get(organization=self.org, code="4010")

        lines_data = [
            {"account": cash, "debit": Decimal("250.00"), "credit": Decimal("0.00")},
            {"account": revenue, "debit": Decimal("0.00"), "credit": Decimal("250.00")},
        ]
        entry = JournalEntryService.create_journal_entry(
            organization=self.org,
            user=self.user,
            fiscal_period=p1,
            entry_date=date(2026, 1, 5),
            narration="Lock period test",
            lines_data=lines_data,
        )

        # Manually lock period
        p1.is_closed = True
        p1.save()

        # Posting should fail due to closed period
        with self.assertRaises(ValidationError):
            JournalEntryService.post_journal_entry(entry, self.user)

    def test_journal_entry_reversal_lifecycle(self):
        GLAccountService.provision_standard_chart_of_accounts(self.org)
        fy = FiscalPeriodService.create_fiscal_year(
            organization=self.org,
            name="Fiscal Year 2026",
            code="FY2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        p1 = fy.periods.get(period_number=1)
        cash = GLAccount.objects.get(organization=self.org, code="1010")
        rent = GLAccount.objects.get(organization=self.org, code="6020")  # Rent Expense

        # Post Rent payment: Debit Rent 2000, Credit Cash 2000
        lines = [
            {"account": rent, "debit": Decimal("2000.00"), "credit": Decimal("0.00"), "narration": "Office lease"},
            {"account": cash, "debit": Decimal("0.00"), "credit": Decimal("2000.00"), "narration": "Disbursement"},
        ]
        entry = JournalEntryService.create_journal_entry(
            organization=self.org,
            user=self.user,
            fiscal_period=p1,
            entry_date=date(2026, 1, 2),
            narration="Office rent",
            lines_data=lines,
        )
        JournalEntryService.post_journal_entry(entry, self.user)

        rent.refresh_from_db()
        cash.refresh_from_db()
        self.assertEqual(rent.current_balance, Decimal("2000.00"))  # Expense normal balance = DEBIT
        self.assertEqual(cash.current_balance, Decimal("-2000.00"))  # Asset normal balance = DEBIT, credited so -2000

        # Execute reversal
        rev_entry = JournalEntryService.reverse_journal_entry(
            entry,
            self.user,
            reversal_date=date(2026, 1, 15),
            narration="Void duplicate lease payment",
        )

        # Verify original entry status
        entry.refresh_from_db()
        self.assertEqual(entry.status, JournalStatus.REVERSED)
        self.assertEqual(entry.reversed_by_entry, rev_entry)

        # Verify reversal entry
        self.assertEqual(rev_entry.status, JournalStatus.POSTED)
        self.assertEqual(rev_entry.source_document_type, SourceDocumentType.REVERSAL)

        # Verify account balances restored to 0.00!
        rent.refresh_from_db()
        cash.refresh_from_db()
        self.assertEqual(rent.current_balance, Decimal("0.00"))
        self.assertEqual(cash.current_balance, Decimal("0.00"))

    def test_finance_views_response(self):
        GLAccountService.provision_standard_chart_of_accounts(self.org)
        fy = FiscalPeriodService.create_fiscal_year(
            organization=self.org,
            name="Fiscal Year 2026",
            code="FY2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )

        # Dashboard View
        resp = self.client.get(reverse("finance:dashboard"))
        self.assertEqual(resp.status_code, 200)

        # COA List View
        resp = self.client.get(reverse("finance:account_list"))
        self.assertEqual(resp.status_code, 200)

        # Account Detail Ledger Card View
        cash = GLAccount.objects.get(organization=self.org, code="1010")
        resp = self.client.get(reverse("finance:account_detail", kwargs={"pk": cash.pk}))
        self.assertEqual(resp.status_code, 200)

        # Fiscal Year List View
        resp = self.client.get(reverse("finance:fiscal_year_list"))
        self.assertEqual(resp.status_code, 200)

        # Journal Entry List View
        resp = self.client.get(reverse("finance:journal_entry_list"))
        self.assertEqual(resp.status_code, 200)
