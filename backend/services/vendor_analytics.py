from typing import List, Dict, Any

def analyze_vendor_risk(invoices: List[Dict[str, Any]], exceptions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Aggregates spend, violation counts, and risk profiles per vendor.
    """
    vendor_stats: Dict[str, Dict[str, Any]] = {}
    
    # Map exceptions to invoice_ids
    exception_counts: Dict[str, int] = {}
    for exc in exceptions:
        inv_id = str(exc.get("invoice_id") or "")
        exception_counts[inv_id] = exception_counts.get(inv_id, 0) + 1

    for inv in invoices:
        v_name = str(inv.get("vendor_name") or "Unidentified Vendor").strip()
        inv_id = str(inv.get("invoice_id") or "")
        amt = float(inv.get("amount") or 0.0)
        risk = int(inv.get("risk_score") or 0)
        
        if v_name not in vendor_stats:
            vendor_stats[v_name] = {
                "vendor_name": v_name,
                "invoice_count": 0,
                "total_spend": 0.0,
                "total_violations": 0,
                "max_risk_score": 0,
                "avg_risk_score": 0.0,
                "risk_rating": "LOW"
            }
            
        stats = vendor_stats[v_name]
        stats["invoice_count"] += 1
        stats["total_spend"] += max(amt, 0.0)
        stats["total_violations"] += exception_counts.get(inv_id, 0)
        stats["max_risk_score"] = max(stats["max_risk_score"], risk)

    result = []
    for v_name, stats in vendor_stats.items():
        count = stats["invoice_count"]
        stats["total_spend"] = round(stats["total_spend"], 2)
        stats["avg_risk_score"] = round(stats["max_risk_score"] * 0.8, 1)
        
        # Risk Rating Classification
        if stats["max_risk_score"] >= 45 or stats["total_violations"] >= 2:
            stats["risk_rating"] = "HIGH"
        elif stats["max_risk_score"] >= 20 or stats["total_violations"] >= 1:
            stats["risk_rating"] = "MEDIUM"
        else:
            stats["risk_rating"] = "LOW"
            
        result.append(stats)
        
    result.sort(key=lambda x: (x["max_risk_score"], x["total_spend"]), reverse=True)
    return result
