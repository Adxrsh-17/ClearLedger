from .storage import invoice_by_key


def find_invoice(db, payment):
    exact = invoice_by_key(db, payment['customer_id'], payment['invoice_number'])
    return exact['id'] if exact else None


def rematch_unmatched(db, payment_id=None):
    """Attach unmatched payments to newly created matching invoices."""
    query = 'SELECT * FROM payments WHERE invoice_id IS NULL'
    params = []
    if payment_id:
        query += ' AND payment_id=?'
        params.append(payment_id)
    
    unmatched = db.execute(query, params).fetchall()
    matched_count = 0
    with db:
        for p in unmatched:
            exact = invoice_by_key(db, p['customer_id'], p['invoice_number'])
            if exact:
                db.execute('UPDATE payments SET invoice_id=? WHERE payment_id=?', (exact['id'], p['payment_id']))
                matched_count += 1
    return matched_count
