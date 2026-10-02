from typing import List, Dict, Any
import datetime

DEFAULT_AMOUNT_LIMIT = 5000.0

def validate_date(date_str: Any) -> bool:
    if not date_str or str(date_str).strip() in ["None", "nan", ""]:
        return False
    # Attempt common date parsing
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            datetime.datetime.strptime(str(date_str).strip(), fmt)
            return True
        except ValueError:
            continue
    return False

def evaluate_invoice_rules(invoice: Dict[str, Any], amount_limit: float = DEFAULT_AMOUNT_LIMIT) -> List[Dict[str, Any]]:
    violations = []
    inv_id = str(invoice.get("invoice_id") or "UNKNOWN")
    
    # Rule 1: Required Fields Validation
    required_fields = ["invoice_id", "vendor_name", "amount", "invoice_date"]
    missing = [field for field in required_fields if invoice.get(field) is None or str(invoice.get(field)).strip() in ["None", "nan", ""]]
    if missing:
        violations.append({
            "invoice_id": inv_id,
            "rule": "Required Fields Check",
            "status": "FAIL",
            "reason": f"Missing required field(s): {', '.join(missing)}",
            "evidence": f"Provided record lacks values for: {missing}",
            "severity": "HIGH"
        })
        
    # Rule 2: Amount > 0
    amount = invoice.get("amount")
    if amount is not None:
        try:
            val = float(amount)
            if val <= 0:
                violations.append({
                    "invoice_id": inv_id,
                    "rule": "Invalid Amount Check",
                    "status": "FAIL",
                    "reason": f"Invoice amount must be positive. Found ${val:.2f}",
                    "evidence": f"Amount = {val}",
                    "severity": "HIGH"
                })
        except (ValueError, TypeError):
            violations.append({
                "invoice_id": inv_id,
                "rule": "Non-numeric Amount Check",
                "status": "FAIL",
                "reason": "Invoice amount is non-numeric or unparseable",
                "evidence": f"Amount raw value: {amount}",
                "severity": "HIGH"
            })
            
    # Rule 3: Configurable Amount Limit
    if amount is not None:
        try:
            val = float(amount)
            if val > amount_limit:
                violations.append({
                    "invoice_id": inv_id,
                    "rule": "Amount Limit Policy Check",
                    "status": "REVIEW",
                    "reason": f"Invoice amount (${val:,.2f}) exceeds policy threshold limit of (${amount_limit:,.2f})",
                    "evidence": f"Invoice amount ${val:,.2f} > Policy Limit ${amount_limit:,.2f}",
                    "severity": "MEDIUM"
                })
        except (ValueError, TypeError):
            pass

    # Rule 4: Invalid Date Detection
    inv_date = invoice.get("invoice_date")
    if inv_date and not validate_date(inv_date):
        violations.append({
            "invoice_id": inv_id,
            "rule": "Invalid Date Format Check",
            "status": "REVIEW",
            "reason": f"Unrecognized or invalid date format: '{inv_date}'",
            "evidence": f"Invoice Date string: '{inv_date}'",
            "severity": "LOW"
        })
        
    return violations
