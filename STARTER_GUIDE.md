# ClearLedger — Developer Guide (Track A)

A quick guide for running, testing, and reviewing **ClearLedger**.

---

## 1. Quick Start Commands

Run all commands from the `track-a` directory:

```bash
# Run all 19 unit and regression tests
python -m unittest discover -s tests -v

# Restore historical register fixture database & run web application
python restore_fixture.py --replace
python app.py
```

Open **`http://127.0.0.1:8787`** in your browser.

---

## 2. Deliverables & Fixes Summary

### 🛠️ Seeded Defect Fixes
- **Row-level Import Error Isolation** ([`ledger/importing.py`](ledger/importing.py)): Replaced fail-fast list comprehension with per-row validation and line-numbered error reporting (`errors` array).
- **Invoice Idempotency & Duplicate Rejection** ([`ledger/storage.py`](ledger/storage.py)): Skipped identical duplicate invoices and rejected conflicting details to protect financial data.
- **Strict Payment Matching** ([`ledger/matching.py`](ledger/matching.py)): Removed greedy amount matching to ensure payments attach strictly when both `customer_id` and `invoice_number` match.
- **Status Filter Logic** ([`ledger/reporting.py`](ledger/reporting.py)): Fixed inverted `'open'` filter mapping so open invoices ($balance > 0$) display correctly.
- **Monetary Precision in CSV Export** ([`ledger/reporting.py`](ledger/reporting.py)): Replaced float-truncating arithmetic (`int(val * 100) / 100`) with exact two-decimal formatting (`f"{val:.2f}"`).
- **Frontend Error Feedback** ([`web/app.js`](web/app.js)): Checked `response.ok`, parsed JSON counts (`imported`, `skipped`, `rejected`), and rendered line error details.

### ✨ Functional Accounting Improvements Added
1. **Overdue Invoices & Aging Indicator**: Dynamic calculation of `is_overdue` and `days_overdue`, Overdue metric card, `status=overdue` filter, and visual status badges (`Overdue (7d)`, `Open`, `Paid`).
2. **Unmatched Payment Resolution & Re-allocation (`POST /api/rematch`)**: Allows the owner to re-check unmatched payments (e.g. `KEEP-U1`) and automatically link them to newly imported/created invoices, updating invoice balances.
3. **Customer Summary Breakdown & Live Search**: Customer aggregation table (`total_invoiced`, `total_paid`, `outstanding`, `open_count`) and real-time live search filter.

---

## 3. Key Files Structure

```
track-a/
├── HANDOVER.md                 # Official handover notes & evidence
├── STARTER_GUIDE.md            # Developer guide & quick reference
├── BUSINESS_RULES.md           # Specification invariants
├── README.md                   # Assessment instructions
├── app.py                      # Server starter
├── restore_fixture.py          # Database restore script
├── fixtures/
│   ├── existing-register.sqlite3 # Synthetic historical DB (9 invoices, ₹3,698.19)
│   └── expected-records.json     # Baseline reference data
├── ledger/
│   ├── importing.py            # CSV import orchestrator (fixed)
│   ├── storage.py              # SQLite storage & idempotency (fixed)
│   ├── matching.py             # Payment-invoice matching & rematching (fixed)
│   ├── reporting.py            # Overview aggregations & export (fixed)
│   ├── validation.py           # Row validation & regex
│   └── http_app.py             # HTTP API handlers
├── web/
│   ├── index.html              # UI layout
│   ├── app.js                  # Frontend logic & live search
│   └── style.css               # Stylesheet & status badges
└── tests/
    ├── test_defects.py         # 5 targeted defect reproduction tests
    ├── test_preservation.py    # Fixture verification & restart persistence
    ├── test_improvement.py     # Overdue & rematching feature tests
    ├── test_edge_cases.py      # Whitespace, BOM, overpayment tests
    └── test_smoke.py           # Starter smoke tests
```
