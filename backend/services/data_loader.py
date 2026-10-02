import os
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional

# Expected Internal Target Schema
INTERNAL_SCHEMA = [
    "invoice_id",
    "vendor_name",
    "invoice_date",
    "amount",
    "category",
    "employee_id",
    "description"
]

# Common column name aliases for fuzzy/heuristic schema mapping
COLUMN_ALIASES = {
    "invoice_id": ["invoice_id", "invoice_number", "invoiceno", "inv_num", "id", "bill_id", "invoice_no"],
    "vendor_name": ["vendor_name", "vendor", "supplier", "merchant", "company", "biller", "vendor_id"],
    "invoice_date": ["invoice_date", "date", "bill_date", "transaction_date", "inv_date", "issue_date"],
    "amount": ["amount", "total_amount", "total", "cost", "sum", "grand_total", "price", "invoice_amount"],
    "category": ["category", "expense_category", "type", "expense_type", "department"],
    "employee_id": ["employee_id", "emp_id", "user_id", "submitted_by", "claimed_by"],
    "description": ["description", "details", "item_description", "memo", "notes", "particulars"]
}

def auto_map_columns(df_columns: List[str]) -> Dict[str, Optional[str]]:
    """
    Map original dataset column names to the target internal schema without hardcoding.
    Returns dict mapping target_field -> source_column_name (or None if unavailable).
    """
    mapping = {}
    normalized_source_cols = {col.lower().replace(" ", "_").replace("-", "_"): col for col in df_columns}
    
    for target_field, aliases in COLUMN_ALIASES.items():
        matched_source = None
        for alias in aliases:
            if alias in normalized_source_cols:
                matched_source = normalized_source_cols[alias]
                break
        mapping[target_field] = matched_source
        
    return mapping

def load_and_process_dataset(file_path: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Loads dataset from CSV or Excel, maps columns to internal schema, handles missing values safely.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Dataset file not found at: {file_path}")
        
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".csv":
        df_raw = pd.read_csv(file_path)
    elif ext in [".xls", ".xlsx"]:
        df_raw = pd.read_excel(file_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}")
        
    column_mapping = auto_map_columns(df_raw.columns.tolist())
    
    # Construct normalized DataFrame
    df_processed = pd.DataFrame()
    for target_field, source_col in column_mapping.items():
        if source_col and source_col in df_raw.columns:
            df_processed[target_field] = df_raw[source_col]
        else:
            df_processed[target_field] = None
            
    # Clean numeric fields
    if "amount" in df_processed.columns:
        df_processed["amount"] = pd.to_numeric(df_processed["amount"], errors="coerce")
        
    # Clean string fields
    for str_col in ["invoice_id", "vendor_name", "category", "employee_id", "description"]:
        if str_col in df_processed.columns:
            df_processed[str_col] = df_processed[str_col].astype(str).replace("nan", None).replace("None", None)

    metadata = {
        "source_file": file_path,
        "original_rows": len(df_raw),
        "original_cols": len(df_raw.columns),
        "mapped_schema": column_mapping,
        "unmapped_target_fields": [k for k, v in column_mapping.items() if v is None]
    }
    
    return df_processed, metadata
