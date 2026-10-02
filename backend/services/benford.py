import math
from typing import List, Dict, Any

# Theoretical Benford's Law Leading Digit Probabilities
BENFORD_PROBABILITIES = {
    1: 0.3010,
    2: 0.1761,
    3: 0.1249,
    4: 0.0969,
    5: 0.0792,
    6: 0.0669,
    7: 0.0580,
    8: 0.0512,
    9: 0.0458
}

def get_leading_digit(amount: float) -> int:
    try:
        s = f"{abs(float(amount)):.2f}".replace("0.", "").replace(".", "").lstrip("0")
        if s and s[0].isdigit():
            digit = int(s[0])
            if 1 <= digit <= 9:
                return digit
    except (ValueError, TypeError):
        pass
    return None

def analyze_benford_law(invoices: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Applies Benford's Law analysis on invoice amounts to detect statistical fabrication.
    Computes observed vs expected digit distribution and Mean Absolute Deviation (MAD).
    """
    counts = {d: 0 for d in range(1, 10)}
    total_valid = 0
    
    for inv in invoices:
        amt = inv.get("amount")
        if amt is not None:
            digit = get_leading_digit(amt)
            if digit:
                counts[digit] += 1
                total_valid += 1

    if total_valid == 0:
        return {
            "total_analyzed": 0,
            "mad_score": 0.0,
            "conformity": "Insufficient Data",
            "distribution": []
        }

    distribution = []
    mad_sum = 0.0
    
    for d in range(1, 10):
        actual_pct = round(counts[d] / total_valid, 4)
        expected_pct = BENFORD_PROBABILITIES[d]
        diff = abs(actual_pct - expected_pct)
        mad_sum += diff
        
        distribution.append({
            "digit": d,
            "count": counts[d],
            "actual_pct": round(actual_pct * 100, 2),
            "expected_pct": round(expected_pct * 100, 2),
            "deviation": round(diff * 100, 2)
        })

    mad_score = round(mad_sum / 9.0, 4)
    
    # Standard Conformity Classification based on MAD
    if mad_score < 0.006:
        conformity = "Close Conformity (Normal Distribution)"
    elif mad_score < 0.012:
        conformity = "Acceptable Conformity"
    elif mad_score < 0.015:
        conformity = "Marginal Conformity (Slight Anomaly)"
    else:
        conformity = "Non-Conformity (High Risk of Manipulation / Fabrication)"

    return {
        "total_analyzed": total_valid,
        "mad_score": mad_score,
        "conformity": conformity,
        "distribution": distribution
    }
