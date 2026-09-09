"""
EnterpriseOne Finance & General Ledger Models (Milestone 7.1).
Defines Fiscal Years, Accounting Periods, Chart of Accounts, and Double-Entry Journal Entries.
"""
import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class AccountCategory(models.TextChoices):
    ASSET = "asset", _("Asset")
    LIABILITY = "liability", _("Liability")
    EQUITY = "equity", _("Equity")
    REVENUE = "revenue", _("Revenue / Income")
    EXPENSE = "expense", _("Expense / Cost")


class AccountSubtype(models.TextChoices):
    # Assets
    CASH = "cash", _("Cash & Equivalents")
    BANK = "bank", _("Bank Account")
    ACCOUNTS_RECEIVABLE = "receivable", _("Accounts Receivable (AR)")
    CURRENT_ASSET = "current_asset", _("Other Current Asset")
    INVENTORY = "inventory", _("Inventory Asset")
    FIXED_ASSET = "fixed_asset", _("Property, Plant & Equipment")
    ACCUMULATED_DEPRECIATION = "depreciation", _("Accumulated Depreciation")
    NON_CURRENT_ASSET = "non_current_asset", _("Non-Current Asset")
    
    # Liabilities
    ACCOUNTS_PAYABLE = "payable", _("Accounts Payable (AP)")
    CURRENT_LIABILITY = "current_liability", _("Other Current Liability")
    TAX_PAYABLE = "tax_payable", _("Tax / VAT Payable")
    NON_CURRENT_LIABILITY = "non_current_liability", _("Long-Term Liability")
    
    # Equity
    EQUITY_CAPITAL = "equity_capital", _("Share / Owners Capital")
    RETAINED_EARNINGS = "retained_earnings", _("Retained Earnings")
    CURRENT_YEAR_EARNINGS = "current_year_earnings", _("Current Year Earnings")
    
    # Revenue
    OPERATING_REVENUE = "operating_revenue", _("Operating Revenue / Sales")
    OTHER_INCOME = "other_income", _("Other Income / Gains")
    
    # Expenses
    COST_OF_GOODS_SOLD = "cogs", _("Cost of Goods Sold (COGS)")
    OPERATING_EXPENSE = "operating_expense", _("Operating Expense (OPEX)")
    PAYROLL_EXPENSE = "payroll_expense", _("Salaries & Payroll")
    DEPRECIATION_EXPENSE = "depreciation_expense", _("Depreciation & Amortization")
    FINANCIAL_EXPENSE = "financial_expense", _("Interest & Finance Charges")
    TAX_EXPENSE = "tax_expense", _("Income Tax Expense")
    OTHER_EXPENSE = "other_expense", _("Other Expense / Losses")


class NormalBalance(models.TextChoices):
    DEBIT = "debit", _("Debit")
    CREDIT = "credit", _("Credit")


class FiscalYear(models.Model):
    """
    Financial Year definition establishing multi-period reporting calendars.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="fiscal_years",
        help_text="Tenant organization"
    )
    name = models.CharField(max_length=100, help_text="e.g., Fiscal Year 2026")
    code = models.CharField(max_length=20, help_text="e.g., FY2026")
    start_date = models.DateField()
    end_date = models.DateField()
    is_closed = models.BooleanField(default=False)
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="closed_fiscal_years"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Fiscal Year")
        verbose_name_plural = _("Fiscal Years")
        unique_together = [("organization", "code")]
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.code} ({self.organization.name})"

    def clean(self):
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValidationError({"end_date": _("End date must be strictly after start date.")})


class FiscalPeriod(models.Model):
    """
    Monthly or periodic accounting period boundary governing posting locks.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fiscal_year = models.ForeignKey(
        FiscalYear,
        on_delete=models.CASCADE,
        related_name="periods"
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="fiscal_periods"
    )
    period_number = models.PositiveSmallIntegerField(help_text="1 to 12 (or 13 for year-end)")
    name = models.CharField(max_length=50, help_text="e.g., Period 01 - Jan 2026")
    start_date = models.DateField()
    end_date = models.DateField()
    is_closed = models.BooleanField(default=False)
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="closed_fiscal_periods"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Fiscal Period")
        verbose_name_plural = _("Fiscal Periods")
        unique_together = [("fiscal_year", "period_number")]
        ordering = ["fiscal_year", "period_number"]

    def __str__(self):
        status_tag = " [CLOSED]" if self.is_closed else ""
        return f"{self.fiscal_year.code}-P{self.period_number:02d}: {self.name}{status_tag}"

    def clean(self):
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValidationError({"end_date": _("Period end date must be after start date.")})
        if self.fiscal_year:
            if self.start_date < self.fiscal_year.start_date or self.end_date > self.fiscal_year.end_date:
                raise ValidationError(_("Period dates must lie entirely within the fiscal year boundaries."))


