"""
Multi-Currency Normalization Service
Detects foreign currency symbols and ISO codes, converting transactions to USD 
at standard benchmark exchange rates for uniform compliance auditing.
"""

import re
from typing import Tuple, Optional

# Standard benchmark foreign exchange rates to USD
FX_RATES_TO_USD = {
    "USD": 1.0,
    "EUR": 1.08,    # 1 EUR = $1.08 USD
    "GBP": 1.28,    # 1 GBP = $1.28 USD
    "CAD": 0.74,    # 1 CAD = $0.74 USD
    "AUD": 0.65,    # 1 AUD = $0.65 USD
    "INR": 0.012,   # 1 INR = $0.012 USD
    "JPY": 0.0067,  # 1 JPY = $0.0067 USD
    "CHF": 1.13,    # 1 CHF = $1.13 USD
}

CURRENCY_SYMBOLS = {
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
    "¥": "JPY",
    "₹": "INR",
    "C$": "CAD",
    "A$": "AUD"
}

def detect_and_normalize_currency(raw_val: any, default_currency: str = "USD") -> Tuple[Optional[float], str, Optional[float]]:
    """
    Detects currency symbol/code and returns (usd_amount, detected_currency, original_amount).
    Example:
        "€1,500.00" -> (1620.0, "EUR", 1500.0)
        "100.50"    -> (100.5, "USD", 100.5)
    """
    if raw_val is None:
        return None, default_currency, None

    if isinstance(raw_val, (int, float)):
        val = float(raw_val)
        return round(val, 2), default_currency, round(val, 2)

    s = str(raw_val).strip()
    detected_curr = default_currency

    # Check for prefix or suffix currency symbols
    for sym, curr in CURRENCY_SYMBOLS.items():
        if sym in s:
            detected_curr = curr
            s = s.replace(sym, "")
            break

    # Check for 3-letter currency codes
    for code in FX_RATES_TO_USD.keys():
        match = re.search(r'\b' + code + r'\b', s, re.IGNORECASE)
        if match:
            detected_curr = code.upper()
            s = re.sub(r'\b' + code + r'\b', '', s, flags=re.IGNORECASE)
            break

    # Clean remaining string of commas, spaces, quotes
    clean_str = re.sub(r'[^\d.-]', '', s)
    if not clean_str:
        return None, detected_curr, None

    try:
        orig_amount = float(clean_str)
        rate = FX_RATES_TO_USD.get(detected_curr, 1.0)
        usd_amount = round(orig_amount * rate, 2)
        return usd_amount, detected_curr, orig_amount
    except ValueError:
        return None, detected_curr, None
