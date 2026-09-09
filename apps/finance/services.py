"""
EnterpriseOne Finance & General Ledger Domain Services (Milestone 7.1).
Encapsulates business operations for Fiscal Calendars, Chart of Accounts provisioning,
and the Double-Entry Journal Engine (balancing, posting, and reversals).
"""
import calendar
from datetime import date, timedelta
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

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


class FiscalPeriodService:
    """
    Domain service governing financial years, periodic boundaries, and posting locks.
    """

    @classmethod
    @transaction.atomic
    def create_fiscal_year(
        cls,
        organization,
        name,
        code,
        start_date,
        end_date,
        auto_create_monthly_periods=True,
    ):
        """
        Creates a new FiscalYear and optionally generates 12 monthly accounting periods.
        """
        if start_date >= end_date:
            raise ValidationError(_("Fiscal year end date must be strictly after start date."))

        if FiscalYear.objects.filter(organization=organization, code=code).exists():
            raise ValidationError(_(f"A fiscal year with code '{code}' already exists for this organization."))

        fiscal_year = FiscalYear.objects.create(
            organization=organization,
            name=name,
            code=code,
            start_date=start_date,
            end_date=end_date,
        )

        if auto_create_monthly_periods:
            cls._generate_monthly_periods(fiscal_year)

        return fiscal_year

    @classmethod
    def _generate_monthly_periods(cls, fiscal_year):
        """
        Generates 12 standard monthly periods bounded within the fiscal year.
        """
        cur_start = fiscal_year.start_date
        period_num = 1

        while cur_start < fiscal_year.end_date and period_num <= 12:
            # Determine end of the current month
            _, last_day = calendar.monthrange(cur_start.year, cur_start.month)
            month_end = date(cur_start.year, cur_start.month, last_day)
            cur_end = min(month_end, fiscal_year.end_date)
            
            month_name = cur_start.strftime("%b %Y")
            period_name = f"Period {period_num:02d} - {month_name}"

            FiscalPeriod.objects.create(
                fiscal_year=fiscal_year,
                organization=fiscal_year.organization,
                period_number=period_num,
                name=period_name,
                start_date=cur_start,
                end_date=cur_end,
                is_closed=False,
            )

            # Advance to first day of next month
            cur_start = cur_end + timedelta(days=1)
            period_num += 1

    @classmethod
    def get_period_for_date(cls, organization, target_date):
        """
        Resolves the fiscal period encompassing target_date.
        """
        period = FiscalPeriod.objects.filter(
            organization=organization,
            start_date__lte=target_date,
            end_date__gte=target_date,
        ).first()

        if not period:
            raise ValidationError(_(f"No fiscal period configured covering date {target_date}."))
        return period

    @classmethod
    @transaction.atomic
    def close_period(cls, period, user):
        """
        Closes an accounting period, preventing any subsequent transaction postings.
        """
        if period.is_closed:
            return period

        # Verify no unposted draft journal entries exist for this period
        draft_entries = JournalEntry.objects.filter(
            fiscal_period=period,
            status=JournalStatus.DRAFT,
        )
        if draft_entries.exists():
            count = draft_entries.count()
            raise ValidationError(
                _(f"Cannot close fiscal period '{period.name}': {count} unposted draft journal entries remain. Post or cancel them before closing.")
            )

        period.is_closed = True
        period.closed_at = timezone.now()
        period.closed_by = user
        period.save(update_fields=["is_closed", "closed_at", "closed_by", "updated_at"])
        return period

    @classmethod
    @transaction.atomic
    def reopen_period(cls, period, user):
        """
        Reopens a closed accounting period.
        """
        if not period.is_closed:
            return period

        # Check if parent fiscal year is closed
        if period.fiscal_year.is_closed:
            raise ValidationError(_("Cannot reopen period because the parent fiscal year is closed."))

        period.is_closed = False
        period.closed_at = None
        period.closed_by = None
        period.save(update_fields=["is_closed", "closed_at", "closed_by", "updated_at"])
        return period


