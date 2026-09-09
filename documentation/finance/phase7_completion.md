# EnterpriseOne Phase 7 — Finance Completion

## Scope

Phase 7 contains the general ledger foundation plus operational finance workflows: fiscal calendars, chart of accounts, double-entry journals, tax configuration, accounts receivable, accounts payable, payments, budgets, fixed assets, banking, reconciliation and financial reporting.

## Accounting controls

- Posted journals must balance debit and credit totals.
- Closed fiscal periods reject posting.
- Financial records are scoped to the active organization.
- Invoice and bill totals are derived from their lines.
- Receipts and supplier payments cannot exceed the open balance.
- Asset depreciation cannot be generated twice for the same asset and period.
- Bank reconciliations expose a calculated difference.

## Migrations

- `0001_initial.py` — ledger foundation
- `0002_operational_finance.py` — operational finance
- `0003_payment_allocations.py` — payment allocation references

## Verification

Python compilation succeeds across the application source. The full Django test suite should be run in the target environment after installing `requirements.txt`.
