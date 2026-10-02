from typing import List, Dict, Any

def get_demo_dataset() -> List[Dict[str, Any]]:
    """
    Returns controlled demo test cases clearly labeled as 'Kaggle-derived Demo Case'.
    Contains specific compliance test scenarios.
    """
    return [
        {
            "invoice_id": "INV-1001",
            "vendor_name": "Microsoft Azure Services",
            "invoice_date": "2026-09-15",
            "amount": 1420.50,
            "category": "Cloud Infrastructure",
            "employee_id": "EMP-802",
            "description": "Monthly cloud hosting & cognitive services",
            "source": "Kaggle-derived Demo Case"
        },
        {
            "invoice_id": "INV-1002",
            "vendor_name": "Acme Industrial Supplies",
            "invoice_date": "2026-09-18",
            "amount": 450.00,
            "category": "Office Supplies",
            "employee_id": "EMP-415",
            "description": "Ergonomic desk chairs & monitors",
            "source": "Kaggle-derived Demo Case"
        },
        # Controlled Anomaly 1: Similar Duplicate (Fuzzy Vendor Match)
        {
            "invoice_id": "INV-1003",
            "vendor_name": "ACME Corporation Supplies",
            "invoice_date": "2026-09-18",
            "amount": 450.00,
            "category": "Office Equipment",
            "employee_id": "EMP-415",
            "description": "Ergonomic desk chairs & monitors",
            "source": "Kaggle-derived Demo Case"
        },
        # Controlled Anomaly 2: Over-Limit Amount (> $5,000 policy limit)
        {
            "invoice_id": "INV-1004",
            "vendor_name": "Enterprise Server Hardware Ltd",
            "invoice_date": "2026-09-20",
            "amount": 12500.00,
            "category": "Capital Expenditure",
            "employee_id": "EMP-101",
            "description": "Rack server cluster upgrade",
            "source": "Kaggle-derived Demo Case"
        },
        # Controlled Anomaly 3: Exact Duplicate of INV-1004
        {
            "invoice_id": "INV-1004",
            "vendor_name": "Enterprise Server Hardware Ltd",
            "invoice_date": "2026-09-20",
            "amount": 12500.00,
            "category": "Capital Expenditure",
            "employee_id": "EMP-101",
            "description": "Rack server cluster upgrade",
            "source": "Kaggle-derived Demo Case"
        },
        # Controlled Anomaly 4: Negative Invalid Amount
        {
            "invoice_id": "INV-1005",
            "vendor_name": "Global Telecom Systems",
            "invoice_date": "2026-09-22",
            "amount": -150.00,
            "category": "Utilities",
            "employee_id": "EMP-309",
            "description": "Erroneous credit line entry",
            "source": "Kaggle-derived Demo Case"
        },
        # Controlled Anomaly 5: Missing Required Field (Vendor Name is None)
        {
            "invoice_id": "INV-1006",
            "vendor_name": None,
            "invoice_date": "2026-09-25",
            "amount": 890.00,
            "category": "Consulting",
            "employee_id": "EMP-771",
            "description": "External software audit consulting",
            "source": "Kaggle-derived Demo Case"
        },
        {
            "invoice_id": "INV-1007",
            "vendor_name": "Delta Airlines Corporate",
            "invoice_date": "2026-09-28",
            "amount": 620.00,
            "category": "Travel & Lodging",
            "employee_id": "EMP-204",
            "description": "Flight tickets for tech conference",
            "source": "Kaggle-derived Demo Case"
        }
    ]
