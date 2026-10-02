from typing import List, Dict, Any
import numpy as np

def generate_data_profile(invoices: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not invoices:
        return {
            "total_records": 0,
            "columns": [],
            "missing_values_per_column": {},
            "duplicate_count": 0,
            "numeric_columns": [],
            "date_columns": [],
            "categorical_columns": [],
            "stats": {"min_amount": 0, "max_amount": 0, "avg_amount": 0, "total_amount": 0}
        }
        
    total_records = len(invoices)
    sample = invoices[0]
    columns = list(sample.keys())
    
    missing_counts = {col: 0 for col in columns}
    amounts = []
    seen_ids = set()
    dup_count = 0
    
    for inv in invoices:
        # Count missing
        for col in columns:
            val = inv.get(col)
            if val is None or str(val).strip() in ["", "None", "nan"]:
                missing_counts[col] += 1
                
        # Amount stats
        amt = inv.get("amount")
        if amt is not None:
            try:
                amounts.append(float(amt))
            except (ValueError, TypeError):
                pass
                
        # Duplicate ID count
        inv_id = str(inv.get("invoice_id") or "").strip()
        if inv_id and inv_id != "None":
            if inv_id in seen_ids:
                dup_count += 1
            else:
                seen_ids.add(inv_id)

    min_amt = float(np.min(amounts)) if amounts else 0.0
    max_amt = float(np.max(amounts)) if amounts else 0.0
    avg_amt = float(np.mean(amounts)) if amounts else 0.0
    total_amt = float(np.sum(amounts)) if amounts else 0.0
    
    return {
        "total_records": total_records,
        "columns_count": len(columns),
        "columns": columns,
        "missing_values_per_column": missing_counts,
        "duplicate_count": dup_count,
        "numeric_columns": ["amount"],
        "date_columns": ["invoice_date"],
        "categorical_columns": ["category", "vendor_name", "status"],
        "stats": {
            "min_amount": round(min_amt, 2),
            "max_amount": round(max_amt, 2),
            "avg_amount": round(avg_amt, 2),
            "total_amount": round(total_amt, 2)
        }
    }
