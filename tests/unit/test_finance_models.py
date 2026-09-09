"""
Unit tests for Finance & General Ledger Models and Core Rules (Milestone 7.1).
"""
from datetime import date
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.accounts.models import User
from apps.organizations.models import Organization
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
from apps.finance.services import FiscalPeriodService


class FinanceModelTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Apex Financial Corp",
            code="APEX-FIN",
            slug="apex-fin-unique-test",
            tax_id="US-998877",
        )
        self.user = User.objects.create_user(
            email="accountant@apex.com",
            password="SecurePassword123!",
            first_name="Alice",
            last_name="CFO",
        )
        self.fiscal_year = FiscalYear.objects.create(
            organization=self.org,
            name="Fiscal Year 2026",
            code="FY2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        self.period1 = FiscalPeriod.objects.create(
            fiscal_year=self.fiscal_year,
            organization=self.org,
            period_number=1,
            name="Period 01 - Jan 2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
        )

    def test_fiscal_year_validation(self):
        # End date must be after start date
        invalid_fy = FiscalYear(
            organization=self.org,
            name="Invalid FY",
            code="FY-INV",
            start_date=date(2026, 12, 31),
            end_date=date(2026, 1, 1),
        )
        with self.assertRaises(ValidationError):
            invalid_fy.clean()

    def test_fiscal_period_boundaries(self):
        # Period outside fiscal year range should fail clean
        invalid_period = FiscalPeriod(
            fiscal_year=self.fiscal_year,
            organization=self.org,
            period_number=13,
            name="Period 13",
            start_date=date(2027, 1, 1),
            end_date=date(2027, 1, 31),
        )
        with self.assertRaises(ValidationError):
            invalid_period.clean()

    def test_gl_account_normal_balance_validation(self):
        # Asset must have DEBIT normal balance
        invalid_asset = GLAccount(
            organization=self.org,
            code="1015",
            name="Bad Cash Account",
            category=AccountCategory.ASSET,
            subtype=AccountSubtype.CASH,
            normal_balance=NormalBalance.CREDIT,  # Invalid for Asset
        )
        with self.assertRaises(ValidationError):
            invalid_asset.clean()

        # Revenue must have CREDIT normal balance
        invalid_rev = GLAccount(
            organization=self.org,
            code="4015",
            name="Bad Revenue Account",
            category=AccountCategory.REVENUE,
            subtype=AccountSubtype.OPERATING_REVENUE,
            normal_balance=NormalBalance.DEBIT,  # Invalid for Revenue
        )
        with self.assertRaises(ValidationError):
            invalid_rev.clean()

    def test_gl_account_parent_cross_org_validation(self):
        other_org = Organization.objects.create(
            name="Other Corp",
            code="OTHER-CORP",
            slug="other-corp-fin-test",
        )
        other_parent = GLAccount.objects.create(
            organization=other_org,
            code="1000",
            name="Other Parent",
            category=AccountCategory.ASSET,
            subtype=AccountSubtype.CURRENT_ASSET,
            normal_balance=NormalBalance.DEBIT,
        )
        child = GLAccount(
            organization=self.org,
            code="1011",
            name="Apex Child",
            category=AccountCategory.ASSET,
            subtype=AccountSubtype.CASH,
            normal_balance=NormalBalance.DEBIT,
            parent=other_parent,
        )
        with self.assertRaises(ValidationError):
            child.clean()

    def test_journal_entry_balancing_calculation(self):
        cash_acc = GLAccount.objects.create(
            organization=self.org,
            code="1010",
            name="Cash",
            category=AccountCategory.ASSET,
            subtype=AccountSubtype.CASH,
            normal_balance=NormalBalance.DEBIT,
        )
        rev_acc = GLAccount.objects.create(
            organization=self.org,
            code="4010",
            name="Sales",
            category=AccountCategory.REVENUE,
            subtype=AccountSubtype.OPERATING_REVENUE,
            normal_balance=NormalBalance.CREDIT,
        )

        entry = JournalEntry.objects.create(
            organization=self.org,
            entry_number="JE-2026-00001",
            entry_date=date(2026, 1, 15),
            fiscal_period=self.period1,
            narration="Cash sales test",
            created_by=self.user,
        )

        JournalEntryLine.objects.create(
            journal_entry=entry,
            line_number=1,
            account=cash_acc,
            debit=Decimal("500.00"),
            credit=Decimal("0.00"),
        )
        JournalEntryLine.objects.create(
            journal_entry=entry,
            line_number=2,
            account=rev_acc,
            debit=Decimal("0.00"),
            credit=Decimal("500.00"),
        )

        is_balanced = entry.calculate_totals()
        self.assertTrue(is_balanced)
        self.assertEqual(entry.total_debit, Decimal("500.00"))
        self.assertEqual(entry.total_credit, Decimal("500.00"))

    def test_journal_entry_line_validation_rules(self):
        cash_acc = GLAccount.objects.create(
            organization=self.org,
            code="1010",
            name="Cash",
            category=AccountCategory.ASSET,
            subtype=AccountSubtype.CASH,
            normal_balance=NormalBalance.DEBIT,
            allow_direct_posting=False,  # Header account
        )
        entry = JournalEntry.objects.create(
            organization=self.org,
            entry_number="JE-2026-00002",
            entry_date=date(2026, 1, 15),
            fiscal_period=self.period1,
            narration="Direct posting test",
            created_by=self.user,
        )

        # 1. Direct posting prohibited
        line = JournalEntryLine(
            journal_entry=entry,
            line_number=1,
            account=cash_acc,
            debit=Decimal("100.00"),
            credit=Decimal("0.00"),
        )
        with self.assertRaises(ValidationError):
            line.clean()

        cash_acc.allow_direct_posting = True
        cash_acc.save()

        # 2. Both debit and credit zero
        zero_line = JournalEntryLine(
            journal_entry=entry,
            line_number=1,
            account=cash_acc,
            debit=Decimal("0.00"),
            credit=Decimal("0.00"),
        )
        with self.assertRaises(ValidationError):
            zero_line.clean()

        # 3. Both debit and credit positive
        both_line = JournalEntryLine(
            journal_entry=entry,
            line_number=1,
            account=cash_acc,
            debit=Decimal("100.00"),
            credit=Decimal("50.00"),
        )
        with self.assertRaises(ValidationError):
            both_line.clean()

        # 4. Negative debit
        neg_line = JournalEntryLine(
            journal_entry=entry,
            line_number=1,
            account=cash_acc,
            debit=Decimal("-10.00"),
            credit=Decimal("0.00"),
        )
        with self.assertRaises(ValidationError):
            neg_line.clean()
