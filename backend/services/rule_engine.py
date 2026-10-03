from typing import List, Dict, Any, Tuple, Optional
import datetime

DEFAULT_AMOUNT_LIMIT = 5000.0

CATEGORY_LIMITS = {
    "meals & entertainment": 250.0,
    "meals": 250.0,
    "office supplies": 1000.0,
    "travel & lodging": 3000.0,
    "travel": 3000.0,
    "consulting": 8000.0
}

def validate_date(date_val: Any) -> Tuple[bool, Optional[datetime.date]]:
    if date_val is None:
        return False, None
    if isinstance(date_val, datetime.datetime):
        return True, date_val.date()
    if isinstance(date_val, datetime.date):
        return True, date_val

    s = str(date_val).strip()
    if not s or s.lower() in ["none", "nan", "nat", ""]:
        return False, None

    # Handle ISO formats like 2026-10-01T00:00:00 or with space
    s_clean = s.split("T")[0].split(" ")[0]

    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y", "%m-%d-%Y", "%Y%m%d"):
        try:
            dt = datetime.datetime.strptime(s_clean, fmt).date()
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

def evaluate_invoice_rules(invoice: Dict[str, Any], amount_limit: float = DEFAULT_AMOUNT_LIMIT, category_limits: Optional[Dict[str, float]] = None) -> List[Dict[str, Any]]:
    violations = []
    inv_id = str(invoice.get("invoice_id") or "UNKNOWN")
    
    # Rule 1: Required Fields Validation
    required_fields = ["vendor_name", "amount", "invoice_date"]
    missing = [field for field in required_fields if invoice.get(field) is None or str(invoice.get(field)).strip() in ["None", "nan", ""]]
    
    # Also check if original invoice_id was missing
    if invoice.get("_missing_id") or not invoice.get("invoice_id") or str(invoice.get("invoice_id")).strip() in ["None", "nan", "", "UNKNOWN"]:
        missing.insert(0, "invoice_id")

    if missing:
        violations.append({
            "invoice_id": inv_id,
            "rule": "Required Fields Check",
            "status": "FAIL",
            "reason": f"Missing required field(s): {', '.join(missing)}",
            "evidence": f"Provided record lacks values for: {missing}",
            "citation": f"AP Policy Reference: Mandatory field(s) missing from invoice ({', '.join(missing)})",
            "severity": "HIGH"
        })
        
    # Rule 2: Amount Validation (Numeric, Multi-Currency Normalization & > 0)
    amount = invoice.get("amount")
    val_amount = None
    if amount is not None:
        try:
            from services.currency import detect_and_normalize_currency
            usd_amt, detected_curr, orig_amt = detect_and_normalize_currency(amount)
            if usd_amt is not None:
                val_amount = usd_amt
                if val_amount <= 0:
                    violations.append({
                        "invoice_id": inv_id,
                        "rule": "Invalid Amount Check",
                        "status": "FAIL",
                        "reason": f"Invoice amount must be positive. Found ${val_amount:.2f} ({detected_curr})",
                        "evidence": f"Amount = {val_amount} ({detected_curr})",
                        "citation": f"AP Policy Reference: Non-positive invoice amount (${val_amount:.2f})",
                        "severity": "HIGH"
                    })
            else:
                violations.append({
                    "invoice_id": inv_id,
                    "rule": "Non-numeric Amount Check",
                    "status": "FAIL",
                    "reason": "Invoice amount is non-numeric or unparseable",
                    "evidence": f"Amount raw value: {amount}",
                    "citation": f"AP Policy Reference: Unparseable amount format: '{amount}'",
                    "severity": "HIGH"
                })
        except Exception:
            violations.append({
                "invoice_id": inv_id,
                "rule": "Non-numeric Amount Check",
                "status": "FAIL",
                "reason": "Invoice amount is non-numeric or unparseable",
                "evidence": f"Amount raw value: {amount}",
                "citation": f"AP Policy Reference: Unparseable amount format: '{amount}'",
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
                "citation": f"AP Policy Reference: Global approval threshold ${amount_limit:,.2f} exceeded by ${(val_amount - amount_limit):,.2f}",
                "severity": "MEDIUM"
            })

    # Rule 4: Category-Specific Limit Check
    active_limits = category_limits if category_limits is not None else CATEGORY_LIMITS
    cat = str(invoice.get("category") or "").strip().lower()
    if cat in active_limits and val_amount is not None and val_amount > 0:
        cat_limit = active_limits[cat]
        if val_amount > cat_limit:
            violations.append({
                "invoice_id": inv_id,
                "rule": "Category Policy Threshold Check",
                "status": "REVIEW",
                "reason": f"Invoice amount (${val_amount:,.2f}) exceeds policy limit for category '{invoice.get('category')}' (${cat_limit:,.2f})",
                "evidence": f"Category: '{invoice.get('category')}', Amount: ${val_amount:,.2f}, Category Limit: ${cat_limit:,.2f}",
                "citation": f"AP Policy Reference: Category '{invoice.get('category')}' ceiling ${cat_limit:,.2f} exceeded by ${(val_amount - cat_limit):,.2f}",
                "severity": "MEDIUM"
            })

    # Rule 5: Date Format, Weekend & Future Date Check
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
                "citation": f"AP Policy Reference: Invalid date syntax '{inv_date}'",
                "severity": "LOW"
            })
        elif dt_obj:
            today = datetime.date.today()
            # Future date check (more than 7 days ahead)
            if dt_obj > today + datetime.timedelta(days=7):
                violations.append({
                    "invoice_id": inv_id,
                    "rule": "Future-Dated Invoice Warning",
                    "status": "REVIEW",
                    "reason": f"Invoice date '{inv_date}' is set in the future relative to system time",
                    "evidence": f"Invoice Date: {inv_date} > System Date: {today}",
                    "citation": f"AP Policy Reference: Forward-dated claim ({inv_date})",
                    "severity": "LOW"
                })
            # Weekend check
            elif dt_obj.weekday() in (5, 6): # Saturday = 5, Sunday = 6
                violations.append({
                    "invoice_id": inv_id,
                    "rule": "Off-Hours Weekend Date Warning",
                    "status": "REVIEW",
                    "reason": f"Invoice date '{inv_date}' falls on a weekend ({dt_obj.strftime('%A')})",
                    "evidence": f"Date: {inv_date} ({dt_obj.strftime('%A')})",
                    "citation": f"AP Policy Reference: Weekend expenditure ({dt_obj.strftime('%A')}) requiring justification",
                    "severity": "LOW"
                })

    # Rule 6: High-Risk & Sanctions Watchlist Screening
    vendor_name = invoice.get("vendor_name")
    if vendor_name:
        from services.watchlist import screen_vendor
        is_watched, match_info, sim_score = screen_vendor(vendor_name)
        if is_watched and match_info:
            violations.append({
                "invoice_id": inv_id,
                "rule": "Sanctions & High-Risk Entity Watchlist Screening",
                "status": "FAIL",
                "reason": f"Vendor '{vendor_name}' matches watched high-risk entity '{match_info['entity_name']}' ({sim_score}% similarity). Reason: {match_info['reason']}",
                "evidence": f"Watchlist Category: {match_info['category']}, Risk Level: {match_info['risk_level']}, Similarity: {sim_score}%",
                "citation": f"Sanctions List Citation: Matched restricted entity '{match_info['entity_name']}' ({match_info['category']}, {match_info['risk_level']}) at {sim_score}% token similarity",
                "severity": "HIGH"
            })

    # Rule 7: Round-Number Forensic Anomaly Check
    if val_amount is not None and val_amount >= 1000.0:
        non_itemized_cats = ["consulting", "advisory", "meals", "meals & entertainment", "travel", "travel & lodging", "services", "marketing"]
        if cat in non_itemized_cats and (val_amount % 500 == 0):
            violations.append({
                "invoice_id": inv_id,
                "rule": "Round-Number Forensic Anomaly Check",
                "status": "REVIEW",
                "reason": f"Invoice amount (${val_amount:,.2f}) in category '{invoice.get('category')}' is an exact round number without itemized cents, a common indicator of estimated or fabricated claims.",
                "evidence": f"Amount: ${val_amount:,.2f} (multiple of $500), Category: '{invoice.get('category')}'",
                "citation": f"Forensic Accounting Citation: Unitemized round multiple of $500 (${val_amount:,.2f}) in discretionary category '{invoice.get('category')}'",
                "severity": "MEDIUM"
            })
        
    return violations
