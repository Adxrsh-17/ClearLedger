import json
import shutil
import tempfile
import unittest
from pathlib import Path
from ledger import storage, reporting, importing

ROOT = Path(__file__).resolve().parent.parent


class PreservationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / 'preserved.sqlite3'
        fixture_source = ROOT / 'fixtures' / 'existing-register.sqlite3'
        shutil.copy2(fixture_source, self.db_path)
        self.db = storage.connect(self.db_path)

        with open(ROOT / 'fixtures' / 'expected-records.json', 'r', encoding='utf-8') as f:
            self.expected = json.load(f)

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_existing_register_initial_state(self):
        """Verify the restored fixture matches expected-records.json exactly."""
        ov = reporting.overview(self.db)
        summary = ov['summary']
        self.assertEqual(summary['invoice_count'], 9)
        self.assertEqual(summary['open_count'], 7)
        self.assertEqual(summary['outstanding'], 3698.19)

        # Invoices check
        invoices = reporting.invoices(self.db)
        self.assertEqual(len(invoices), 9)

        # Check specific fixture records
        inv_map = {(r['customer_id'], r['invoice_number']): r for r in invoices}
        self.assertIn(('HARBOR', 'KEEP-700'), inv_map)
        self.assertEqual(inv_map[('HARBOR', 'KEEP-700')]['amount'], 456.78)
        self.assertEqual(inv_map[('HARBOR', 'KEEP-700')]['paid'], 56.78)
        self.assertEqual(inv_map[('HARBOR', 'KEEP-700')]['balance'], 400.00)
        self.assertEqual(inv_map[('HARBOR', 'KEEP-700')]['status'], 'open')

        self.assertIn(('MAPLE', 'KEEP-700'), inv_map)
        self.assertEqual(inv_map[('MAPLE', 'KEEP-700')]['balance'], 88.20)
        self.assertEqual(inv_map[('MAPLE', 'KEEP-700')]['status'], 'open')

        self.assertIn(('NORTH', 'KEEP-702'), inv_map)
        self.assertEqual(inv_map[('NORTH', 'KEEP-702')]['paid'], 150.00)
        self.assertEqual(inv_map[('NORTH', 'KEEP-702')]['balance'], 0.00)
        self.assertEqual(inv_map[('NORTH', 'KEEP-702')]['status'], 'paid')

        # Check unmatched payments
        unmatched = ov['unmatched_payments']
        self.assertEqual(len(unmatched), 1)
        self.assertEqual(unmatched[0]['payment_id'], 'KEEP-U1')
        self.assertEqual(unmatched[0]['amount'], 33.33)

    def test_new_imports_and_persistence_across_restart(self):
        """Verify importing new invoice and payment on top of fixture, and persisting across restart."""
        # Import new invoice
        new_inv_csv = "customer_id,invoice_number,amount,due_date\nMAPLE,NEW-800,200.00,2026-09-20\n"
        res_inv = importing.import_csv(self.db, new_inv_csv, 'invoices')
        self.assertEqual(res_inv['imported'], 1)

        # Import new payment for this new invoice
        new_pay_csv = "payment_id,customer_id,invoice_number,amount\nNEW-P1,MAPLE,NEW-800,50.00\n"
        res_pay = importing.import_csv(self.db, new_pay_csv, 'payments')
        self.assertEqual(res_pay['imported'], 1)

        # Check state before restart
        ov_before = reporting.overview(self.db)
        self.assertEqual(ov_before['summary']['invoice_count'], 10)
        self.assertEqual(ov_before['summary']['open_count'], 8)
        self.assertEqual(ov_before['summary']['outstanding'], 3848.19)  # 3698.19 + (200 - 50) = 3848.19

        # Simulate app restart
        self.db.close()
        self.db = storage.connect(self.db_path)

        # Verify all records persist after restart
        ov_after = reporting.overview(self.db)
        self.assertEqual(ov_after['summary']['invoice_count'], 10)
        self.assertEqual(ov_after['summary']['open_count'], 8)
        self.assertEqual(ov_after['summary']['outstanding'], 3848.19)

        # Verify KEEP-U1 remains unmatched
        self.assertEqual(len(ov_after['unmatched_payments']), 1)
        self.assertEqual(ov_after['unmatched_payments'][0]['payment_id'], 'KEEP-U1')


if __name__ == '__main__':
    unittest.main()