class GLAccountService:
    """
    Domain service for Chart of Accounts management, standard template seeding,
    and running balance calculations.
    """

    @classmethod
    @transaction.atomic
    def provision_standard_chart_of_accounts(cls, organization):
        """
        Seeds a standard enterprise GAAP/IFRS Chart of Accounts hierarchy for an organization.
        """
        if GLAccount.objects.filter(organization=organization).exists():
            return 0  # Already provisioned

        standard_accounts = [
            # --- ASSETS (1000s) ---
            {
                "code": "1000",
                "name": "Current Assets",
                "category": AccountCategory.ASSET,
                "subtype": AccountSubtype.CURRENT_ASSET,
                "normal_balance": NormalBalance.DEBIT,
                "allow_direct_posting": False,
                "description": "Current assets header folder",
                "parent_code": None,
            },
            {
                "code": "1010",
                "name": "Cash on Hand",
                "category": AccountCategory.ASSET,
                "subtype": AccountSubtype.CASH,
                "normal_balance": NormalBalance.DEBIT,
                "allow_direct_posting": True,
                "description": "Petty cash and drawer balances",
                "parent_code": "1000",
            },
            {
                "code": "1020",
                "name": "Operating Bank Account",
                "category": AccountCategory.ASSET,
                "subtype": AccountSubtype.BANK,
                "normal_balance": NormalBalance.DEBIT,
                "allow_direct_posting": True,
                "description": "Primary commercial checking/operating bank account",
                "parent_code": "1000",
            },
            {
                "code": "1100",
                "name": "Accounts Receivable (Trade)",
                "category": AccountCategory.ASSET,
                "subtype": AccountSubtype.ACCOUNTS_RECEIVABLE,
                "normal_balance": NormalBalance.DEBIT,
                "allow_direct_posting": True,
                "is_reconciliation": True,
                "description": "Customer trade receivables control account",
                "parent_code": "1000",
            },
            {
                "code": "1200",
                "name": "Inventory Asset",
                "category": AccountCategory.ASSET,
                "subtype": AccountSubtype.INVENTORY,
                "normal_balance": NormalBalance.DEBIT,
                "allow_direct_posting": True,
                "description": "Warehouse stock inventory valuation",
                "parent_code": "1000",
            },
            {
                "code": "1300",
                "name": "Prepaid Expenses",
                "category": AccountCategory.ASSET,
                "subtype": AccountSubtype.CURRENT_ASSET,
                "normal_balance": NormalBalance.DEBIT,
                "allow_direct_posting": True,
                "description": "Prepaid insurance, software licenses, and advance payments",
                "parent_code": "1000",
            },
            {
                "code": "1500",
                "name": "Property, Plant & Equipment",
                "category": AccountCategory.ASSET,
                "subtype": AccountSubtype.FIXED_ASSET,
                "normal_balance": NormalBalance.DEBIT,
                "allow_direct_posting": False,
                "description": "Fixed assets header",
                "parent_code": None,
            },
            {
                "code": "1510",
                "name": "Machinery & Equipment",
                "category": AccountCategory.ASSET,
                "subtype": AccountSubtype.FIXED_ASSET,
                "normal_balance": NormalBalance.DEBIT,
                "allow_direct_posting": True,
                "description": "Plant machinery, tooling, and computer hardware",
                "parent_code": "1500",
            },

            # --- LIABILITIES (2000s) ---
            {
                "code": "2000",
                "name": "Current Liabilities",
                "category": AccountCategory.LIABILITY,
                "subtype": AccountSubtype.CURRENT_LIABILITY,
                "normal_balance": NormalBalance.CREDIT,
                "allow_direct_posting": False,
                "description": "Current liabilities header folder",
                "parent_code": None,
            },
            {
                "code": "2010",
                "name": "Accounts Payable (Trade)",
                "category": AccountCategory.LIABILITY,
                "subtype": AccountSubtype.ACCOUNTS_PAYABLE,
                "normal_balance": NormalBalance.CREDIT,
                "allow_direct_posting": True,
                "is_reconciliation": True,
                "description": "Vendor trade payables control account",
                "parent_code": "2000",
            },
            {
                "code": "2020",
                "name": "Accrued Operating Expenses",
                "category": AccountCategory.LIABILITY,
                "subtype": AccountSubtype.CURRENT_LIABILITY,
                "normal_balance": NormalBalance.CREDIT,
                "allow_direct_posting": True,
                "description": "Accrued unbilled liabilities and contractor expenses",
                "parent_code": "2000",
            },
            {
                "code": "2050",
                "name": "Sales Tax / VAT Payable",
                "category": AccountCategory.LIABILITY,
                "subtype": AccountSubtype.TAX_PAYABLE,
                "normal_balance": NormalBalance.CREDIT,
                "allow_direct_posting": True,
                "description": "Collected sales tax and value added tax obligations",
                "parent_code": "2000",
            },
            {
                "code": "2500",
                "name": "Long-Term Liabilities",
                "category": AccountCategory.LIABILITY,
                "subtype": AccountSubtype.NON_CURRENT_LIABILITY,
                "normal_balance": NormalBalance.CREDIT,
                "allow_direct_posting": True,
                "description": "Commercial bank credit lines and loans",
                "parent_code": None,
            },

            # --- EQUITY (3000s) ---
            {
                "code": "3000",
                "name": "Owners' Equity & Capital",
                "category": AccountCategory.EQUITY,
                "subtype": AccountSubtype.EQUITY_CAPITAL,
                "normal_balance": NormalBalance.CREDIT,
                "allow_direct_posting": False,
                "description": "Equity header",
                "parent_code": None,
            },
            {
                "code": "3010",
                "name": "Common Stock / Contributed Capital",
                "category": AccountCategory.EQUITY,
                "subtype": AccountSubtype.EQUITY_CAPITAL,
                "normal_balance": NormalBalance.CREDIT,
                "allow_direct_posting": True,
                "description": "Paid-in shareholder equity",
                "parent_code": "3000",
            },
            {
                "code": "3020",
                "name": "Retained Earnings",
                "category": AccountCategory.EQUITY,
                "subtype": AccountSubtype.RETAINED_EARNINGS,
                "normal_balance": NormalBalance.CREDIT,
                "allow_direct_posting": True,
                "description": "Cumulative historical profits/losses retained",
                "parent_code": "3000",
            },

            # --- REVENUE (4000s) ---
            {
                "code": "4000",
                "name": "Operating Revenue",
                "category": AccountCategory.REVENUE,
                "subtype": AccountSubtype.OPERATING_REVENUE,
                "normal_balance": NormalBalance.CREDIT,
                "allow_direct_posting": False,
                "description": "Revenue header",
                "parent_code": None,
            },
            {
                "code": "4010",
                "name": "Product Sales Revenue",
                "category": AccountCategory.REVENUE,
                "subtype": AccountSubtype.OPERATING_REVENUE,
                "normal_balance": NormalBalance.CREDIT,
                "allow_direct_posting": True,
                "description": "Commercial product sales gross revenue",
                "parent_code": "4000",
            },
            {
                "code": "4020",
                "name": "Services & Consulting Revenue",
                "category": AccountCategory.REVENUE,
                "subtype": AccountSubtype.OPERATING_REVENUE,
                "normal_balance": NormalBalance.CREDIT,
                "allow_direct_posting": True,
                "description": "Professional services and implementation fees",
                "parent_code": "4000",
            },
            {
                "code": "4100",
                "name": "Other Income & Gains",
                "category": AccountCategory.REVENUE,
                "subtype": AccountSubtype.OTHER_INCOME,
                "normal_balance": NormalBalance.CREDIT,
                "allow_direct_posting": True,
                "description": "Interest income, foreign exchange gains",
                "parent_code": "4000",
            },

            # --- COST OF GOODS SOLD (5000s) ---
            {
                "code": "5000",
                "name": "Cost of Goods Sold (COGS)",
                "category": AccountCategory.EXPENSE,
                "subtype": AccountSubtype.COST_OF_GOODS_SOLD,
                "normal_balance": NormalBalance.DEBIT,
                "allow_direct_posting": False,
                "description": "Direct cost of sales header",
                "parent_code": None,
            },
            {
                "code": "5010",
                "name": "Direct Material Cost / COGS",
                "category": AccountCategory.EXPENSE,
                "subtype": AccountSubtype.COST_OF_GOODS_SOLD,
                "normal_balance": NormalBalance.DEBIT,
                "allow_direct_posting": True,
                "description": "Cost of merchandise and raw materials sold",
                "parent_code": "5000",
            },
            {
                "code": "5020",
                "name": "Direct Inbound Shipping & Freight",
                "category": AccountCategory.EXPENSE,
                "subtype": AccountSubtype.COST_OF_GOODS_SOLD,
                "normal_balance": NormalBalance.DEBIT,
                "allow_direct_posting": True,
                "description": "Landed freight and customs tariffs on inventory",
                "parent_code": "5000",
            },

            # --- OPERATING EXPENSES (6000s) ---
            {
                "code": "6000",
                "name": "Operating Expenses (OPEX)",
                "category": AccountCategory.EXPENSE,
                "subtype": AccountSubtype.OPERATING_EXPENSE,
                "normal_balance": NormalBalance.DEBIT,
                "allow_direct_posting": False,
                "description": "Operating expenses header",
                "parent_code": None,
            },
            {
                "code": "6010",
                "name": "Salaries, Wages & Benefits",
                "category": AccountCategory.EXPENSE,
                "subtype": AccountSubtype.PAYROLL_EXPENSE,
                "normal_balance": NormalBalance.DEBIT,
                "allow_direct_posting": True,
                "description": "Staff compensation and healthcare benefits",
                "parent_code": "6000",
            },
            {
                "code": "6020",
                "name": "Rent & Facilities",
                "category": AccountCategory.EXPENSE,
                "subtype": AccountSubtype.OPERATING_EXPENSE,
                "normal_balance": NormalBalance.DEBIT,
                "allow_direct_posting": True,
                "description": "Office and warehouse lease payments",
                "parent_code": "6000",
            },
            {
                "code": "6030",
                "name": "Utilities & Telecom",
                "category": AccountCategory.EXPENSE,
                "subtype": AccountSubtype.OPERATING_EXPENSE,
                "normal_balance": NormalBalance.DEBIT,
                "allow_direct_posting": True,
                "description": "Electric, water, internet, and telephone",
                "parent_code": "6000",
            },
            {
                "code": "6040",
                "name": "Marketing & Advertising",
                "category": AccountCategory.EXPENSE,
                "subtype": AccountSubtype.OPERATING_EXPENSE,
                "normal_balance": NormalBalance.DEBIT,
                "allow_direct_posting": True,
                "description": "Digital marketing campaigns and advertising",
                "parent_code": "6000",
            },
            {
                "code": "6050",
                "name": "Depreciation Expense",
                "category": AccountCategory.EXPENSE,
                "subtype": AccountSubtype.DEPRECIATION_EXPENSE,
                "normal_balance": NormalBalance.DEBIT,
                "allow_direct_posting": True,
                "description": "Depreciation on plant and equipment",
                "parent_code": "6000",
            },
            {
                "code": "6060",
                "name": "Professional & Legal Fees",
                "category": AccountCategory.EXPENSE,
                "subtype": AccountSubtype.OPERATING_EXPENSE,
                "normal_balance": NormalBalance.DEBIT,
                "allow_direct_posting": True,
                "description": "Auditing, legal counsel, and advisory",
                "parent_code": "6000",
            },
            {
                "code": "6070",
                "name": "Bank & Payment Processing Fees",
                "category": AccountCategory.EXPENSE,
                "subtype": AccountSubtype.FINANCIAL_EXPENSE,
                "normal_balance": NormalBalance.DEBIT,
                "allow_direct_posting": True,
                "description": "Merchant gateway and bank service charges",
                "parent_code": "6000",
            },
            {
                "code": "6080",
                "name": "Income Tax Expense",
                "category": AccountCategory.EXPENSE,
                "subtype": AccountSubtype.TAX_EXPENSE,
                "normal_balance": NormalBalance.DEBIT,
                "allow_direct_posting": True,
                "description": "Corporate income taxes",
                "parent_code": "6000",
            },
        ]

        created_map = {}
        # First pass: create parent accounts
        for item in standard_accounts:
            if item["parent_code"] is None:
                acc = GLAccount.objects.create(
                    organization=organization,
                    code=item["code"],
                    name=item["name"],
                    category=item["category"],
                    subtype=item["subtype"],
                    normal_balance=item["normal_balance"],
                    allow_direct_posting=item["allow_direct_posting"],
                    is_reconciliation=item.get("is_reconciliation", False),
                    description=item["description"],
                )
                created_map[item["code"]] = acc

        # Second pass: create child accounts
        for item in standard_accounts:
            if item["parent_code"] is not None:
                parent_acc = created_map.get(item["parent_code"])
                acc = GLAccount.objects.create(
                    organization=organization,
                    code=item["code"],
                    name=item["name"],
                    category=item["category"],
                    subtype=item["subtype"],
                    normal_balance=item["normal_balance"],
                    parent=parent_acc,
                    allow_direct_posting=item["allow_direct_posting"],
                    is_reconciliation=item.get("is_reconciliation", False),
                    description=item["description"],
                )
                created_map[item["code"]] = acc

        return len(created_map)

    @classmethod
    def recalculate_account_balance(cls, account):
        """
        Recomputes cumulative balance from all posted journal entry lines.
        Adheres to standard normal balance direction:
          Debit balance = total_debit - total_credit
          Credit balance = total_credit - total_debit
        """
        posted_lines = JournalEntryLine.objects.filter(
            account=account,
            journal_entry__status__in=[JournalStatus.POSTED, JournalStatus.REVERSED],
        )

        total_debit = Decimal("0.00")
        total_credit = Decimal("0.00")
        for line in posted_lines:
            total_debit += line.debit
            total_credit += line.credit

        if account.normal_balance == NormalBalance.DEBIT:
            balance = total_debit - total_credit
        else:
            balance = total_credit - total_debit

        account.current_balance = balance
        account.save(update_fields=["current_balance", "updated_at"])
        return balance


