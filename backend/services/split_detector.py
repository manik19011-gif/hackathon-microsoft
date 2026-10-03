from typing import List, Dict, Any
import datetime

def parse_simple_date(date_val: Any) -> datetime.date:
    if isinstance(date_val, datetime.datetime):
        return date_val.date()
    if isinstance(date_val, datetime.date):
        return date_val
    s = str(date_val).strip().split("T")[0].split(" ")[0]
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None

def detect_split_transactions(invoices: List[Dict[str, Any]], amount_limit: float = 5000.0, max_day_window: int = 7) -> List[Dict[str, Any]]:
    """
    Detects split transactions / threshold structuring where multiple invoices
    from the same vendor fall just below the approval threshold limit within a rolling temporal window (e.g. 7 days).
    """
    violations = []
    threshold_lower_bound = amount_limit * 0.80 # e.g. $4,000 if limit is $5,000
    
    vendor_groups: Dict[str, List[Dict[str, Any]]] = {}
    
    for inv in invoices:
        v_name = str(inv.get("vendor_name") or "").strip().lower()
        if not v_name or v_name in ["none", "nan", "null"]:
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
            # Check temporal window: are they proximate in date?
            # Sort by parsed date
            dates = [parse_simple_date(i.get("invoice_date")) for i in near_threshold_invoices]
            is_proximate = False
            valid_dates = [d for d in dates if d is not None]
            
            if len(valid_dates) >= 2:
                valid_dates.sort()
                day_span = (valid_dates[-1] - valid_dates[0]).days
                if day_span <= max_day_window:
                    is_proximate = True
            else:
                # If dates are unavailable, flag with caution based on vendor batching
                is_proximate = True
                
            if is_proximate:
                inv_ids = [str(i.get("invoice_id") or "") for i in near_threshold_invoices]
                total_split_amt = sum(float(i.get("amount", 0)) for i in near_threshold_invoices)
                
                for inv in near_threshold_invoices:
                    inv_id = str(inv.get("invoice_id") or "UNKNOWN")
                    counterparts = [x for x in inv_ids if x != inv_id]
                    violations.append({
                        "invoice_id": inv_id,
                        "rule": "Split Transaction / Threshold Evasion Check",
                        "status": "FAIL",
                        "reason": f"Suspicious split transaction pattern detected for vendor '{inv.get('vendor_name')}'. {len(near_threshold_invoices)} invoices totaling ${total_split_amt:,.2f} hover just below approval threshold (${amount_limit:,.2f}) within {max_day_window} days",
                        "evidence": f"Multiple near-limit invoices ({', '.join(inv_ids)}) totaling ${total_split_amt:,.2f} > Policy Limit ${amount_limit:,.2f}",
                        "citation": f"Matched split transaction cohort: Invoices [{', '.join(counterparts)}] from vendor '{inv.get('vendor_name')}' within {max_day_window} days",
                        "matched_invoice_ids": counterparts,
                        "severity": "HIGH"
                    })

    return violations
