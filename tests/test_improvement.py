import tempfile
import unittest
from datetime import date
from pathlib import Path
from ledger import storage, reporting


class OverdueTrackingImprovementTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = storage.connect(Path(self.tmp.name) / 'test_improvement.sqlite3')
        storage.seed(self.db)
        # In seed data:
        # INV-100: due 2026-09-01, balance 1250.00 (open)
        # INV-200: due 2026-09-02, balance 1250.00 (open)
        # INV-300: due 2026-09-03, balance 9.99 (open)
        # INV-101: due 2026-09-04, balance 0.00 (paid)
        # INV-201: due 2026-09-05, balance 600.00 (open)
        # INV-301: due 2026-09-06, balance 100.00 (open)

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_overdue_detection_and_aging_calculation(self):
        """Test overdue flag and days overdue calculation as of 2026-09-04."""
        as_of = date(2026, 9, 4)
        invoices = reporting.invoices(self.db, as_of=as_of)
        inv_map = {r['invoice_number']: r for r in invoices}

        # INV-100 (due 2026-09-01): 3 days overdue
        self.assertTrue(inv_map['INV-100']['is_overdue'])
        self.assertEqual(inv_map['INV-100']['days_overdue'], 3)

        # INV-200 (due 2026-09-02): 2 days overdue
        self.assertTrue(inv_map['INV-200']['is_overdue'])
        self.assertEqual(inv_map['INV-200']['days_overdue'], 2)

        # INV-300 (due 2026-09-03): 1 day overdue
        self.assertTrue(inv_map['INV-300']['is_overdue'])
        self.assertEqual(inv_map['INV-300']['days_overdue'], 1)

        # INV-101 (due 2026-09-04, paid): not overdue because balance is 0
        self.assertFalse(inv_map['INV-101']['is_overdue'])
        self.assertEqual(inv_map['INV-101']['days_overdue'], 0)

        # INV-201 (due 2026-09-05, future): not overdue
        self.assertFalse(inv_map['INV-201']['is_overdue'])
        self.assertEqual(inv_map['INV-201']['days_overdue'], 0)

    def test_overdue_filtering_and_summary(self):
        """Test status=overdue filter and summary metrics in overview."""
        as_of = date(2026, 9, 4)
        overdue_invoices = reporting.invoices(self.db, status='overdue', as_of=as_of)
        # As of Sep 4, overdue are INV-100, INV-200, INV-300
        self.assertEqual(len(overdue_invoices), 3)
        self.assertEqual({r['invoice_number'] for r in overdue_invoices}, {'INV-100', 'INV-200', 'INV-300'})

        ov = reporting.overview(self.db, as_of=as_of)
        summary = ov['summary']
        self.assertEqual(summary['overdue_count'], 3)
        # Overdue balance sum: 1250.00 + 1250.00 + 9.99 = 2509.99
        self.assertEqual(summary['overdue_amount'], 2509.99)
        # Existing summary invariants untouched
        self.assertEqual(summary['invoice_count'], 6)
        self.assertEqual(summary['open_count'], 5)
        self.assertEqual(summary['outstanding'], 3209.99)


    def test_rematch_unmatched_payments(self):
        """Test re-allocating an unmatched payment when matching invoice is subsequently imported."""
        from ledger import importing, matching
        # Import an unmatched payment for MAPLE / WAIT-900 (does not exist yet)
        pay_csv = "payment_id,customer_id,invoice_number,amount\nPAY-WAIT,MAPLE,WAIT-900,100.00\n"
        importing.import_csv(self.db, pay_csv, 'payments')
        
        # Verify it's initially unmatched
        ov1 = reporting.overview(self.db)
        unmatched_pids = [p['payment_id'] for p in ov1['unmatched_payments']]
        self.assertIn('PAY-WAIT', unmatched_pids)
        
        # Now import the missing invoice MAPLE / WAIT-900 (amount 150.00)
        inv_csv = "customer_id,invoice_number,amount,due_date\nMAPLE,WAIT-900,150.00,2026-09-20\n"
        importing.import_csv(self.db, inv_csv, 'invoices')
        
        # Trigger rematch
        matched = matching.rematch_unmatched(self.db)
        self.assertGreaterEqual(matched, 1)
        
        # Verify PAY-WAIT is no longer unmatched and WAIT-900 has balance 50.00
        ov2 = reporting.overview(self.db)
        unmatched_pids_after = [p['payment_id'] for p in ov2['unmatched_payments']]
        self.assertNotIn('PAY-WAIT', unmatched_pids_after)
        
        inv = next(r for r in ov2['invoices'] if r['invoice_number'] == 'WAIT-900')
        self.assertEqual(inv['paid'], 100.00)
        self.assertEqual(inv['balance'], 50.00)


if __name__ == '__main__':
    unittest.main()