class GLAccount(models.Model):
    """
    Master General Ledger Chart of Accounts node representing financial ledger classifications.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="gl_accounts"
    )
    code = models.CharField(max_length=30, help_text="Accounting account number, e.g. 1010, 2000, 4000")
    name = models.CharField(max_length=150, help_text="Account name, e.g. Cash in Bank, Accounts Payable")
    category = models.CharField(max_length=20, choices=AccountCategory.choices)
    subtype = models.CharField(max_length=40, choices=AccountSubtype.choices)
    normal_balance = models.CharField(max_length=10, choices=NormalBalance.choices)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
        help_text="Parent account for hierarchical reporting trees"
    )
    currency = models.CharField(max_length=3, default="USD")
    is_reconciliation = models.BooleanField(
        default=False,
        help_text="If True, acts as an AR/AP control reconciliation account"
    )
    is_active = models.BooleanField(default=True)
    allow_direct_posting = models.BooleanField(
        default=True,
        help_text="If False, acts purely as a header/rollup folder account"
    )
    description = models.TextField(blank=True)
    current_balance = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Current cumulative posted balance adhering to normal debit/credit sign"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("GL Account")
        verbose_name_plural = _("GL Accounts")
        unique_together = [("organization", "code")]
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.name}"

    def clean(self):
        if self.parent and self.parent.organization_id != self.organization_id:
            raise ValidationError({"parent": _("Parent account must belong to the identical organization.")})
        
        # Enforce canonical GAAP/IFRS normal balance defaults
        if self.category in [AccountCategory.ASSET, AccountCategory.EXPENSE]:
            expected_normal = NormalBalance.DEBIT
        else:
            expected_normal = NormalBalance.CREDIT
            
        if self.normal_balance != expected_normal:
            raise ValidationError({
                "normal_balance": _(f"Category '{self.get_category_display()}' requires a normal balance of {expected_normal.label}.")
            })


class JournalStatus(models.TextChoices):
    DRAFT = "draft", _("Draft (Unposted)")
    POSTED = "posted", _("Posted to General Ledger")
    REVERSED = "reversed", _("Reversed")


class SourceDocumentType(models.TextChoices):
    MANUAL = "manual", _("Manual General Journal")
    SALES_INVOICE = "sales_invoice", _("Sales Customer Invoice")
    VENDOR_BILL = "vendor_bill", _("Vendor Bill Payable")
    INVENTORY_VALUATION = "inventory_valuation", _("Inventory Stock Valuation")
    PAYMENT = "payment", _("Cash / Bank Payment")
    RECEIPT = "receipt", _("Customer Payment Receipt")
    REVERSAL = "reversal", _("Off-Setting Journal Reversal")
    CLOSING = "closing", _("Fiscal Period / Year Closing")


class JournalEntry(models.Model):
    """
    Double-entry accounting transaction voucher maintaining mathematical balancing integrity.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="journal_entries"
    )
    entry_number = models.CharField(max_length=50, help_text="e.g. JE-2026-00001")
    entry_date = models.DateField(default=timezone.now)
    posting_date = models.DateField(null=True, blank=True)
    fiscal_period = models.ForeignKey(
        FiscalPeriod,
        on_delete=models.PROTECT,
        related_name="journal_entries"
    )
    reference = models.CharField(max_length=100, blank=True, help_text="External voucher, check, or invoice ref")
    source_document_type = models.CharField(
        max_length=50,
        choices=SourceDocumentType.choices,
        default=SourceDocumentType.MANUAL
    )
    source_document_id = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=20,
        choices=JournalStatus.choices,
        default=JournalStatus.DRAFT
    )
    narration = models.TextField(help_text="Detailed transaction explanation / audit memo")
    total_debit = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))
    total_credit = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))
    is_balanced = models.BooleanField(default=True)
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="posted_journal_entries"
    )
    posted_at = models.DateTimeField(null=True, blank=True)
    reversed_by_entry = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reverses_entry",
        help_text="Link to the counter-balancing journal entry if reversed"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_journal_entries"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Journal Entry")
        verbose_name_plural = _("Journal Entries")
        unique_together = [("organization", "entry_number")]
        ordering = ["-entry_date", "-entry_number"]

    def __str__(self):
        return f"{self.entry_number} ({self.get_status_display()}) - {self.total_debit} USD"

    def calculate_totals(self):
        """
        Recalculates debits and credits across all constituent lines.
        """
        lines = self.lines.all()
        debit_sum = sum((line.debit for line in lines), Decimal("0.00"))
        credit_sum = sum((line.credit for line in lines), Decimal("0.00"))
        self.total_debit = debit_sum
        self.total_credit = credit_sum
        self.is_balanced = (debit_sum == credit_sum and debit_sum > Decimal("0.00"))
        return self.is_balanced

    def clean(self):
        if self.fiscal_period:
            if self.fiscal_period.organization_id != self.organization_id:
                raise ValidationError({"fiscal_period": _("Fiscal period must belong to the same organization.")})
            if self.entry_date < self.fiscal_period.start_date or self.entry_date > self.fiscal_period.end_date:
                raise ValidationError({"entry_date": _("Entry date must fall within the selected fiscal period boundaries.")})
            if self.fiscal_period.is_closed and self.status == JournalStatus.POSTED:
                raise ValidationError(_("Cannot post transactions to a closed fiscal period."))


