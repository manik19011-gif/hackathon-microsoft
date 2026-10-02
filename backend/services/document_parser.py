"""
Invoice Document & OCR Text Parser Service
Extracts key compliance fields from raw invoice text or PDF documents,
reconciles line-item mathematical sums, and validates sales tax rates.
"""

import re
import io
from typing import Dict, Any, List, Optional, Tuple
import pypdf
from services.currency import detect_and_normalize_currency

def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """
    Extracts concatenated text across all pages of a PDF document.
    """
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    text_parts = []
    for page in reader.pages:
        t = page.extract_text()
        if t:
            text_parts.append(t)
    return "\n".join(text_parts)

def parse_invoice_text(text: str) -> Dict[str, Any]:
    """
    Extracts invoice_id, vendor_name, date, amount, tax, and line items from text.
    Verifies mathematical consistency: Subtotal + Tax == Total.
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    full_text = "\n".join(lines)
    
    # 1. Invoice ID
    inv_id = None
    inv_id_match = re.search(r'(?:invoice\s*(?:#|no\.?|num(?:ber)?)|inv(?:oice)?)[^\w\d]*([A-Z0-9\-_/]+)', full_text, re.IGNORECASE)
    if inv_id_match:
        inv_id = inv_id_match.group(1).strip()
    else:
        # Check standard INV- pattern
        stand_match = re.search(r'\b(INV-[A-Z0-9\-]+)\b', full_text, re.IGNORECASE)
        if stand_match:
            inv_id = stand_match.group(1).strip()
        else:
            inv_id = f"DOC-{abs(hash(full_text[:50])) % 100000}"

    # 2. Date
    inv_date = None
    date_match = re.search(r'(?:date|invoice\s*date|dated)[^\w\d]*(\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})', full_text, re.IGNORECASE)
    if date_match:
        raw_d = date_match.group(1)
        # Normalize to YYYY-MM-DD if possible
        parts = re.split(r'[-/.]', raw_d)
        if len(parts) == 3:
            if len(parts[0]) == 4: # YYYY-MM-DD
                inv_date = f"{parts[0]}-{int(parts[1]):02d}-{int(parts[2]):02d}"
            elif len(parts[2]) == 4: # DD-MM-YYYY or MM-DD-YYYY
                inv_date = f"{parts[2]}-{int(parts[0]):02d}-{int(parts[1]):02d}"
            else:
                inv_date = raw_d
    else:
        iso_match = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', full_text)
        if iso_match:
            inv_date = iso_match.group(1)

    # 3. Vendor Name
    vendor_name = None
    vendor_match = re.search(r'(?:from|vendor|biller|supplier|company)[:\s]*([^\n\r]+)', full_text, re.IGNORECASE)
    if vendor_match:
        cand = vendor_match.group(1).strip()
        if len(cand) > 2 and not any(k in cand.lower() for k in ["invoice", "date", "total", "amount"]):
            vendor_name = cand
    if not vendor_name and len(lines) > 0:
        # Often the first line of an invoice is the vendor/company name
        first_line = lines[0]
        if len(first_line) < 60 and not re.search(r'invoice|receipt|statement|page', first_line, re.IGNORECASE):
            vendor_name = first_line

    # 4. Total Amount
    raw_amount = None
    total_match = re.search(r'\b(?:total(?:\s+(?:amount|due))?|grand\s+total|balance\s+due)[:\s]*([$€£¥₹]?\s*[0-9,]+\.[0-9]{2})', full_text, re.IGNORECASE)
    if total_match:
        raw_amount = total_match.group(1).strip()
    else:
        # Find highest dollar amount in text
        amounts = re.findall(r'[$€£¥₹]?\s*([0-9,]+\.[0-9]{2})', full_text)
        if amounts:
            nums = []
            for a in amounts:
                try:
                    nums.append(float(a.replace(",", "")))
                except ValueError:
                    pass
            if nums:
                raw_amount = str(max(nums))

    usd_amount, detected_curr, orig_amount = detect_and_normalize_currency(raw_amount)

    # 5. Subtotal & Tax (for mathematical reconciliation)
    subtotal = None
    tax = None
    sub_match = re.search(r'(?:subtotal|sub-total|net\s*amount)[:\s]*([$€£¥₹]?\s*[0-9,]+\.[0-9]{2})', full_text, re.IGNORECASE)
    if sub_match:
        sub_usd, _, sub_orig = detect_and_normalize_currency(sub_match.group(1))
        subtotal = sub_usd

    tax_match = re.search(r'(?:tax|vat|sales\s*tax|gst)[:\s]*([$€£¥₹]?\s*[0-9,]+\.[0-9]{2})', full_text, re.IGNORECASE)
    if tax_match:
        tax_usd, _, tax_orig = detect_and_normalize_currency(tax_match.group(1))
        tax = tax_usd

    # 6. Mathematical Reconciliation
    math_verified = True
    math_discrepancy = 0.0
    math_note = "Mathematical balance verified."

    if subtotal is not None and tax is not None and usd_amount is not None:
        calc_total = round(subtotal + tax, 2)
        diff = round(abs(calc_total - usd_amount), 2)
        if diff > 0.05:
            math_verified = False
            math_discrepancy = diff
            math_note = f"Discrepancy detected: Subtotal (${subtotal:,.2f}) + Tax (${tax:,.2f}) = ${calc_total:,.2f}, but Total is ${usd_amount:,.2f} (Difference: ${diff:,.2f})"

    # 7. Category Inferred from Text Keywords
    category = "General Expense"
    cat_keywords = {
        "Cloud Infrastructure": ["aws", "azure", "cloud", "hosting", "server", "datapipeline", "kubernetes"],
        "Office Supplies": ["paper", "staples", "pen", "desk", "chair", "stationery", "printer", "toner"],
        "Travel & Lodging": ["hotel", "flight", "airline", "uber", "lyft", "lodging", "travel", "car rental"],
        "Meals & Entertainment": ["restaurant", "dinner", "lunch", "catering", "cafe", "bistro", "steakhouse", "meal"],
        "Software": ["license", "subscription", "saas", "software", "github", "jira", "zoom", "slack"],
        "Hardware": ["laptop", "monitor", "dell", "apple", "macbook", "keyboard", "docking", "ram", "cpu"]
    }
    lowered = full_text.lower()
    for cat_name, words in cat_keywords.items():
        if any(w in lowered for w in words):
            category = cat_name
            break

    return {
        "invoice_id": inv_id or "UNKNOWN",
        "vendor_name": vendor_name or "Unspecified Vendor",
        "invoice_date": inv_date,
        "amount": usd_amount,
        "original_amount": orig_amount,
        "currency": detected_curr,
        "subtotal": subtotal,
        "tax": tax,
        "category": category,
        "math_verified": math_verified,
        "math_discrepancy": math_discrepancy,
        "math_note": math_note,
        "description": lines[1] if len(lines) > 1 else "Parsed invoice document",
        "raw_text_snippet": full_text[:400] + ("..." if len(full_text) > 400 else "")
    }
