import tempfile
import unittest
from pathlib import Path
from ledger import storage, reporting, importing


class DefectReproductionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / 'test.sqlite3'
        self.db = storage.connect(self.db_path)
        storage.seed(self.db)

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_defect_1_row_level_import_error_isolation(self):
        """Defect 1: An invalid data row should only reject that row, processing other valid rows.
        Currently fails because list comprehension crashes on the first invalid row."""
        csv_data = (
            "customer_id,invoice_number,amount,due_date\n"
            "HARBOR,INV-GOOD-1,100.00,2026-09-01\n"
            "HARBOR,INV-BAD-2,invalid_amount,2026-09-02\n"
            "HARBOR,INV-GOOD-3,200.00,2026-09-03\n"
        )
        result = importing.import_csv(self.db, csv_data, 'invoices')
        self.assertEqual(result['imported'], 2, "Valid rows should be imported")
        self.assertEqual(result['rejected'], 1, "Invalid row should be rejected")
        self.assertEqual(len(result['errors']), 1)
        self.assertEqual(result['errors'][0]['line'], 3, "Header is line 1, second data row is line 3")

    def test_defect_2_duplicate_and_conflicting_invoice_import(self):
        """Defect 2: Re-importing an identical invoice must skip it; conflicting details must reject it.
        Currently fails because duplicates are inserted unconditionally into invoices table."""
        # HARBOR / INV-100 is seeded with 1250.00, 2026-09-01
        identical_csv = (
            "customer_id,invoice_number,amount,due_date\n"
            "HARBOR,INV-100,1250.00,2026-09-01\n"
        )
        res_skip = importing.import_csv(self.db, identical_csv, 'invoices')
        self.assertEqual(res_skip['skipped'], 1, "Identical re-import should be skipped")
        self.assertEqual(res_skip['imported'], 0)
        # Check count is still 6
        self.assertEqual(len(reporting.invoices(self.db)), 6, "Total invoice count must not increase on duplicate")

        # Conflicting re-import (different amount)
        conflicting_csv = (
            "customer_id,invoice_number,amount,due_date\n"
            "HARBOR,INV-100,9999.00,2026-09-01\n"
        )
        res_reject = importing.import_csv(self.db, conflicting_csv, 'invoices')
        self.assertEqual(res_reject['rejected'], 1, "Conflicting invoice details must be rejected")
        # Ensure original record preserved
        inv = storage.invoice_by_key(self.db, 'HARBOR', 'INV-100')
        self.assertEqual(inv['amount'], 1250.00)

    def test_defect_3_payment_matching_strict_customer_and_invoice(self):
        """Defect 3: Payments must attach ONLY to matching customer_id and invoice_number.
        Currently fails because find_invoice matches greedily by amount alone."""
        # MAPLE / WAIT-900 does not exist, but amount 1250.00 matches HARBOR / INV-100 and MAPLE / INV-200.
        # It must NOT attach to HARBOR / INV-100 or MAPLE / INV-200; it must remain unmatched.
        csv_data = (
            "payment_id,customer_id,invoice_number,amount\n"
            "PAY-UNMATCHED,MAPLE,WAIT-900,1250.00\n"
        )
        result = importing.import_csv(self.db, csv_data, 'payments')
        self.assertEqual(result['imported'], 1)

        # Check that WAIT-900 is in unmatched payments
        ov = reporting.overview(self.db)
        unmatched_ids = [p['payment_id'] for p in ov['unmatched_payments']]
        self.assertIn('PAY-UNMATCHED', unmatched_ids, "Payment for non-existent invoice must remain unmatched")

        # Check HARBOR / INV-100 was not credited
        inv_100 = next(r for r in ov['invoices'] if r['customer_id'] == 'HARBOR' and r['invoice_number'] == 'INV-100')
        self.assertEqual(inv_100['paid'], 0.0, "HARBOR INV-100 should have 0 paid")

    def test_defect_4_open_and_paid_invoice_filtering(self):
        """Defect 4: GET /api/invoices?status=open must return open invoices (balance > 0).
        Currently fails because reporting.invoices maps 'open' -> 'paid'."""
        open_invoices = reporting.invoices(self.db, status='open')
        # In seed: 6 invoices, INV-101 (300 amount, 300 paid) is paid. Remaining 5 are open.
        self.assertEqual(len(open_invoices), 5, "Seed should have 5 open invoices")
        for inv in open_invoices:
            self.assertEqual(inv['status'], 'open')
            self.assertGreater(inv['balance'], 0)

        paid_invoices = reporting.invoices(self.db, status='paid')
        self.assertEqual(len(paid_invoices), 1, "Seed should have 1 paid invoice (INV-101)")
        self.assertEqual(paid_invoices[0]['invoice_number'], 'INV-101')
        self.assertEqual(paid_invoices[0]['status'], 'paid')

    def test_defect_5_export_csv_monetary_precision(self):
        """Defect 5: CSV export must accurately format amounts to 2 decimal places without float truncation.
        Currently fails on values like 19.99 or 9.99 which get truncated to 19.98 / 9.98."""
        csv_text = reporting.export_csv(self.db)
        # In seed: NORTH INV-300 has amount 19.99, paid 10.00, balance 9.99
        self.assertIn("NORTH,INV-300,19.99,10.00,9.99,open", csv_text)


if __name__ == '__main__':
    unittest.main()
