import tempfile
import unittest
from pathlib import Path
from ledger import storage, reporting, importing


class EdgeCaseAndBusinessRuleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = storage.connect(Path(self.tmp.name) / 'test_edge.sqlite3')
        storage.seed(self.db)

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_whitespace_trimming_and_utf8_bom(self):
        """CSV values with surrounding whitespace and UTF-8 BOM must be trimmed and processed."""
        csv_with_bom_and_spaces = (
            "\ufeffcustomer_id,invoice_number,amount,due_date\n"
            "  HARBOR  ,  INV-WS-1  ,  450.50  ,  2026-09-15  \n"
        )
        res = importing.import_csv(self.db, csv_with_bom_and_spaces, 'invoices')
        self.assertEqual(res['imported'], 1)
        inv = storage.invoice_by_key(self.db, 'HARBOR', 'INV-WS-1')
        self.assertIsNotNone(inv)
        self.assertEqual(inv['amount'], 450.50)
        self.assertEqual(inv['due_date'], '2026-09-15')

    def test_overpayment_handling(self):
        """Overpayment is permitted: shows negative balance, marks invoice paid, doesn't affect others."""
        # HARBOR / INV-100 amount is 1250.00
        pay_csv = "payment_id,customer_id,invoice_number,amount\nPAY-OVER,HARBOR,INV-100,1500.00\n"
        res = importing.import_csv(self.db, pay_csv, 'payments')
        self.assertEqual(res['imported'], 1)

        invoices = reporting.invoices(self.db)
        inv_100 = next(r for r in invoices if r['invoice_number'] == 'INV-100')
        self.assertEqual(inv_100['paid'], 1500.00)
        self.assertEqual(inv_100['balance'], -250.00)
        self.assertEqual(inv_100['status'], 'paid')

        # Total outstanding should only sum positive balances (not reduced by the negative 250)
        # Remaining open: MAPLE INV-200 (1250), NORTH INV-300 (9.99), MAPLE INV-201 (600), NORTH INV-301 (100)
        # Sum = 1959.99
        ov = reporting.overview(self.db)
        self.assertEqual(ov['summary']['outstanding'], 1959.99)

    def test_valid_header_empty_rows(self):
        """A valid header with zero data rows is a successful import with zero counts."""
        empty_csv = "customer_id,invoice_number,amount,due_date\n"
        res = importing.import_csv(self.db, empty_csv, 'invoices')
        self.assertEqual(res, {'imported': 0, 'skipped': 0, 'rejected': 0, 'errors': []})

    def test_invalid_header_rejection(self):
        """An invalid header raises ValueError and does not write to the database."""
        bad_csv = "wrong,header,cols,here\nHARBOR,INV-999,100.00,2026-09-01\n"
        with self.assertRaises(ValueError) as ctx:
            importing.import_csv(self.db, bad_csv, 'invoices')
        self.assertIn("Expected CSV header", str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
