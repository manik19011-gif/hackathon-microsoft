import sqlite3
import os
import json
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "invoice_checker.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Invoices table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_id TEXT UNIQUE,
        vendor_name TEXT,
        invoice_date TEXT,
        amount REAL,
        category TEXT,
        employee_id TEXT,
        description TEXT,
        status TEXT DEFAULT 'PASS',
        risk_score INTEGER DEFAULT 0,
        decision_status TEXT DEFAULT 'PENDING',
        decision_notes TEXT,
        source TEXT DEFAULT 'Kaggle-derived Demo Case',
        raw_data TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Rule violations / Exceptions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS exceptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_id TEXT,
        rule TEXT,
        status TEXT,
        reason TEXT,
        evidence TEXT,
        citation TEXT,
        severity TEXT DEFAULT 'MEDIUM',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(invoice_id) REFERENCES invoices(invoice_id)
    )
    """)

    # Ensure citation column exists if table was created previously
    cursor.execute("PRAGMA table_info(exceptions)")
    exc_cols = [r["name"] for r in cursor.fetchall()]
    if "citation" not in exc_cols:
        cursor.execute("ALTER TABLE exceptions ADD COLUMN citation TEXT")
    
    # Audit log table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        action TEXT,
        user_name TEXT DEFAULT 'System',
        details TEXT
    )
    """)
    
    # Source dataset table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS source_datasets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        total_records INTEGER,
        status TEXT
    )
    """)
    
    conn.commit()
    conn.close()

def log_audit(action: str, details: str, user_name: str = "System"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO audit_logs (action, user_name, details) VALUES (?, ?, ?)",
        (action, user_name, details)
    )
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at", DB_PATH)
