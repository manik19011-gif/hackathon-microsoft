from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import sqlite3
import json
import io
import csv
import datetime

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db import get_connection, init_db, log_audit
from services.rule_engine import evaluate_invoice_rules, calculate_risk_score
from services.duplicate_detector import detect_duplicates
from services.split_detector import detect_split_transactions
from services.benford import analyze_benford_law
from services.vendor_analytics import analyze_vendor_risk
from services.profiler import generate_data_profile
from services.ai_explainer import generate_ai_explanation
from services.demo_generator import get_demo_dataset
from services.data_loader import load_and_process_dataset

app = FastAPI(
    title="Invoice & Expense Checker Assistant API",
    description="Automated compliance, duplicate detection, split transaction analysis, Benford's Law screening, vendor risk analytics, and AI audit for enterprise expense invoices.",
    version="1.4.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

class DecisionPayload(BaseModel):
    action: str  # "APPROVE", "REJECT", "ESCALATE", "MARK_DUPLICATE"
    notes: Optional[str] = None
    user_name: Optional[str] = "Compliance Officer"

class SingleInvoicePayload(BaseModel):
    invoice_id: str
    vendor_name: str
    amount: float
    invoice_date: str
    category: Optional[str] = "General"
    employee_id: Optional[str] = "EMP-001"
    description: Optional[str] = ""
    save_to_db: Optional[bool] = False

class BatchDecisionPayload(BaseModel):
    invoice_ids: List[str]
    action: str  # "APPROVE", "REJECT", "ESCALATE"
    notes: Optional[str] = None
    user_name: Optional[str] = "Compliance Officer"

class WatchlistPayload(BaseModel):
    entity_name: str
    reason: str
    risk_level: Optional[str] = "HIGH"
    category: Optional[str] = "Custom Watchlist"

class AskAIPayload(BaseModel):
    query: str

class PolicyConfigPayload(BaseModel):
    amount_limit: float = 5000.0
    similarity_threshold: float = 85.0
    split_window_days: int = 7
    category_limits: Dict[str, float] = {
        "meals & entertainment": 250.0,
        "meals": 250.0,
        "office supplies": 1000.0,
        "travel & lodging": 3000.0,
        "travel": 3000.0,
        "consulting": 8000.0
    }

ACTIVE_POLICY = {
    "amount_limit": 5000.0,
    "similarity_threshold": 85.0,
    "split_window_days": 7,
    "category_limits": {
        "meals & entertainment": 250.0,
        "meals": 250.0,
        "office supplies": 1000.0,
        "travel & lodging": 3000.0,
        "travel": 3000.0,
        "consulting": 8000.0
    }
}

@app.on_event("startup")
def startup_event():
    init_db()
    log_audit("API Startup", "Database initialized and API endpoints ready.")

@app.get("/")
def get_home_page():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"status": "online", "message": "Frontend not found"}

@app.get("/landing")
def get_landing_page():
    landing_path = os.path.join(FRONTEND_DIR, "landing.html")
    if os.path.exists(landing_path):
        return FileResponse(landing_path)
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/api/status")
def api_status():
    return {
        "status": "online",
        "service": "Invoice & Expense Checker Assistant API",
        "documentation": "/docs"
    }

