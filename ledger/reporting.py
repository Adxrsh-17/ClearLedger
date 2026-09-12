import csv
import io


from datetime import date


def invoices(db, status='all', as_of=None):
    if status not in ('all', 'open', 'paid', 'overdue'):
        raise ValueError('status must be all, open, paid or overdue')
    ref_date = as_of or date.today()
    data = db.execute('''
        SELECT i.id, i.customer_id, c.name AS customer_name, i.invoice_number,
               i.amount, i.due_date, COALESCE(SUM(p.amount), 0) AS paid
        FROM invoices i JOIN customers c ON c.customer_id=i.customer_id
        LEFT JOIN payments p ON p.invoice_id=i.id
        GROUP BY i.id ORDER BY i.id
    ''').fetchall()
    result = []
    for row in data:
        item = dict(row)
        item['amount'] = round(float(item['amount']), 2)
        item['paid'] = round(float(item['paid']), 2)
        item['balance'] = round(item['amount'] - item['paid'], 2)
        item['status'] = 'paid' if item['balance'] <= 0 else 'open'
        try:
            due = date.fromisoformat(item['due_date'])
            diff = (ref_date - due).days
            item['is_overdue'] = bool(item['status'] == 'open' and diff > 0)
            item['days_overdue'] = max(0, diff) if item['is_overdue'] else 0
        except (ValueError, TypeError):
            item['is_overdue'] = False
            item['days_overdue'] = 0
        result.append(item)
    if status == 'overdue':
        result = [r for r in result if r['is_overdue']]
    elif status != 'all':
        result = [r for r in result if r['status'] == status]
    return result


def overview(db, as_of=None):
    rows = invoices(db, as_of=as_of)
    unmatched = [dict(r) for r in db.execute('''SELECT payment_id, customer_id,
        invoice_number, amount FROM payments WHERE invoice_id IS NULL ORDER BY payment_id''')]
    overdue_rows = [r for r in rows if r.get('is_overdue')]

    customers_data = db.execute('SELECT customer_id, name FROM customers ORDER BY customer_id').fetchall()
    customer_breakdown = []
    for c in customers_data:
        cid = c['customer_id']
        c_invoices = [r for r in rows if r['customer_id'] == cid]
        tot_inv = sum(r['amount'] for r in c_invoices)
        tot_paid = sum(r['paid'] for r in c_invoices)
        tot_out = sum(max(0, r['balance']) for r in c_invoices)
        open_cnt = sum(r['status'] == 'open' for r in c_invoices)
        customer_breakdown.append({
            'customer_id': cid,
            'name': c['name'],
            'total_invoiced': round(tot_inv, 2),
            'total_paid': round(tot_paid, 2),
            'outstanding': round(tot_out, 2),
            'open_count': open_cnt,
        })

    return {'invoices': rows, 'unmatched_payments': unmatched, 'customers': customer_breakdown, 'summary': {
        'invoice_count': len(rows),
        'open_count': sum(r['status'] == 'open' for r in rows),
        'outstanding': round(sum(max(0, r['balance']) for r in rows), 2),
        'overdue_count': len(overdue_rows),
        'overdue_amount': round(sum(r['balance'] for r in overdue_rows), 2),
    }}


def export_csv(db):
    output = io.StringIO(newline='')
    fields = ['customer_id', 'invoice_number', 'amount', 'paid', 'balance', 'status']
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for row in invoices(db):
        item = {k: row[k] for k in fields}
        for key in ('amount', 'paid', 'balance'):
            item[key] = f"{item[key]:.2f}"
        writer.writerow(item)
    return output.getvalue()
