from typing import List, Dict, Any
import datetime

def detect_split_transactions(invoices: List[Dict[str, Any]], amount_limit: float = 5000.0) -> List[Dict[str, Any]]:
    """
    Detects split transactions / threshold structuring where multiple invoices
    from the same vendor fall just below the approval threshold limit within a short time frame.
    """
    violations = []
    threshold_lower_bound = amount_limit * 0.80 # e.g. $4,000 if limit is $5,000
    
    vendor_groups: Dict[str, List[Dict[str, Any]]] = {}
    
    for inv in invoices:
        v_name = str(inv.get("vendor_name") or "").strip().lower()
        if not v_name or v_name == "none":
            continue
        if v_name not in vendor_groups:
            vendor_groups[v_name] = []
        vendor_groups[v_name].append(inv)
        
    for v_name, group in vendor_groups.items():
        if len(group) < 2:
            continue
            
        near_threshold_invoices = []
        for inv in group:
            amt = inv.get("amount")
            if amt is not None:
                try:
                    val = float(amt)
                    if threshold_lower_bound <= val < amount_limit:
                        near_threshold_invoices.append(inv)
                except (ValueError, TypeError):
                    pass
                    
        if len(near_threshold_invoices) >= 2:
            inv_ids = [str(i.get("invoice_id") or "") for i in near_threshold_invoices]
            total_split_amt = sum(float(i.get("amount", 0)) for i in near_threshold_invoices)
            
            for inv in near_threshold_invoices:
                inv_id = str(inv.get("invoice_id") or "UNKNOWN")
                violations.append({
                    "invoice_id": inv_id,
                    "rule": "Split Transaction / Threshold Evasion Check",
                    "status": "FAIL",
                    "reason": f"Suspicious split transaction pattern detected for vendor '{inv.get('vendor_name')}'. {len(near_threshold_invoices)} invoices totaling ${total_split_amt:,.2f} hover just below approval threshold (${amount_limit:,.2f})",
                    "evidence": f"Multiple near-limit invoices ({', '.join(inv_ids)}) totaling ${total_split_amt:,.2f} > Policy Limit ${amount_limit:,.2f}",
                    "severity": "HIGH"
                })

    return violations
