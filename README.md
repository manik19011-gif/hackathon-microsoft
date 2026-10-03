# InvoiceCompliance.AI — Enterprise AP Exception Pile & Anti-Fraud Suite

> **Microsoft Hackathon Submission — Challenge #16: The Accounts-Payable Exception Pile**  
> *Autonomous Triage, Forensic Rule Engine, Matched Record Citations & Immutable Audit Logging*

---

## 🌟 Executive Summary

In enterprise Accounts Payable (AP), companies process thousands of invoices monthly. Human AP sampling only catches 5-10% of errors, allowing **duplicates, unitemized missing details, split structuring, and over-limit claims** to slip through and cost millions in financial leakage.

**InvoiceCompliance.AI** solves Challenge #16 with an enterprise-grade automated triage engine that:
1. **Auto-Passes Clean Claims**: Verifies clean invoices with 100% confidence, auto-clearing ~90% of routine claims without human bottleneck.
2. **Routes Only Exceptions**: Traps low-confidence, high-risk, and non-compliant claims in **The AP Exception Pile** for human auditor review.
3. **Cites Matched Records**: Makes every flag fully explainable by citing exact matching transaction IDs, amounts, dates, and similarity scores.
4. **Maintains Immutable Audit Logs**: Records every system auto-pass and human auditor decision for SOX Section 404 and GAAP compliance.

---

## 🚀 Key Features

* **Multi-Layer Compliance & Forensic Rules Engine**:
  * Mandatory AP Schema Checks (`vendor_name`, `amount`, `invoice_date`, `invoice_id`).
  * Global & Category-Specific Spend Ceilings (`meals`, `travel`, `supplies`, `software`).
  * **RapidFuzz** Fuzzy Duplicate Matcher (token-sort ratio catching typos and naming variations).
  * Rolling Temporal Window Split Structuring Detector (identifies multi-invoice evasion below approval limits).
  * Sanctions & High-Risk Entity Watchlist Screening (OFAC SDN & shell company checks).
  * Benford's Law First-Digit Statistical Distribution Screening (forensic accounting logarithmic conformity).
  * Round-Number Forensic Anomaly Check ($500/$1k exact round multiples in discretionary categories).
  * Multi-Currency Normalization (USD, EUR, GBP, JPY, INR, CAD, AUD, CHF FX conversion).
* **Document OCR & Math Reconciliation**:
  * PDF and receipt text parsing with automated field extraction.
  * Mathematical line-item reconciliation (`Subtotal + Tax == Total Amount`).
* **Interactive AP Exception Short Report (`/ap-exception-report`)**:
  * Generates instant executive briefs summarizing portfolio health, auto-pass rate, and itemized flagged issues.
* **Grounded Compliance AI Copilot (`/ask-ai`)**:
  * Natural language Q&A assistant grounded directly in live SQLite database records.
* **Interactive Hackathon Judge Tour**:
  * 1-click 5-step guided demonstration designed for hackathon judges to verify all features in under 60 seconds.

---

## 🛠️ Tech Stack

* **Backend**: Python 3.14 / FastAPI, Pydantic V2, SQLite, RapidFuzz, Pandas, PyPDF, Uvicorn
* **Frontend**: Vanilla HTML5/JS (Single-page app), Tailwind CSS (CDN), Lucide Vector Icons, Chart.js 4+
* **Testing**: Pytest (25 passing unit & integration tests)

---

## ⚡ Quick Start & Installation

### 1. Prerequisites
* Python 3.10+ (tested on Python 3.14)

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Automated Test Suite
```bash
pytest backend/tests/ -v
```
*(All 25 tests should pass with 100% success).*

### 4. Start the Application Server
```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### 5. Access the Web Application
Open your browser to:
* **Web Application**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
* **Interactive Swagger API Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **AP Exception Short Report Endpoint**: [http://127.0.0.1:8000/ap-exception-report](http://127.0.0.1:8000/ap-exception-report)

---

## 📂 Project Architecture

```
├── backend/
│   ├── main.py                     # FastAPI server, endpoints & triage orchestration
│   ├── database/
│   │   ├── db.py                   # SQLite schema, migrations & SOX audit log service
│   │   └── invoice_checker.db      # Live transactional SQLite database
│   ├── services/
│   │   ├── rule_engine.py          # 7-layer compliance & forensic rules engine
│   │   ├── duplicate_detector.py   # Exact and RapidFuzz typo duplicate matching
│   │   ├── split_detector.py       # Rolling temporal window structuring detection
│   │   ├── watchlist.py            # Sanctions and high-risk counterparty screening
│   │   ├── currency.py             # Multi-currency detection and FX normalization
│   │   ├── document_parser.py      # PDF text extraction and math reconciliation
│   │   ├── benford.py              # Benford's Law logarithmic distribution screening
│   │   ├── vendor_analytics.py     # Counterparty risk profiling & metrics
│   │   ├── profiler.py             # Dataset hygiene and missing values profiling
│   │   ├── ai_copilot.py           # Grounded natural language Q&A assistant
│   │   └── data_loader.py          # Multi-alias CSV/Excel dataset ingestion
│   └── tests/
│       └── test_compliance.py      # 25 automated unit and integration tests
├── frontend/
│   └── index.html                  # Responsive enterprise UI with Judge Tour & Command Palette
├── requirements.txt                # Pinned production dependencies
└── README.md                       # Project documentation & hackathon submission brief
```

---

## 🏆 Problem Statement Alignment Checklist

| Challenge #16 Requirement | Implementation in InvoiceCompliance.AI | Verified |
|---|---|:---:|
| **Check invoices against limits, required fields, duplicates** | Comprehensive rule engine checking limits, schema fields, and RapidFuzz fuzzy duplicates | ✅ |
| **Send only exception rows to human — auto-pass clean ones** | Clean invoices assigned `decision_status = 'AUTO_PASSED'`; violations sent to `IN_EXCEPTION_PILE` | ✅ |
| **Make each flag explainable by citing matched record** | All duplicates and split flags cite historical invoice IDs, vendors, amounts, and dates | ✅ |
| **Keep an audit log of every decision** | Every system auto-pass and human auditor action recorded in immutable `audit_logs` table | ✅ |
| **Flags anything wrong with a short report** | Dedicated `GET /ap-exception-report` endpoint & in-app printable AP Exception brief | ✅ |
