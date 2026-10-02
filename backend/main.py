from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import sqlite3
import json
import io
import csv

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db import get_connection, init_db, log_audit
from services.rule_engine import evaluate_invoice_rules, calculate_risk_score
from services.duplicate_detector import detect_duplicates
from services.profiler import generate_data_profile
from services.ai_explainer import generate_ai_explanation
from services.demo_generator import get_demo_dataset
from services.data_loader import load_and_process_dataset

app = FastAPI(
    title="Invoice & Expense Checker Assistant API",
    description="Automated compliance, duplicate detection, and AI audit for enterprise expense invoices.",
    version="1.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    init_db()
    log_audit("API Startup", "Database initialized and API endpoints ready.")

@app.get("/")
def root():
    return {
        "status": "online",
        "service": "Invoice & Expense Checker Assistant API",
        "documentation": "/docs"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}

def process_and_store_invoices(invoices: List[Dict[str, Any]], amount_limit: float = 5000.0):
    """
    Runs rule engine + duplicate detector and persists records + exceptions into SQLite.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if risk_score column exists
    cursor.execute("PRAGMA table_info(invoices)")
    cols = [r["name"] for r in cursor.fetchall()]
    if "risk_score" not in cols:
        cursor.execute("ALTER TABLE invoices ADD COLUMN risk_score INTEGER DEFAULT 0")
        conn.commit()

    # 1. Evaluate Rule Engine for each record
    invoice_violations_map = {}
    for inv in invoices:
        inv_id = str(inv.get("invoice_id") or "UNKNOWN")
        v_list = evaluate_invoice_rules(inv, amount_limit=amount_limit)
        invoice_violations_map[inv_id] = v_list
        
    # 2. Evaluate Duplicate Detection across dataset
    duplicate_violations = detect_duplicates(invoices)
    for dup_v in duplicate_violations:
        inv_id = dup_v["invoice_id"]
        if inv_id in invoice_violations_map:
            invoice_violations_map[inv_id].append(dup_v)
        else:
            invoice_violations_map[inv_id] = [dup_v]
            
    # 3. Persist to Database
    for inv in invoices:
        inv_id = str(inv.get("invoice_id") or "UNKNOWN")
        violations = invoice_violations_map.get(inv_id, [])
        risk_score = calculate_risk_score(violations)
        
        # Determine overall status
        status = "PASS"
        if any(v["status"] == "FAIL" for v in violations):
            status = "FAIL"
        elif any(v["status"] == "REVIEW" for v in violations):
            status = "REVIEW"
            
        cursor.execute("""
            INSERT OR REPLACE INTO invoices 
            (invoice_id, vendor_name, invoice_date, amount, category, employee_id, description, status, risk_score, source, raw_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            inv.get("source", "System Ingestion"),
            json.dumps(inv)
        ))
        
        # Store violations
        for v in violations:
            cursor.execute("""
                INSERT INTO exceptions (invoice_id, rule, status, reason, evidence, severity)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (inv_id, v["rule"], v["status"], v["reason"], v["evidence"], v.get("severity", "MEDIUM")))
            
    conn.commit()
    conn.close()
    log_audit("Dataset Processed", f"Ingested {len(invoices)} records. Amount limit policy: ${amount_limit}")

@app.post("/seed-demo")
def seed_demo(amount_limit: float = Query(5000.0, description="Configurable amount limit threshold")):
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
    """
    Upload CSV or Excel file directly into dataset processing pipeline.
    """
    temp_dir = os.path.join(os.path.dirname(__file__), "data", "raw")
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, file.filename)
    
    contents = await file.read()
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

@app.get("/exceptions")
def list_exceptions(severity: Optional[str] = None):
    conn = get_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT e.*, i.vendor_name, i.amount, i.invoice_date, i.source 
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

@app.get("/export-exceptions-csv")
def export_exceptions_csv():
    """
    Generates downloadable CSV report of all flagged compliance exceptions.
    """
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
    
    cursor.execute("SELECT COUNT(*) as missing FROM exceptions WHERE rule LIKE '%Required%'")
    missing_count = cursor.fetchone()["missing"]

    cursor.execute("SELECT COUNT(*) as over_limit FROM exceptions WHERE rule LIKE '%Amount Limit%' OR rule LIKE '%Threshold%'")
    over_limit_count = cursor.fetchone()["over_limit"]

    cursor.execute("SELECT SUM(amount) as total_amt FROM invoices WHERE amount IS NOT NULL")
    res_amt = cursor.fetchone()["total_amt"]
    total_amount = round(res_amt or 0.0, 2)
    
    cursor.execute("SELECT AVG(risk_score) as avg_risk FROM invoices")
    res_risk = cursor.fetchone()["avg_risk"]
    avg_risk = round(res_risk or 0.0, 1)

    conn.close()
    
    return {
        "total_records": total_records,
        "valid_records": valid_records,
        "exceptions_records": review_records + fail_records,
        "review_records": review_records,
        "fail_records": fail_records,
        "possible_duplicates": duplicates_count,
        "missing_fields_count": missing_count,
        "over_limit_count": over_limit_count,
        "total_amount": total_amount,
        "avg_risk_score": avg_risk
    }

@app.post("/run-audit")
def trigger_re_audit(amount_limit: float = Query(5000.0)):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM invoices")
    rows = [dict(r) for r in cursor.fetchall()]
    
    cursor.execute("DELETE FROM exceptions")
    conn.commit()
    conn.close()
    
    if rows:
        process_and_store_invoices(rows, amount_limit=amount_limit)
        
    return {
        "status": "success",
        "message": f"Re-audited {len(rows)} records using amount limit threshold of ${amount_limit:,.2f}"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