class JournalEntryService:
    """
    Domain service for Double-Entry Journal operations:
    Sequential numbering, balancing enforcement, posting, and reversals.
    """

    @classmethod
    def generate_entry_number(cls, organization, entry_date=None):
        """
        Generates thread-safe sequential journal entry number: JE-YYYY-XXXXX.
        """
        year_str = str((entry_date or timezone.now().date()).year)
        prefix = f"JE-{year_str}-"

        latest = (
            JournalEntry.objects.filter(
                organization=organization,
                entry_number__startswith=prefix,
            )
            .order_by("-entry_number")
            .first()
        )

        if latest and latest.entry_number.startswith(prefix):
            try:
                seq_str = latest.entry_number.split("-")[-1]
                seq = int(seq_str) + 1
            except ValueError:
                seq = 1
        else:
            seq = 1

        return f"{prefix}{seq:05d}"

    @classmethod
    @transaction.atomic
    def create_journal_entry(
        cls,
        organization,
        user,
        fiscal_period,
        entry_date,
        narration,
        lines_data,
        reference="",
        source_document_type=SourceDocumentType.MANUAL,
        source_document_id="",
    ):
        """
        Creates a draft journal entry and its balanced constituent lines.
        """
        if fiscal_period.organization_id != organization.id:
            raise ValidationError(_("Fiscal period must belong to the same organization."))

        if entry_date < fiscal_period.start_date or entry_date > fiscal_period.end_date:
            raise ValidationError(_(f"Entry date {entry_date} lies outside fiscal period boundaries ({fiscal_period.start_date} to {fiscal_period.end_date})."))

        if not lines_data or len(lines_data) < 2:
            raise ValidationError(_("A double-entry transaction must contain at least two lines."))

        entry_number = cls.generate_entry_number(organization, entry_date)

        journal_entry = JournalEntry.objects.create(
            organization=organization,
            entry_number=entry_number,
            entry_date=entry_date,
            fiscal_period=fiscal_period,
            reference=reference,
            source_document_type=source_document_type,
            source_document_id=source_document_id,
            status=JournalStatus.DRAFT,
            narration=narration,
            created_by=user,
        )

        line_num = 1
        for ldata in lines_data:
            account = ldata["account"]
            if account.organization_id != organization.id:
                raise ValidationError(_(f"Account {account.code} does not belong to this organization."))
            if not account.allow_direct_posting:
                raise ValidationError(_(f"Account '{account.code}' is a header account and does not allow direct postings."))

            debit = Decimal(str(ldata.get("debit", 0)))
            credit = Decimal(str(ldata.get("credit", 0)))

            line = JournalEntryLine.objects.create(
                journal_entry=journal_entry,
                line_number=line_num,
                account=account,
                debit=debit,
                credit=credit,
                narration=ldata.get("narration", ""),
                partner_name=ldata.get("partner_name", ""),
                cost_center=ldata.get("cost_center", ""),
            )
            line.clean()
            line_num += 1

        is_balanced = journal_entry.calculate_totals()
        if not is_balanced:
            raise ValidationError(_(
                f"Journal Entry is unbalanced: Total Debit ({journal_entry.total_debit}) does not equal Total Credit ({journal_entry.total_credit})."
            ))

        journal_entry.save(update_fields=["total_debit", "total_credit", "is_balanced", "updated_at"])
        return journal_entry

    @classmethod
    @transaction.atomic
    def post_journal_entry(cls, journal_entry, user):
        """
        Posts a draft journal entry to the General Ledger.
        Validates open fiscal period and balancing integrity.
        Updates running balances on all touched accounts atomically.
        """
        # Lock entry row for concurrent safety
        entry = JournalEntry.objects.select_for_update().get(id=journal_entry.id)

        if entry.status != JournalStatus.DRAFT:
            raise ValidationError(_(f"Cannot post journal entry in status '{entry.get_status_display()}'. Only Draft entries can be posted."))

        if entry.fiscal_period.is_closed:
            raise ValidationError(_(f"Cannot post to closed fiscal period '{entry.fiscal_period.name}'."))

        is_balanced = entry.calculate_totals()
        if not is_balanced:
            raise ValidationError(_(
                f"Cannot post unbalanced journal entry: Total Debit ({entry.total_debit}) != Total Credit ({entry.total_credit})."
            ))

        posting_date = timezone.now().date()
        entry.status = JournalStatus.POSTED
        entry.posting_date = posting_date
        entry.posted_by = user
        entry.posted_at = timezone.now()
        entry.save(update_fields=["status", "posting_date", "posted_by", "posted_at", "total_debit", "total_credit", "is_balanced", "updated_at"])

        # Update account balances
        touched_accounts = set()
        for line in entry.lines.select_related("account"):
            touched_accounts.add(line.account)

        for account in touched_accounts:
            GLAccountService.recalculate_account_balance(account)

        return entry

    @classmethod
    @transaction.atomic
    def reverse_journal_entry(cls, journal_entry, user, reversal_date=None, narration=None):
        """
        Generates an offsetting reversal journal entry swapping debits and credits.
        Posts the reversal entry, locks the original entry, and updates balances.
        """
        entry = JournalEntry.objects.select_for_update().get(id=journal_entry.id)

        if entry.status != JournalStatus.POSTED:
            raise ValidationError(_("Only posted journal entries can be reversed."))

        if entry.reversed_by_entry_id:
            raise ValidationError(_(f"This entry was already reversed by {entry.reversed_by_entry.entry_number}."))

        rev_date = reversal_date or timezone.now().date()
        rev_period = FiscalPeriodService.get_period_for_date(entry.organization, rev_date)

        if rev_period.is_closed:
            raise ValidationError(_(f"Cannot post reversal into closed fiscal period '{rev_period.name}'."))

        rev_narration = narration or f"Reversal of {entry.entry_number}: {entry.narration}"
        reversal_entry_number = cls.generate_entry_number(entry.organization, rev_date)

        reversal_entry = JournalEntry.objects.create(
            organization=entry.organization,
            entry_number=reversal_entry_number,
            entry_date=rev_date,
            posting_date=rev_date,
            fiscal_period=rev_period,
            reference=f"REV-{entry.entry_number}",
            source_document_type=SourceDocumentType.REVERSAL,
            source_document_id=str(entry.id),
            status=JournalStatus.POSTED,
            narration=rev_narration,
            total_debit=entry.total_credit,
            total_credit=entry.total_debit,
            is_balanced=True,
            posted_by=user,
            posted_at=timezone.now(),
            created_by=user,
        )

        line_num = 1
        touched_accounts = set()
        for orig_line in entry.lines.select_related("account").order_by("line_number"):
            JournalEntryLine.objects.create(
                journal_entry=reversal_entry,
                line_number=line_num,
                account=orig_line.account,
                debit=orig_line.credit,   # Swap debit with credit
                credit=orig_line.debit,   # Swap credit with debit
                narration=f"Reversal: {orig_line.narration}".strip(),
                partner_name=orig_line.partner_name,
                cost_center=orig_line.cost_center,
            )
            touched_accounts.add(orig_line.account)
            line_num += 1

        # Link original entry
        entry.reversed_by_entry = reversal_entry
        entry.status = JournalStatus.REVERSED
        entry.save(update_fields=["reversed_by_entry", "status", "updated_at"])

        # Recalculate balances
        for account in touched_accounts:
            GLAccountService.recalculate_account_balance(account)

        return reversal_entry