class JournalEntryLine(models.Model):
    """
    Individual debit or credit ledger leg adhering to double-entry accounting.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    journal_entry = models.ForeignKey(
        JournalEntry,
        on_delete=models.CASCADE,
        related_name="lines"
    )
    line_number = models.PositiveSmallIntegerField(default=1)
    account = models.ForeignKey(
        GLAccount,
        on_delete=models.PROTECT,
        related_name="journal_lines"
    )
    debit = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))
    credit = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))
    narration = models.CharField(max_length=255, blank=True)
    partner_name = models.CharField(max_length=200, blank=True, help_text="Optional Customer or Supplier memo")
    cost_center = models.CharField(max_length=100, blank=True, help_text="Optional cost center / division tag")

    class Meta:
        verbose_name = _("Journal Entry Line")
        verbose_name_plural = _("Journal Entry Lines")
        ordering = ["line_number"]

    def __str__(self):
        return f"Line {self.line_number}: {self.account.code} | Dr: {self.debit} Cr: {self.credit}"

    def clean(self):
        if self.journal_entry_id and self.account_id:
            if self.account.organization_id != self.journal_entry.organization_id:
                raise ValidationError({"account": _("Account must belong to the identical organization.")})
        if not self.account.allow_direct_posting:
            raise ValidationError({"account": _(f"Account '{self.account.code}' is a header account and does not accept direct postings.")})
        if self.debit < Decimal("0.00"):
            raise ValidationError({"debit": _("Debit amount cannot be negative.")})
        if self.credit < Decimal("0.00"):
            raise ValidationError({"credit": _("Credit amount cannot be negative.")})
        if self.debit == Decimal("0.00") and self.credit == Decimal("0.00"):
            raise ValidationError(_("Line must contain either a non-zero debit or credit amount."))
        if self.debit > Decimal("0.00") and self.credit > Decimal("0.00"):
            raise ValidationError(_("A single line cannot simultaneously possess both debit and credit amounts."))
