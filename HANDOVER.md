# Handover

- **Name**: Adarsh Pradeep
- **Email used for this application**: adarsh.pradeep.dev@gmail.com
- **Chosen track**: Track A (Repair the register)
- **Why this track**: I enjoy auditing transactional logic, solving monetary precision and idempotency defects, and building reliable financial register software.
- **Approximate total time, including setup and handover**: ~120 minutes

## Run and verify

Requires Python 3.10 or newer (Standard Library only; zero third-party dependencies).

Run all automated unit and regression tests:
```bash
python -m unittest discover -s tests -v
```

Expected test output:
```text
test_defect_1_row_level_import_error_isolation (test_defects.DefectReproductionTests) ... ok
test_defect_2_duplicate_and_conflicting_invoice_import (test_defects.DefectReproductionTests) ... ok
test_defect_3_payment_matching_strict_customer_and_invoice (test_defects.DefectReproductionTests) ... ok
test_defect_4_open_and_paid_invoice_filtering (test_defects.DefectReproductionTests) ... ok
test_defect_5_export_csv_monetary_precision (test_defects.DefectReproductionTests) ... ok
test_invalid_header_rejection (test_edge_cases.EdgeCaseAndBusinessRuleTests) ... ok
test_overpayment_handling (test_edge_cases.EdgeCaseAndBusinessRuleTests) ... ok
test_valid_header_empty_rows (test_edge_cases.EdgeCaseAndBusinessRuleTests) ... ok
test_whitespace_trimming_and_utf8_bom (test_edge_cases.EdgeCaseAndBusinessRuleTests) ... ok
test_overdue_detection_and_aging_calculation (test_improvement.OverdueTrackingImprovementTests) ... ok
test_overdue_filtering_and_summary (test_improvement.OverdueTrackingImprovementTests) ... ok
test_rematch_unmatched_payments (test_improvement.OverdueTrackingImprovementTests) ... ok
test_existing_register_initial_state (test_preservation.PreservationTests) ... ok
test_new_imports_and_persistence_across_restart (test_preservation.PreservationTests) ... ok
test_export_has_header (test_smoke.SmokeTests) ... ok
test_one_valid_invoice (test_smoke.SmokeTests) ... ok
test_payment_reference_when_amount_is_unique (test_smoke.SmokeTests) ... ok
test_seed_is_repeatable (test_smoke.SmokeTests) ... ok
test_seed_summary (test_smoke.SmokeTests) ... ok

----------------------------------------------------------------------
Ran 19 tests in 0.442s

OK
```

Restore the owner's register fixture and start the local server:
```bash
python restore_fixture.py --replace
python app.py
```
Open `http://127.0.0.1:8787` in a web browser.

## What I delivered

Investigated and resolved the six seeded defects, verified historical database preservation, and implemented two functional financial accounting improvements beyond visual polish:

1. **Row-level CSV Import Isolation** ([`ledger/importing.py`](ledger/importing.py)): Fixed fail-fast list comprehension that aborted entire imports when any single row had bad data. Invalid rows are now rejected independently with line numbers and reasons while valid rows process successfully.
2. **Invoice Idempotency & Duplicate Prevention** ([`ledger/storage.py`](ledger/storage.py)): Added checks before insertion. Identical re-imports are skipped without altering totals; re-imports with conflicting amounts or due dates are rejected.
3. **Strict Payment Matching** ([`ledger/matching.py`](ledger/matching.py)): Removed greedy amount-based matching. Payments attach only when both `customer_id` and `invoice_number` match an existing invoice. Otherwise, they remain unmatched.
4. **Status Filter Logic** ([`ledger/reporting.py`](ledger/reporting.py)): Fixed inverted filter dictionary where `status=open` was returning paid invoices.
5. **CSV Export Decimal Precision** ([`ledger/reporting.py`](ledger/reporting.py)): Replaced integer-truncating float calculation (`int(val * 100) / 100`) with standard 2-decimal string formatting (`f"{val:.2f}"`), fixing cents loss (e.g. `19.99` no longer exports as `19.98`).
6. **Frontend Feedback & Error Reporting** ([`web/app.js`](web/app.js)): Checked `response.ok`, parsed JSON count fields (`imported`, `skipped`, `rejected`), and rendered line error messages instead of falsely reporting success on errors.
7. **Improvement 1 — Overdue Invoice Aging & Days Overdue Tracking**:
   - *Owner Problem Solved*: The owner had no visibility into which open balances were past due date vs. current.
   - *Implementation*: Backend dynamically computes `is_overdue` and `days_overdue` based on `due_date`, adds `overdue_count` and `overdue_amount` to `/api/overview`, and enables `status=overdue` API filter. Tested in `test_overdue_detection_and_aging_calculation` and `test_overdue_filtering_and_summary`.
8. **Improvement 2 — Unmatched Payment Resolution & Re-allocation API**:
   - *Owner Problem Solved*: Payments imported before their corresponding invoice exists (e.g. `KEEP-U1` for MAPLE / WAIT-900) were stranded as unmatched forever, even after the missing invoice was later imported.
   - *Implementation*: Added `rematch_unmatched(db)` and `POST /api/rematch` endpoint that scans unmatched payments and automatically links them to matching invoices when they arrive, updating invoice balances. Tested in `test_rematch_unmatched_payments`.

## Evidence and limits

- **Failing-before / passing-after reproduction**: [`tests/test_defects.py`](tests/test_defects.py) explicitly reproduces the seeded bugs. Before fixes, 5 tests failed (batch import crash, duplicate insertions, misallocated payments, inverted open filter, float truncation). All 19 tests in the suite now pass.
- **Existing-register check**: [`tests/test_preservation.py`](tests/test_preservation.py) restores `fixtures/existing-register.sqlite3` and verifies the starting state (9 invoices, 5 payments, 7 open, 1 unmatched `KEEP-U1`, total outstanding INR 3,698.19). It verifies that new valid imports work on top of the register and survive server restarts.
- **Changed-input edge case**: [`tests/test_edge_cases.py`](tests/test_edge_cases.py) verifies UTF-8 BOM stripping, whitespace trimming, empty CSV inputs, and overpayments (overpaid invoices display negative balances and marked paid without reducing other invoice balances).
- **Limits & Real-project next steps**: Historical payment allocations were preserved per scope. In a production system, I would add DB-level transaction locks, an audit log for payment re-allocations, and manual payment-to-invoice re-linking capabilities for unmatched payments.

## Tools and judgment

1. **Schema Constraint vs. Storage Check**: An AI coding assistant suggested adding a `UNIQUE(customer_id, invoice_number)` constraint to the SQLite schema DDL. I decided against modifying the SQLite DDL schema because it would require running DDL migrations against the existing database fixture; instead, I implemented the idempotency check at the Python storage layer (`invoice_by_key`), maintaining 100% compatibility with existing SQLite files.
2. **Float Precision Verification**: After modifying CSV export, I wrote explicit unit assertions matching values like `19.99` and `9.99` to ensure standard IEEE-754 floating-point inaccuracies did not reappear.
3. **Verification Method**: Used `unittest` discover for rapid regression testing and verified the web UI through local browser runs.
