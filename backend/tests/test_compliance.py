import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.rule_engine import evaluate_invoice_rules
from services.duplicate_detector import detect_duplicates
from services.profiler import generate_data_profile
from services.ai_explainer import generate_ai_explanation
from services.data_loader import auto_map_columns

def test_auto_map_columns():
    cols = ["Invoice Number", "Vendor", "Total Amount", "Date"]
    mapping = auto_map_columns(cols)
    assert mapping["invoice_id"] == "Invoice Number"
    assert mapping["vendor_name"] == "Vendor"
    assert mapping["amount"] == "Total Amount"
    assert mapping["invoice_date"] == "Date"

def test_rule_engine_valid():
    inv = {
        "invoice_id": "INV-001",
        "vendor_name": "Test Vendor",
        "invoice_date": "2026-10-01",
        "amount": 100.00
    }
    violations = evaluate_invoice_rules(inv, amount_limit=5000.0)
    assert len(violations) == 0

def test_rule_engine_over_limit():
    inv = {
        "invoice_id": "INV-002",
        "vendor_name": "Test Vendor",
        "invoice_date": "2026-10-01",
        "amount": 7500.00
    }
    violations = evaluate_invoice_rules(inv, amount_limit=5000.0)
    assert len(violations) == 1
    assert violations[0]["rule"] == "Global Amount Limit Policy Check"
    assert violations[0]["status"] == "REVIEW"

def test_rule_engine_missing_field():
    inv = {
        "invoice_id": "INV-003",
        "vendor_name": None,
        "invoice_date": "2026-10-01",
        "amount": 100.00
    }
    violations = evaluate_invoice_rules(inv, amount_limit=5000.0)
    assert len(violations) >= 1
    assert violations[0]["rule"] == "Required Fields Check"

def test_duplicate_detector_exact():
    invoices = [
        {"invoice_id": "INV-100", "vendor_name": "Acme", "amount": 250.0, "invoice_date": "2026-10-01"},
        {"invoice_id": "INV-100", "vendor_name": "Acme", "amount": 250.0, "invoice_date": "2026-10-01"}
    ]
    violations = detect_duplicates(invoices)
    assert len(violations) >= 1

def test_duplicate_detector_fuzzy():
    invoices = [
        {"invoice_id": "INV-101", "vendor_name": "Acme Corporation", "amount": 300.0, "invoice_date": "2026-10-01"},
        {"invoice_id": "INV-102", "vendor_name": "ACME Corp", "amount": 300.0, "invoice_date": "2026-10-01"}
    ]
    violations = detect_duplicates(invoices, similarity_threshold=70.0)
    assert len(violations) >= 1
    assert "Similar Duplicate Vendor Check" in [v["rule"] for v in violations]

def test_ai_explainer_fallback():
    violation = {
        "invoice_id": "INV-999",
        "rule": "Amount Limit Policy Check",
        "status": "REVIEW",
        "reason": "Exceeds $5,000 threshold",
        "evidence": "Amount = 8000",
        "severity": "MEDIUM"
    }
    explanation = generate_ai_explanation(violation)
    assert "Amount Limit Policy Check" in explanation
    assert "MEDIUM" in explanation

def test_split_transaction_detector():
    from services.split_detector import detect_split_transactions
    invoices = [
        {"invoice_id": "INV-S1", "vendor_name": "Tech Corp", "amount": 4800.0, "invoice_date": "2026-10-01"},
        {"invoice_id": "INV-S2", "vendor_name": "Tech Corp", "amount": 4900.0, "invoice_date": "2026-10-01"}
    ]
    violations = detect_split_transactions(invoices, amount_limit=5000.0)
    assert len(violations) == 2
    assert violations[0]["rule"] == "Split Transaction / Threshold Evasion Check"

def test_vendor_analytics():
    from services.vendor_analytics import analyze_vendor_risk
    invoices = [
        {"invoice_id": "I1", "vendor_name": "Vendor Alpha", "amount": 100.0, "risk_score": 50},
        {"invoice_id": "I2", "vendor_name": "Vendor Beta", "amount": 200.0, "risk_score": 0}
    ]
    exceptions = [{"invoice_id": "I1"}]
    analysis = analyze_vendor_risk(invoices, exceptions)
    assert len(analysis) == 2
    assert analysis[0]["vendor_name"] == "Vendor Alpha"
    assert analysis[0]["risk_rating"] == "HIGH"

def test_clean_amount_currency():
    from services.data_loader import clean_amount_value
    assert clean_amount_value("$1,540.20") == 1540.20
    assert clean_amount_value("€2,500.00") == 2500.00
    assert clean_amount_value("   450.50  ") == 450.50
    assert clean_amount_value("invalid_num") is None
    assert clean_amount_value(None) is None

def test_benford_law():
    from services.benford import analyze_benford_law
    invoices = [
        {"amount": 120.0}, {"amount": 150.0}, {"amount": 190.0},
        {"amount": 210.0}, {"amount": 340.0}, {"amount": 410.0}
    ]
    result = analyze_benford_law(invoices)
    assert result["total_analyzed"] == 6
    assert "conformity" in result
    assert len(result["distribution"]) == 9