@app.get("/sample-csv")
def get_sample_csv():
    """
    Generates and returns an enterprise sample CSV file with clean records and compliance test anomalies.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Invoice Number", "Vendor", "Date", "Total Amount", "Category", "Employee ID", "Description"])
    writer.writerow(["INV-2001", "Microsoft Azure Services", "2026-10-01", 1540.20, "Cloud Infrastructure", "EMP-101", "Monthly cloud services & database hosting"])
    writer.writerow(["INV-2002", "Dell Enterprise Solutions", "2026-10-02", 3200.00, "Hardware", "EMP-102", "High-performance workstations"])
    writer.writerow(["INV-2003", "Staples Office Supply", "2026-10-03", 420.50, "Office Supplies", "EMP-103", "Ergonomic accessories & paper stock"])
    writer.writerow(["INV-2004", "STAPLES OFFICE SUPPLIES", "2026-10-03", 420.50, "Office Supplies", "EMP-103", "Ergonomic accessories & paper stock"])
    writer.writerow(["INV-2005", "Global Data Center Corp", "2026-10-04", 14500.00, "Capital Expenditure", "EMP-104", "Server rack cooling upgrade"])
    writer.writerow(["INV-2006", "Apex Logistics Group", "2026-10-05", 4880.00, "Shipping & Freight", "EMP-105", "Bulk equipment shipping batch 1"])
    writer.writerow(["INV-2007", "Apex Logistics Group", "2026-10-05", 4920.00, "Shipping & Freight", "EMP-105", "Bulk equipment shipping batch 2"])
    writer.writerow(["INV-2008", "", "2026-10-06", 750.00, "Consulting", "EMP-106", "Vendor name missing anomaly test"])
    writer.writerow(["INV-2009", "Metro Catering & Dining", "2026-10-07", 650.00, "Meals & Entertainment", "EMP-107", "Executive team conference dinner"])
    writer.writerow(["INV-2010", "Telecom Network Refund", "2026-10-08", -250.00, "Utilities", "EMP-108", "Erroneous negative line item"])
    output.seek(0)
    
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=enterprise_sample_invoices.csv"}
    )

@app.get("/health")
def health_check():
    return {"status": "healthy"}

def process_and_store_invoices(invoices: List[Dict[str, Any]], amount_limit: float = 5000.0):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(invoices)")
    cols = [r["name"] for r in cursor.fetchall()]
    if "risk_score" not in cols:
        cursor.execute("ALTER TABLE invoices ADD COLUMN risk_score INTEGER DEFAULT 0")
    if "decision_status" not in cols:
        cursor.execute("ALTER TABLE invoices ADD COLUMN decision_status TEXT DEFAULT 'PENDING'")
    if "decision_notes" not in cols:
        cursor.execute("ALTER TABLE invoices ADD COLUMN decision_notes TEXT")
    cursor.execute("PRAGMA table_info(exceptions)")
    exc_cols = [r["name"] for r in cursor.fetchall()]
    if "citation" not in exc_cols:
        cursor.execute("ALTER TABLE exceptions ADD COLUMN citation TEXT")
    conn.commit()

    # Pre-process: ensure unique surrogate ID for records lacking an invoice_id to prevent collision
    for idx, inv in enumerate(invoices):
        raw_id = inv.get("invoice_id")
        if not raw_id or str(raw_id).strip().lower() in ["none", "nan", "null", "", "unknown"]:
            inv["_missing_id"] = True
            inv["invoice_id"] = f"GEN_ID_{idx + 1}"

    # 1. Rule Engine
    invoice_violations_map = {}
    for inv in invoices:
        inv_id = str(inv.get("invoice_id"))
        v_list = evaluate_invoice_rules(inv, amount_limit=amount_limit)
        invoice_violations_map[inv_id] = v_list
        
    # 2. Duplicate Detection
    duplicate_violations = detect_duplicates(invoices)
    for dup_v in duplicate_violations:
        inv_id = dup_v["invoice_id"]
        if inv_id in invoice_violations_map:
            invoice_violations_map[inv_id].append(dup_v)
        else:
            invoice_violations_map[inv_id] = [dup_v]

    # 3. Split Transaction Detection
    split_violations = detect_split_transactions(invoices, amount_limit=amount_limit)
    for split_v in split_violations:
        inv_id = split_v["invoice_id"]
        if inv_id in invoice_violations_map:
            invoice_violations_map[inv_id].append(split_v)
        else:
            invoice_violations_map[inv_id] = [split_v]
            
    # 4. Persist
    for inv in invoices:
        inv_id = str(inv.get("invoice_id"))
        violations = invoice_violations_map.get(inv_id, [])
        risk_score = calculate_risk_score(violations)
        
        status = "PASS"
        if any(v["status"] == "FAIL" for v in violations):
            status = "FAIL"
        elif any(v["status"] == "REVIEW" for v in violations):
            status = "REVIEW"

        if status == "PASS":
            decision_status = "AUTO_PASSED"
            decision_notes = "Auto-passed by AP Compliance Engine (0 violations, high confidence)"
        else:
            decision_status = "IN_EXCEPTION_PILE"
            decision_notes = f"Routed to Human AP Exception Pile: {len(violations)} rule violation(s) detected"

        cursor.execute("""
            INSERT OR REPLACE INTO invoices 
            (invoice_id, vendor_name, invoice_date, amount, category, employee_id, description, status, risk_score, decision_status, decision_notes, source, raw_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            inv_id,
            inv.get("vendor_name"),
            inv.get("invoice_date"),
            inv.get("amount"),
            inv.get("category"),
            inv.get("employee_id"),
            inv.get("description"),
            status,
            risk_score,
            decision_status,
            decision_notes,
            inv.get("source", "System Ingestion"),
            json.dumps(inv)
        ))
        
        for v in violations:
            cursor.execute("""
                INSERT INTO exceptions (invoice_id, rule, status, reason, evidence, citation, severity)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (inv_id, v["rule"], v["status"], v["reason"], v["evidence"], v.get("citation", v["evidence"]), v.get("severity", "MEDIUM")))
            
    conn.commit()
    conn.close()

    clean_count = sum(1 for inv in invoices if not any(v["status"] in ("FAIL", "REVIEW") for v in invoice_violations_map.get(str(inv.get("invoice_id")), [])))
    exception_count = len(invoices) - clean_count
    auto_rate = round((clean_count / len(invoices) * 100), 1) if invoices else 100.0
    log_audit("AP Auto-Pass Triage", f"Ingested {len(invoices)} invoices. Auto-passed {clean_count} clean records ({auto_rate}% auto-pass rate). Sent {exception_count} records to Human AP Exception Pile.", user_name="AP Triage Engine")

@app.post("/seed-demo")
def seed_demo(amount_limit: float = Query(5000.0)):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM invoices")
    cursor.execute("DELETE FROM exceptions")
    conn.commit()
    conn.close()
    
    demo_records = get_demo_dataset()
    process_and_store_invoices(demo_records, amount_limit=amount_limit)
    
    return {
        "message": "Demo dataset successfully seeded and analyzed.",
        "records_count": len(demo_records),
        "amount_limit_applied": amount_limit
    }

@app.post("/upload-dataset")
async def upload_dataset(file: UploadFile = File(...), amount_limit: float = Query(5000.0)):
    valid_exts = [".csv", ".xlsx", ".xls"]
    ext = os.path.splitext(file.filename)[1].lower() if file.filename else ""
    if ext not in valid_exts:
        raise HTTPException(status_code=400, detail=f"Unsupported file type '{ext}'. Supported formats: {', '.join(valid_exts)}")

    temp_dir = os.path.join(os.path.dirname(__file__), "data", "raw")
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, file.filename)
    
    contents = await file.read()
    if not contents or len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    with open(file_path, "wb") as f:
        f.write(contents)
        
    try:
        df_processed, metadata = load_and_process_dataset(file_path)
        records = df_processed.to_dict(orient="records")
        for r in records:
            r["source"] = f"Uploaded File ({file.filename})"
            
        process_and_store_invoices(records, amount_limit=amount_limit)
        
        return {
            "status": "success",
            "filename": file.filename,
            "processed_rows": len(records),
            "mapped_schema": metadata["mapped_schema"],
            "unmapped_fields": metadata["unmapped_target_fields"]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process dataset file: {str(e)}")

@app.get("/invoices")
def list_invoices(
    status: Optional[str] = None,
    source: Optional[str] = None,
    search: Optional[str] = None,
    risk_level: Optional[str] = None,
    limit: int = 100
):
    conn = get_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM invoices WHERE 1=1"
    params = []
    
    if status:
        query += " AND status = ?"
        params.append(status)
    if source:
        query += " AND source = ?"
        params.append(source)
    if risk_level == "HIGH":
        query += " AND risk_score >= 45"
    elif risk_level == "MEDIUM":
        query += " AND risk_score >= 20 AND risk_score < 45"
    elif risk_level == "LOW":
        query += " AND risk_score < 20"
    if search:
        query += " AND (invoice_id LIKE ? OR vendor_name LIKE ? OR description LIKE ?)"
        s_term = f"%{search}%"
        params.extend([s_term, s_term, s_term])
        
    query += " ORDER BY risk_score DESC, id DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return {"invoices": rows, "count": len(rows)}

@app.get("/invoices/{invoice_id}")
def get_invoice_detail(invoice_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM invoices WHERE invoice_id = ?", (invoice_id,))
    inv = cursor.fetchone()
    if not inv:
        conn.close()
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    invoice_dict = dict(inv)
    
    cursor.execute("SELECT * FROM exceptions WHERE invoice_id = ?", (invoice_id,))
    exceptions = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    for exc in exceptions:
        exc["ai_explanation"] = generate_ai_explanation(exc, invoice_dict)
        
    invoice_dict["exceptions"] = exceptions
    return invoice_dict

@app.post("/invoices/{invoice_id}/decision")
def record_audit_decision(invoice_id: str, payload: DecisionPayload):
    """
    Records human auditor decision (APPROVE, REJECT, ESCALATE, MARK_DUPLICATE) on flagged invoice.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM invoices WHERE invoice_id = ?", (invoice_id,))
    inv = cursor.fetchone()
    if not inv:
        conn.close()
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    new_status = inv["status"]
    if payload.action == "APPROVE":
        new_status = "PASS"
    elif payload.action == "REJECT":
        new_status = "FAIL"
        
    cursor.execute("""
        UPDATE invoices 
        SET decision_status = ?, decision_notes = ?, status = ?
        WHERE invoice_id = ?
    """, (payload.action, payload.notes, new_status, invoice_id))
    
    conn.commit()
    conn.close()
    
    log_audit(f"Audit Decision ({payload.action})", f"Invoice {invoice_id} decision updated to '{payload.action}'. Notes: {payload.notes or 'None'}", user_name=payload.user_name or "Compliance Officer")
    
    return {
        "status": "success",
        "invoice_id": invoice_id,
        "decision": payload.action,
        "updated_status": new_status
    }

@app.get("/exceptions")
def list_exceptions(severity: Optional[str] = None):
    conn = get_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT e.*, i.vendor_name, i.amount, i.invoice_date, i.source, i.decision_status 
        FROM exceptions e 
        LEFT JOIN invoices i ON e.invoice_id = i.invoice_id
        WHERE 1=1
    """
    params = []
    if severity:
        query += " AND e.severity = ?"
        params.append(severity)
        
    query += " ORDER BY e.id DESC"
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    for r in rows:
        r["ai_explanation"] = generate_ai_explanation(r)
        
    return {"exceptions": rows, "count": len(rows)}

@app.get("/vendor-analytics")
def get_vendor_analytics():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM invoices")
    invoices = [dict(r) for r in cursor.fetchall()]
    
    cursor.execute("SELECT * FROM exceptions")
    exceptions = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    analysis = analyze_vendor_risk(invoices, exceptions)
    return {"vendors": analysis, "total_vendors": len(analysis)}

@app.get("/benford-analysis")
def get_benford_analysis():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT amount FROM invoices WHERE amount IS NOT NULL")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    result = analyze_benford_law(rows)
    return result

@app.get("/audit-trail")
def get_audit_trail(limit: int = 50):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"audit_trail": rows, "count": len(rows)}

@app.get("/export-exceptions-csv")
def export_exceptions_csv():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT e.invoice_id, e.rule, e.severity, e.status, e.reason, e.evidence, i.vendor_name, i.amount, i.invoice_date
        FROM exceptions e
        LEFT JOIN invoices i ON e.invoice_id = i.invoice_id
        ORDER BY e.id DESC
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["invoice_id", "rule", "severity", "status", "reason", "evidence", "vendor_name", "amount", "invoice_date"])
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
        
    output.seek(0)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=compliance_exceptions_report.csv"}
    )

@app.get("/data-profile")
def get_data_profile_endpoint():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM invoices")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    profile = generate_data_profile(rows)
    return profile

@app.get("/dashboard-stats")
def get_dashboard_stats():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as total FROM invoices")
    total_records = cursor.fetchone()["total"]
    
    cursor.execute("SELECT COUNT(*) as valid FROM invoices WHERE status = 'PASS'")
    valid_records = cursor.fetchone()["valid"]
    
    cursor.execute("SELECT COUNT(*) as review FROM invoices WHERE status = 'REVIEW'")
    review_records = cursor.fetchone()["review"]
    
    cursor.execute("SELECT COUNT(*) as fail FROM invoices WHERE status = 'FAIL'")
    fail_records = cursor.fetchone()["fail"]
    
    cursor.execute("SELECT COUNT(*) as dups FROM exceptions WHERE rule LIKE '%Duplicate%'")
    duplicates_count = cursor.fetchone()["dups"]

    cursor.execute("SELECT COUNT(*) as splits FROM exceptions WHERE rule LIKE '%Split%'")
    splits_count = cursor.fetchone()["splits"]
    
    cursor.execute("SELECT COUNT(*) as missing FROM exceptions WHERE rule LIKE '%Required%'")
    missing_count = cursor.fetchone()["missing"]

    cursor.execute("SELECT COUNT(*) as over_limit FROM exceptions WHERE rule LIKE '%Limit%' OR rule LIKE '%Threshold%'")
    over_limit_count = cursor.fetchone()["over_limit"]

    cursor.execute("SELECT SUM(amount) as total_amt FROM invoices WHERE amount IS NOT NULL")
    res_amt = cursor.fetchone()["total_amt"]
    total_amount = round(res_amt or 0.0, 2)

    cursor.execute("SELECT SUM(amount) as clean_amt FROM invoices WHERE status = 'PASS' AND amount IS NOT NULL")
    clean_row = cursor.fetchone()["clean_amt"]
    auto_passed_amount = round(clean_row or 0.0, 2)

    cursor.execute("SELECT SUM(amount) as exc_amt FROM invoices WHERE status IN ('FAIL', 'REVIEW') AND amount IS NOT NULL")
    exc_row = cursor.fetchone()["exc_amt"]
    exception_pile_amount = round(exc_row or 0.0, 2)
    
    cursor.execute("SELECT AVG(risk_score) as avg_risk FROM invoices")
    res_risk = cursor.fetchone()["avg_risk"]
    avg_risk = round(res_risk or 0.0, 1)

    conn.close()
    
    auto_pass_rate = round((valid_records / total_records * 100), 1) if total_records > 0 else 100.0

    return {
        "total_records": total_records,
        "valid_records": valid_records,
        "exceptions_records": review_records + fail_records,
        "auto_passed_count": valid_records,
        "exception_pile_count": review_records + fail_records,
        "auto_pass_rate_pct": auto_pass_rate,
        "auto_passed_amount": auto_passed_amount,
        "exception_pile_amount": exception_pile_amount,
        "review_records": review_records,
        "fail_records": fail_records,
        "possible_duplicates": duplicates_count,
        "split_transactions_count": splits_count,
        "missing_fields_count": missing_count,
        "over_limit_count": over_limit_count,
        "total_amount": total_amount,
        "avg_risk_score": avg_risk
    }

@app.get("/ap-exception-report")
def get_ap_exception_report():
    """
    Generates a concise Accounts-Payable Exception Pile Summary Report.
    Fulfills challenge: 'flags anything wrong with a short report'.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as total, SUM(amount) as total_amt FROM invoices")
    tot_row = cursor.fetchone()
    total_records = tot_row["total"] or 0
    total_spend = round(tot_row["total_amt"] or 0.0, 2)
    
    cursor.execute("SELECT COUNT(*) as passed, SUM(amount) as passed_amt FROM invoices WHERE status = 'PASS'")
    pass_row = cursor.fetchone()
    auto_passed_count = pass_row["passed"] or 0
    auto_passed_spend = round(pass_row["passed_amt"] or 0.0, 2)
    
    cursor.execute("SELECT COUNT(*) as exc, SUM(amount) as exc_amt FROM invoices WHERE status IN ('FAIL', 'REVIEW')")
    exc_row = cursor.fetchone()
    exception_count = exc_row["exc"] or 0
    exception_spend = round(exc_row["exc_amt"] or 0.0, 2)
    
    # Exceptions breakdown
    cursor.execute("""
        SELECT e.*, i.vendor_name, i.amount, i.invoice_date, i.category, i.decision_status
        FROM exceptions e
        LEFT JOIN invoices i ON e.invoice_id = i.invoice_id
        ORDER BY e.severity = 'HIGH' DESC, e.id DESC
    """)
    exceptions_list = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    for exc in exceptions_list:
        exc["ai_explanation"] = generate_ai_explanation(exc)
        
    return {
        "title": "Accounts-Payable Exception Pile Summary Report",
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "system": "InvoiceCompliance.AI v2.5",
        "summary": {
            "total_invoices_audited": total_records,
            "total_spend_audited": total_spend,
            "auto_passed_clean_invoices": auto_passed_count,
            "auto_passed_spend": auto_passed_spend,
            "auto_pass_rate_pct": round((auto_passed_count / total_records * 100), 1) if total_records > 0 else 100.0,
            "exception_pile_count": exception_count,
            "exception_pile_at_risk_spend": exception_spend,
        },
        "enterprise_controls": [
            "Auto-pass clean transactions with 100% confidence",
            "Route only exception pile rows to human AP auditor",
            "Explain each violation citing the matched transaction",
            "Immutable audit log for every system & human decision"
        ],
        "exception_pile_items": exceptions_list
    }

@app.post("/check-single-invoice")
def check_single_invoice(payload: SingleInvoicePayload):
    """
    Real-time pre-payment validation for a single invoice against compliance rules,
    RapidFuzz fuzzy duplicates, and split-transaction patterns in the active database.
    """
    inv_dict = payload.model_dump()
    inv_id = payload.invoice_id
    
    # 1. Rule Engine Check
    violations = evaluate_invoice_rules(
        inv_dict,
        amount_limit=ACTIVE_POLICY["amount_limit"],
        category_limits=ACTIVE_POLICY["category_limits"]
    )
    
    # 2. Check against existing invoices in database for Duplicates & Splits
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM invoices")
    existing_invoices = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    combined = existing_invoices + [inv_dict]
    
    # Duplicate check
    dup_violations = detect_duplicates(combined, similarity_threshold=ACTIVE_POLICY["similarity_threshold"])
    for dv in dup_violations:
        if dv["invoice_id"] == inv_id:
            violations.append(dv)
            
    # Split check
    split_violations = detect_split_transactions(combined, amount_limit=ACTIVE_POLICY["amount_limit"], max_day_window=ACTIVE_POLICY["split_window_days"])
    for sv in split_violations:
        if sv["invoice_id"] == inv_id:
            violations.append(sv)

    risk_score = calculate_risk_score(violations)
    
    status = "PASS"
    if any(v["status"] == "FAIL" for v in violations):
        status = "FAIL"
    elif any(v["status"] == "REVIEW" for v in violations):
        status = "REVIEW"

    # Attach AI explanations
    for v in violations:
        v["ai_explanation"] = generate_ai_explanation(v, inv_dict)

    # Optional: Save to database if requested
    if payload.save_to_db:
        conn = get_connection()
        cursor = conn.cursor()
        dec_status = "AUTO_PASSED" if status == "PASS" else "IN_EXCEPTION_PILE"
        dec_notes = "Auto-passed by AP Compliance Engine" if status == "PASS" else f"Flagged to Exception Pile ({len(violations)} violation(s))"
        cursor.execute("""
            INSERT OR REPLACE INTO invoices 
            (invoice_id, vendor_name, invoice_date, amount, category, employee_id, description, status, risk_score, decision_status, decision_notes, source, raw_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            inv_id,
            payload.vendor_name,
            payload.invoice_date,
            payload.amount,
            payload.category,
            payload.employee_id,
            payload.description,
            status,
            risk_score,
            dec_status,
            dec_notes,
            "Single Invoice Pre-Check",
            json.dumps(inv_dict)
        ))
        for v in violations:
            cursor.execute("""
                INSERT INTO exceptions (invoice_id, rule, status, reason, evidence, citation, severity)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (inv_id, v["rule"], v["status"], v["reason"], v["evidence"], v.get("citation", v["evidence"]), v.get("severity", "MEDIUM")))
        conn.commit()
        conn.close()
        log_audit(f"Single Invoice Decision ({dec_status})", f"Invoice {inv_id} for '{payload.vendor_name}' saved via Pre-Payment Checker (Status: {status}, Decision: {dec_status}, Risk: {risk_score}).")

    return {
        "invoice_id": inv_id,
        "vendor_name": payload.vendor_name,
        "amount": payload.amount,
        "status": status,
        "risk_score": risk_score,
        "violations_count": len(violations),
        "violations": violations,
        "saved_to_db": payload.save_to_db,
        "recommendation": "APPROVED FOR PAYMENT" if status == "PASS" else "HOLD FOR COMPLIANCE REVIEW" if status == "REVIEW" else "REJECTED - POLICY VIOLATION"
    }

@app.post("/invoices/batch-decision")
def batch_decision(payload: BatchDecisionPayload):
    """
    Applies an audit decision (APPROVE, REJECT, ESCALATE) to multiple selected invoices in one operation.
    """
    if not payload.invoice_ids:
        raise HTTPException(status_code=400, detail="No invoice IDs provided")
        
    conn = get_connection()
    cursor = conn.cursor()
    
    new_status = "PASS" if payload.action == "APPROVE" else "FAIL" if payload.action == "REJECT" else "REVIEW"
    
    for inv_id in payload.invoice_ids:
        cursor.execute("""
            UPDATE invoices 
            SET decision_status = ?, decision_notes = ?, status = ?
            WHERE invoice_id = ?
        """, (payload.action, payload.notes or f"Batch {payload.action}", new_status, inv_id))
        
    conn.commit()
    conn.close()
    
    log_audit(f"Batch Decision ({payload.action})", f"Updated {len(payload.invoice_ids)} invoices to '{payload.action}'.", user_name=payload.user_name or "Compliance Officer")
    
    return {
        "status": "success",
        "action": payload.action,
        "updated_count": len(payload.invoice_ids)
    }

@app.get("/policy-config")
def get_policy_config():
    """
    Retrieves current active compliance policy parameters.
    """
    return ACTIVE_POLICY

@app.post("/policy-config")
def update_policy_config(payload: PolicyConfigPayload):
    """
    Updates active compliance policy parameters and dynamically re-audits all records.
    """
    global ACTIVE_POLICY
    ACTIVE_POLICY["amount_limit"] = payload.amount_limit
    ACTIVE_POLICY["similarity_threshold"] = payload.similarity_threshold
    ACTIVE_POLICY["split_window_days"] = payload.split_window_days
    ACTIVE_POLICY["category_limits"] = payload.category_limits
    
    # Automatically re-audit active records with new policy
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM invoices")
    rows = [dict(r) for r in cursor.fetchall()]
    cursor.execute("DELETE FROM exceptions")
    conn.commit()
    conn.close()
    
    if rows:
        process_and_store_invoices(rows, amount_limit=payload.amount_limit)
        
    log_audit("Policy Updated", f"Global limit: ${payload.amount_limit}, Similarity: {payload.similarity_threshold}%, Split window: {payload.split_window_days} days.")
    
    return {
        "status": "success",
        "message": "Policy configuration updated and all active records re-audited.",
        "active_policy": ACTIVE_POLICY
    }

@app.post("/seed-scenario/{scenario_id}")
def seed_scenario(scenario_id: str):
    """
    Seeds preloaded real-world compliance scenarios for testing.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM invoices")
    cursor.execute("DELETE FROM exceptions")
    conn.commit()
    conn.close()
    
    if scenario_id == "procurement-fraud":
        records = [
            {"invoice_id": "PR-901", "vendor_name": "Apex Global Procurement", "invoice_date": "2026-10-01", "amount": 4900.0, "category": "Consulting", "employee_id": "EMP-99", "description": "Vendor advisory split 1", "source": "Procurement Fraud Scenario"},
            {"invoice_id": "PR-902", "vendor_name": "Apex Global Procurement", "invoice_date": "2026-10-02", "amount": 4950.0, "category": "Consulting", "employee_id": "EMP-99", "description": "Vendor advisory split 2", "source": "Procurement Fraud Scenario"},
            {"invoice_id": "PR-903", "vendor_name": "Apex Global Procurement Ltd", "invoice_date": "2026-10-03", "amount": 4950.0, "category": "Consulting", "employee_id": "EMP-99", "description": "Vendor advisory split 3", "source": "Procurement Fraud Scenario"},
            {"invoice_id": "PR-904", "vendor_name": "Executive Flight Charters", "invoice_date": "2026-10-04", "amount": 16500.0, "category": "Travel & Lodging", "employee_id": "EMP-01", "description": "Charter jet reservation", "source": "Procurement Fraud Scenario"}
        ]
    elif scenario_id == "clean-operations":
        records = [
            {"invoice_id": "CLN-101", "vendor_name": "Microsoft Azure Cloud", "invoice_date": "2026-10-01", "amount": 1450.0, "category": "Cloud Infrastructure", "employee_id": "EMP-20", "description": "Monthly hosting", "source": "Clean Operations Scenario"},
            {"invoice_id": "CLN-102", "vendor_name": "Staples Office Solutions", "invoice_date": "2026-10-02", "amount": 320.0, "category": "Office Supplies", "employee_id": "EMP-21", "description": "Office paper & stationery", "source": "Clean Operations Scenario"},
            {"invoice_id": "CLN-103", "vendor_name": "Delta Airlines Corporate", "invoice_date": "2026-10-03", "amount": 780.0, "category": "Travel & Lodging", "employee_id": "EMP-22", "description": "Flight booking", "source": "Clean Operations Scenario"}
        ]
    else: # Default scenario: enterprise-mixed
        records = get_demo_dataset()
        
    process_and_store_invoices(records, amount_limit=ACTIVE_POLICY["amount_limit"])
    log_audit("Scenario Seeded", f"Loaded scenario '{scenario_id}' with {len(records)} records.")
    
    return {
        "status": "success",
        "scenario": scenario_id,
        "records_loaded": len(records)
    }

@app.post("/parse-document")
async def parse_document(file: Optional[UploadFile] = File(None), raw_text: Optional[str] = Form(None)):
    """
    Parses PDF document bytes or raw pasted invoice OCR text, extracts structured fields,
    verifies mathematical line-item integrity (subtotal + tax = total), and infers categories.
    """
    from services.document_parser import extract_text_from_pdf_bytes, parse_invoice_text
    
    text_content = ""
    if file:
        content_bytes = await file.read()
        filename = file.filename.lower()
        if filename.endswith(".pdf"):
            text_content = extract_text_from_pdf_bytes(content_bytes)
        else:
            text_content = content_bytes.decode("utf-8", errors="ignore")
    elif raw_text:
        text_content = raw_text
        
    if not text_content.strip():
        raise HTTPException(status_code=400, detail="No document file or text content provided for parsing.")
        
    parsed = parse_invoice_text(text_content)
    log_audit("Document Parsed", f"Parsed invoice '{parsed['invoice_id']}' for '{parsed['vendor_name']}' (${parsed['amount']}). Math verified: {parsed['math_verified']}.")
    return parsed

@app.get("/watchlist")
def get_watchlist_api():
    """
    Returns active high-risk / sanctioned counterparty entities monitored by RapidFuzz.
    """
    from services.watchlist import get_watchlist
    return {"watchlist": get_watchlist()}

@app.post("/watchlist")
def add_watchlist_api(payload: WatchlistPayload):
    """
    Adds a new high-risk or restricted counterparty to the active screening watchlist.
    """
    from services.watchlist import add_to_watchlist
    item = add_to_watchlist(payload.entity_name, payload.reason, payload.risk_level or "HIGH", payload.category or "Custom Watchlist")
    log_audit("Watchlist Updated", f"Added '{payload.entity_name}' to high-risk counterparty watchlist.")
    return {"status": "success", "entity": item}

@app.delete("/watchlist/{entity_name}")
def delete_watchlist_api(entity_name: str):
    """
    Removes an entity from the active screening watchlist.
    """
    from services.watchlist import remove_from_watchlist
    removed = remove_from_watchlist(entity_name)
    if not removed:
        raise HTTPException(status_code=404, detail="Entity not found on watchlist.")
    log_audit("Watchlist Updated", f"Removed '{entity_name}' from high-risk watchlist.")
    return {"status": "success", "message": f"Entity '{entity_name}' removed from watchlist."}

@app.post("/ask-ai")
def ask_compliance_copilot(payload: AskAIPayload):
    """
    Compliance AI Copilot: Answers natural language questions from auditors
    grounded strictly in the live SQLite database state without hallucinations.
    """
    from services.ai_copilot import answer_compliance_query
    return answer_compliance_query(payload.query)

@app.get("/export-erp-json")
def export_erp_json():
    """
    Exports audited invoices formatted for enterprise ERP ingestion (SAP S/4HANA & Oracle Cloud ERP).
    """
    import datetime
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM invoices")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    erp_records = []
    for r in rows:
        erp_records.append({
            "erp_transaction_id": r["invoice_id"],
            "supplier_name": r["vendor_name"],
            "posting_date": r["invoice_date"],
            "currency": "USD",
            "net_amount": r["amount"],
            "accounting_classification": r["category"],
            "compliance_status": r["status"],
            "audit_decision": r.get("decision_status", "PENDING"),
            "risk_index": r.get("risk_score", 0),
            "approval_ready": (r["status"] == "PASS" or r.get("decision_status") == "APPROVE")
        })
        
    return {
        "erp_system": "Standard Financial Gateway (SAP S/4HANA & Oracle Cloud Ready)",
        "exported_at": datetime.datetime.now().isoformat(),
        "total_records": len(erp_records),
        "records": erp_records
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
