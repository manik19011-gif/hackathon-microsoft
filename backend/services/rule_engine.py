from typing import List, Dict, Any, Tuple
import datetime

DEFAULT_AMOUNT_LIMIT = 5000.0

CATEGORY_LIMITS = {
    "meals & entertainment": 250.0,
    "meals": 250.0,
    "office supplies": 1000.0,
    "travel & lodging": 3000.0,
    "travel": 3000.0
}

def validate_date(date_str: Any) -> Tuple[bool, Optional[datetime.date]]:
    if not date_str or str(date_str).strip() in ["None", "nan", ""]:
        return False, None
    s = str(date_str).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            dt = datetime.datetime.strptime(s, fmt).date()
            return True, dt
        except ValueError:
            continue
    return False, None

def calculate_risk_score(violations: List[Dict[str, Any]]) -> int:
    """
    Calculates a 0-100 Risk Score for an invoice based on violation severity weights.
    """
    if not violations:
        return 0
    score = 0
    for v in violations:
        sev = v.get("severity", "MEDIUM").upper()
        if sev == "HIGH":
            score += 45
        elif sev == "MEDIUM":
            score += 25
        elif sev == "LOW":
            score += 10
    return min(score, 100)

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
    val_amount = None
    if amount is not None:
        try:
            val_amount = float(amount)
            if val_amount <= 0:
                violations.append({
                    "invoice_id": inv_id,
                    "rule": "Invalid Amount Check",
                    "status": "FAIL",
                    "reason": f"Invoice amount must be positive. Found ${val_amount:.2f}",
                    "evidence": f"Amount = {val_amount}",
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
            
    # Rule 3: Configurable Global Amount Limit
    if val_amount is not None and val_amount > 0:
        if val_amount > amount_limit:
            violations.append({
                "invoice_id": inv_id,
                "rule": "Global Amount Limit Policy Check",
                "status": "REVIEW",
                "reason": f"Invoice amount (${val_amount:,.2f}) exceeds global limit threshold of (${amount_limit:,.2f})",
                "evidence": f"Invoice amount ${val_amount:,.2f} > Policy Limit ${amount_limit:,.2f}",
                "severity": "MEDIUM"
            })

    # Rule 4: Category-Specific Limit Check
    cat = str(invoice.get("category") or "").strip().lower()
    if cat in CATEGORY_LIMITS and val_amount is not None and val_amount > 0:
        cat_limit = CATEGORY_LIMITS[cat]
        if val_amount > cat_limit:
            violations.append({
                "invoice_id": inv_id,
                "rule": "Category Policy Threshold Check",
                "status": "REVIEW",
                "reason": f"Invoice amount (${val_amount:,.2f}) exceeds policy limit for category '{invoice.get('category')}' (${cat_limit:,.2f})",
                "evidence": f"Category: '{invoice.get('category')}', Amount: ${val_amount:,.2f}, Category Limit: ${cat_limit:,.2f}",
                "severity": "MEDIUM"
            })

    # Rule 5: Date Format and Weekend Check
    inv_date = invoice.get("invoice_date")
    if inv_date:
        is_valid, dt_obj = validate_date(inv_date)
        if not is_valid:
            violations.append({
                "invoice_id": inv_id,
                "rule": "Invalid Date Format Check",
                "status": "REVIEW",
                "reason": f"Unrecognized or invalid date format: '{inv_date}'",
                "evidence": f"Invoice Date string: '{inv_date}'",
                "severity": "LOW"
            })
        elif dt_obj and dt_obj.weekday() in (5, 6): # Saturday = 5, Sunday = 6
            violations.append({
                "invoice_id": inv_id,
                "rule": "Off-Hours Weekend Date Warning",
                "status": "REVIEW",
                "reason": f"Invoice date '{inv_date}' falls on a weekend ({dt_obj.strftime('%A')})",
                "evidence": f"Date: {inv_date} ({dt_obj.strftime('%A')})",
                "severity": "LOW"
            })
        
    return violations
