"""
High-Risk Entity & Sanctions Watchlist Screening Service
Uses RapidFuzz token-sort similarity to screen invoice vendors against restricted,
sanctioned, or fraudulent counterparty databases (OFAC, PEP, Internal Blacklists).
"""

from typing import List, Dict, Any, Tuple, Optional
from rapidfuzz import fuzz

# Default enterprise high-risk / sanctioned entity watchlist
DEFAULT_WATCHLIST: List[Dict[str, Any]] = [
    {
        "entity_name": "Apex Shell Holdings Ltd",
        "reason": "Unregistered offshore shell entity flagged for procurement fraud",
        "risk_level": "CRITICAL",
        "category": "Shell Company / Money Laundering"
    },
    {
        "entity_name": "Offshore Logistics Corp",
        "reason": "Disallowed intermediary without verified physical operations",
        "risk_level": "HIGH",
        "category": "Procurement Intermediary"
    },
    {
        "entity_name": "Phantom Advisory Group LLC",
        "reason": "Fabricated consulting receipts and employee kickback scheme",
        "risk_level": "CRITICAL",
        "category": "Kickback Risk"
    },
    {
        "entity_name": "Global Sanctioned Trading AG",
        "reason": "OFAC / International sanctions restricted trade counterparty",
        "risk_level": "CRITICAL",
        "category": "International Sanctions (OFAC)"
    },
    {
        "entity_name": "Panama Express Courier SA",
        "reason": "Unlicensed high-risk freight carrier under investigation",
        "risk_level": "HIGH",
        "category": "Restricted Logistics"
    }
]

# Active runtime watchlist (can be appended or modified dynamically)
ACTIVE_WATCHLIST: List[Dict[str, Any]] = list(DEFAULT_WATCHLIST)

def get_watchlist() -> List[Dict[str, Any]]:
    return ACTIVE_WATCHLIST

def add_to_watchlist(entity_name: str, reason: str, risk_level: str = "HIGH", category: str = "Custom Watchlist") -> Dict[str, Any]:
    item = {
        "entity_name": entity_name.strip(),
        "reason": reason.strip(),
        "risk_level": risk_level.upper(),
        "category": category.strip()
    }
    # Avoid duplicate exact names
    for existing in ACTIVE_WATCHLIST:
        if existing["entity_name"].lower() == item["entity_name"].lower():
            existing.update(item)
            return existing
    ACTIVE_WATCHLIST.append(item)
    return item

def remove_from_watchlist(entity_name: str) -> bool:
    global ACTIVE_WATCHLIST
    initial_len = len(ACTIVE_WATCHLIST)
    ACTIVE_WATCHLIST = [e for e in ACTIVE_WATCHLIST if e["entity_name"].lower() != entity_name.strip().lower()]
    return len(ACTIVE_WATCHLIST) < initial_len

def screen_vendor(vendor_name: Optional[str], threshold: float = 80.0) -> Tuple[bool, Optional[Dict[str, Any]], float]:
    """
    Screens a vendor against the active watchlist using RapidFuzz token sort ratio.
    Returns:
        (is_matched, matched_watchlist_item, similarity_score)
    """
    if not vendor_name or str(vendor_name).strip().lower() in ["none", "nan", "null", ""]:
        return False, None, 0.0

    v_clean = str(vendor_name).strip()
    best_match = None
    best_score = 0.0

    for item in ACTIVE_WATCHLIST:
        target = item["entity_name"]
        score = fuzz.token_sort_ratio(v_clean.lower(), target.lower())
        if score > best_score:
            best_score = score
            best_match = item

    if best_score >= threshold and best_match:
        return True, best_match, round(best_score, 1)

    return False, None, round(best_score, 1)
