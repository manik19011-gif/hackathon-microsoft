from typing import List, Dict, Any
from rapidfuzz import fuzz

def detect_duplicates(invoices: List[Dict[str, Any]], similarity_threshold: float = 85.0) -> List[Dict[str, Any]]:
    """
    Scans a list of invoice dicts for exact and fuzzy/similar duplicates.
    Adaptively handles missing or optional fields and optimizes comparison speed.
    """
    violations = []
    seen_ids: Dict[str, str] = {}
    
    # 1. Exact Duplicate ID check (Skip placeholder or auto-gen IDs)
    for inv in invoices:
        inv_id = str(inv.get("invoice_id") or "").strip()
        if not inv_id or inv_id.lower() in ["none", "nan", "unknown", ""] or inv_id.startswith("AUTO_GEN_"):
            continue
            
        if inv_id in seen_ids:
            violations.append({
                "invoice_id": inv_id,
                "rule": "Exact Duplicate Identifier Check",
                "status": "FAIL",
                "reason": f"Duplicate invoice ID detected: '{inv_id}'",
                "evidence": f"Multiple records share the same invoice_id: '{inv_id}'",
                "severity": "HIGH"
            })
        else:
            seen_ids[inv_id] = inv_id

    # 2. Optimized Comparison for Exact & Similar Duplicates
    n = len(invoices)
    for i in range(n):
        inv_a = invoices[i]
        id_a = str(inv_a.get("invoice_id") or f"ROW_{i}")
        vendor_a = str(inv_a.get("vendor_name") or "").strip().lower()
        amount_a = inv_a.get("amount")
        date_a = str(inv_a.get("invoice_date") or "").strip()
        
        # Skip comparison if basic vendor identifier is missing
        if not vendor_a or vendor_a in ["none", "nan", "null"]:
            continue
            
        for j in range(i + 1, n):
            inv_b = invoices[j]
            id_b = str(inv_b.get("invoice_id") or f"ROW_{j}")
            vendor_b = str(inv_b.get("vendor_name") or "").strip().lower()
            amount_b = inv_b.get("amount")
            date_b = str(inv_b.get("invoice_date") or "").strip()
            
            if not vendor_b or vendor_b in ["none", "nan", "null"]:
                continue
                
            # Check amount match (within 0.01 tolerance)
            amounts_match = False
            if amount_a is not None and amount_b is not None:
                try:
                    amounts_match = abs(float(amount_a) - float(amount_b)) < 0.01
                except (ValueError, TypeError):
                    pass

            # Check exact vendor + amount + date match
            if vendor_a == vendor_b and amounts_match:
                if date_a and date_b and date_a == date_b:
                    violations.append({
                        "invoice_id": id_b,
                        "rule": "Exact Duplicate Content Check",
                        "status": "FAIL",
                        "reason": f"Exact duplicate record found matching Invoice '{id_a}' (Vendor: '{inv_a.get('vendor_name')}', Amount: ${amount_a}, Date: '{date_a}')",
                        "evidence": f"Identical Vendor, Amount (${amount_a}), and Date ({date_a}) across '{id_a}' and '{id_b}'",
                        "severity": "HIGH"
                    })
                    continue
                elif not date_a or not date_b or date_a == date_b:
                    # Same vendor and exact amount
                    violations.append({
                        "invoice_id": id_b,
                        "rule": "Exact Duplicate Content Check",
                        "status": "FAIL",
                        "reason": f"Duplicate transaction detected: Identical Vendor and Amount matching Invoice '{id_a}'",
                        "evidence": f"Vendor: '{inv_a.get('vendor_name')}', Amount: ${amount_a} across '{id_a}' and '{id_b}'",
                        "severity": "HIGH"
                    })
                    continue
                
            # Check Fuzzy / Similar Vendor + Exact Amount
            if amounts_match and vendor_a != vendor_b:
                sim_score = fuzz.ratio(vendor_a, vendor_b)
                if sim_score >= similarity_threshold:
                    violations.append({
                        "invoice_id": id_b,
                        "rule": "Similar Duplicate Vendor Check",
                        "status": "REVIEW",
                        "reason": f"Suspiciously similar invoice found compared to '{id_a}'. Vendor similarity: {sim_score:.0f}% ('{inv_a.get('vendor_name')}' vs '{inv_b.get('vendor_name')}') with identical amount ${amount_a}",
                        "evidence": f"Vendor match score: {sim_score:.0f}%, Amount: ${amount_a}, Matched with Invoice '{id_a}'",
                        "severity": "MEDIUM"
                    })

    return violations
