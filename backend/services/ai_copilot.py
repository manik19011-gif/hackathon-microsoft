"""
Interactive Compliance AI Copilot Service
Provides grounded natural language responses to auditor queries regarding active
compliance exceptions, high-risk vendors, split transactions, and Benford distributions.
"""

from typing import Dict, Any, List
import sqlite3
import re
from database.db import get_connection
from services.benford import analyze_benford_law
from services.vendor_analytics import analyze_vendor_risk

def answer_compliance_query(query: str) -> Dict[str, Any]:
    """
    Answers an auditor's natural language question grounded in the active database state.
    """
    q = query.strip().lower()
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM invoices")
    invoices = [dict(r) for r in cursor.fetchall()]
    
    cursor.execute("SELECT * FROM exceptions")
    exceptions = [dict(r) for r in cursor.fetchall()]
    
    conn.close()
    
    total_invoices = len(invoices)
    total_spend = sum(float(i.get("amount") or 0) for i in invoices if float(i.get("amount") or 0) > 0)
    failed_invoices = [i for i in invoices if i.get("status") == "FAIL"]
    review_invoices = [i for i in invoices if i.get("status") == "REVIEW"]
    passed_invoices = [i for i in invoices if i.get("status") == "PASS"]
    
    vendor_analytics = analyze_vendor_risk(invoices, exceptions)
    benford_stats = analyze_benford_law(invoices)
    
    # 1. Split Transaction Query
    if any(k in q for k in ["split", "structuring", "threshold evasion", "evade"]):
        splits = [e for e in exceptions if "split" in e.get("rule", "").lower()]
        if not splits:
            return {
                "query": query,
                "answer": "No split-transaction threshold structuring patterns were detected in the active ledger. All consecutive transactions within 7-day intervals fall within approved compliance boundaries.",
                "category": "Split Transactions",
                "citations": []
            }
        citations = list(set([s["invoice_id"] for s in splits]))
        sample = splits[0]
        return {
            "query": query,
            "answer": f"Found {len(splits)} invoices flagged for split-transaction structuring under the 7-day rolling window rule. For instance, invoice {sample['invoice_id']} was flagged because consecutive near-limit purchases were submitted to bypass the approval threshold without executive sign-off.",
            "category": "Split Transactions",
            "citations": citations,
            "evidence": [s["reason"] for s in splits[:3]]
        }
        
    # 2. Duplicate Payments / Invoices Query
    if any(k in q for k in ["duplicate", "fuzzy", "rapidfuzz", "double payment"]):
        dups = [e for e in exceptions if "duplicate" in e.get("rule", "").lower()]
        if not dups:
            return {
                "query": query,
                "answer": "No exact or fuzzy duplicate invoices were identified. All invoice identifiers and vendor-amount pairings are distinct.",
                "category": "Duplicate Detection",
                "citations": []
            }
        citations = list(set([d["invoice_id"] for d in dups]))
        return {
            "query": query,
            "answer": f"Detected {len(dups)} duplicate invoice violations across the active ledger. RapidFuzz token sorting caught fuzzy vendor variations and identical amount submissions requiring immediate credit note or payment hold.",
            "category": "Duplicate Detection",
            "citations": citations,
            "evidence": [d["reason"] for d in dups[:3]]
        }

    # 3. High-Risk / Sanctions / Watchlist Query
    if any(k in q for k in ["watch", "sanction", "watchlist", "shell", "riskiest vendor", "risky vendor", "top risk"]):
        watchlist_matches = [e for e in exceptions if "watchlist" in e.get("rule", "").lower() or "sanction" in e.get("rule", "").lower()]
        top_risk_vendor = vendor_analytics[0] if vendor_analytics else None
        
        ans_parts = []
        if watchlist_matches:
            ans_parts.append(f"CRITICAL ALERT: {len(watchlist_matches)} invoices matched high-risk / sanctioned counterparty watchlists.")
        if top_risk_vendor:
            ans_parts.append(f"The highest-risk vendor is '{top_risk_vendor['vendor_name']}' with a risk rating of {top_risk_vendor['risk_rating']} (Max Risk Score: {top_risk_vendor['max_risk_score']}/100, Total Spend: ${top_risk_vendor['total_spend']:,.2f}, Violations: {top_risk_vendor['total_violations']}).")
        
        return {
            "query": query,
            "answer": " ".join(ans_parts) or "All vendors are currently categorized under low or standard operational risk.",
            "category": "Vendor Intelligence",
            "citations": [w["invoice_id"] for w in watchlist_matches],
            "top_vendor": top_risk_vendor
        }

    # 4. Benford's Law Query
    if any(k in q for k in ["benford", "statistical", "first digit", "conformity", "mad score"]):
        return {
            "query": query,
            "answer": f"Benford's Law statistical screening evaluated {benford_stats['total_analyzed']} invoices. Overall natural log conformity is rated as '{benford_stats['conformity']}' with a Mean Absolute Deviation (MAD) score of {benford_stats['mad_score']}. This metric assesses whether numerical receipts follow authentic logarithmic distributions or show manual fabrication.",
            "category": "Forensic Analytics",
            "conformity": benford_stats["conformity"],
            "mad_score": benford_stats["mad_score"]
        }

    # 5. General Summary & Portfolio Health Query
    pass_pct = round((len(passed_invoices) / total_invoices * 100), 1) if total_invoices > 0 else 0.0
    return {
        "query": query,
        "answer": f"Active Portfolio Summary: Audited {total_invoices} invoices representing ${total_spend:,.2f} in total procurement spend. Overall compliance pass rate is {pass_pct}%. Currently, {len(failed_invoices)} invoices have critical FAIL violations, {len(review_invoices)} require auditor review, and {len(passed_invoices)} passed clean. Top risk categories are actively monitored under SOX 404 controls.",
        "category": "Executive Summary",
        "total_invoices": total_invoices,
        "total_spend": total_spend,
        "pass_rate_pct": pass_pct,
        "critical_fails": len(failed_invoices),
        "review_required": len(review_invoices)
    }
