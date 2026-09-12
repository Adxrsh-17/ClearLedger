# ClearLedger

> **ClearLedger** is a lightweight, zero-dependency local financial register application for tracking customer invoices, payment allocations, outstanding balances, and overdue aging metrics.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-19%20Passing-brightgreen.svg)]()

---

## 🌟 Key Features

- 📑 **Invoice & Payment Register**: Track customer invoices, paid amounts, remaining balances, and status (`open`, `paid`, `overdue`).
- ⏳ **Overdue Aging Tracking**: Automated overdue detection and days past due (`days_overdue`) calculation with color-coded status badges.
- 👥 **Customer Summary Breakdown**: Aggregate total invoiced, total paid, outstanding debt, and open items per customer.
- ⚡ **Instant Live Search**: Client-side filtering across customer names, customer IDs, and invoice numbers.
- 📥 **CSV Bulk Imports**: Row-level error isolation supporting UTF-8 BOM, whitespace trimming, and line-numbered rejection reasons.
- 🔄 **Idempotent Storage & Strict Matching**: Prevents duplicate insertions, rejects conflicting record modifications, and enforces strict `(customer_id, invoice_number)` payment matching.
- 🔗 **Unmatched Payment Resolution**: Automated re-matching endpoint (`POST /api/rematch`) to link orphaned payments when missing invoices arrive.
- 📊 **CSV Report Exports**: Accurate monetary exports to 2 decimal places preserving exact cent balances.

---

## 🛠️ Tech Stack & Architecture

- **Backend**: Python 3.10+ (Standard Library only: `sqlite3`, `http.server`, `csv`, `json`, `unittest`). Zero external pip dependencies required.
- **Frontend**: Vanilla HTML5, CSS3 (Inter font, responsive Fintech design system), and JavaScript (Fetch API).
- **Database**: SQLite3 (`PRAGMA foreign_keys = ON`).

---

## 🚀 Quick Start & Installation

### Prerequisites
- Python 3.10 or higher.
- A modern web browser.

### Setup Instructions

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/Adxrsh-17/ClearLedger.git
   cd ClearLedger
   ```

2. **Restore Fixture Database**:
   ```bash
   python restore_fixture.py --replace
   ```

3. **Start the Web Application**:
   ```bash
   python app.py
   ```

4. **Access the Dashboard**:
   Open **`http://127.0.0.1:8787`** in your browser.

---

## 🧪 Testing & Verification

Run the full automated unittest suite (19 passing unit, regression, and edge-case checks):

```bash
python -m unittest discover -s tests -v
```

### Test Suite Structure
- `tests/test_defects.py`: Core bug fixes & regression checks.
- `tests/test_preservation.py`: Historical database fixture verification and restart persistence.
- `tests/test_improvement.py`: Overdue aging calculation and payment re-matching features.
- `tests/test_edge_cases.py`: UTF-8 BOM, whitespace trimming, empty inputs, and overpayments.
- `tests/test_smoke.py`: Starter setup checks.

---

## 🔌 API Documentation

| Endpoint | Method | Description |
|---|---|---|
| `GET /api/overview` | `GET` | Returns summary metrics (`invoice_count`, `open_count`, `outstanding`, `overdue_count`, `overdue_amount`), customer summary breakdown, all invoices, and unmatched payments. |
| `GET /api/invoices?status={all\|open\|paid\|overdue}` | `GET` | Returns filtered array of invoice objects. |
| `GET /api/export` | `GET` | Downloads CSV export of all invoices formatted to 2 decimal places. |
| `POST /api/import?kind={invoices\|payments}` | `POST` | Accepts raw CSV text. Returns JSON object with `imported`, `skipped`, `rejected` counts and line `errors`. |
| `POST /api/rematch` | `POST` | Triggers re-check of unmatched payments to link them to newly created matching invoices. |

---

## 📁 Directory Structure

```
ClearLedger/
├── app.py                      # Application server entry point
├── restore_fixture.py          # Database restoration utility
├── HANDOVER.md                 # Technical handover & assessment verification notes
├── STARTER_GUIDE.md            # Quick reference guide
├── BUSINESS_RULES.md           # Business domain specification & invariants
├── fixtures/
│   ├── existing-register.sqlite3 # Synthetic historical database
│   └── expected-records.json     # Reference baseline data
├── ledger/
│   ├── importing.py            # CSV parsing & row isolation
│   ├── storage.py              # SQLite storage & idempotency logic
│   ├── matching.py             # Payment matching & re-allocation engine
│   ├── reporting.py            # Overview calculations & CSV export
│   ├── validation.py           # Data normalization & regex validation
│   └── http_app.py             # HTTP router & API handlers
├── web/
│   ├── index.html              # Dashboard layout
│   ├── app.js                  # Frontend client logic & live search
│   └── style.css               # Modern Fintech stylesheet & badges
└── tests/                      # Automated unit test suite
```

---

## 👨‍💻 Author

**Adarsh Pradeep**  
- GitHub: [@Adxrsh-17](https://github.com/Adxrsh-17)  
- Email: adarssshhhh17@gmail.com  
