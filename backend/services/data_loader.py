import os
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional

INTERNAL_SCHEMA = [
    "invoice_id",
    "vendor_name",
    "invoice_date",
    "amount",
    "category",
    "employee_id",
    "description"
]

COLUMN_ALIASES = {
    "invoice_id": ["invoice_id", "invoice_number", "invoiceno", "inv_num", "id", "bill_id", "invoice_no", "inv_id"],
    "vendor_name": ["vendor_name", "vendor", "supplier", "merchant", "company", "biller", "vendor_id", "payee"],
    "invoice_date": ["invoice_date", "date", "bill_date", "transaction_date", "inv_date", "issue_date", "posting_date"],
    "amount": ["amount", "total_amount", "total", "cost", "sum", "grand_total", "price", "invoice_amount", "net_amount", "gross_amount"],
    "category": ["category", "expense_category", "type", "expense_type", "department", "cost_center", "account"],
    "employee_id": ["employee_id", "emp_id", "user_id", "submitted_by", "claimed_by", "requestor", "creator"],
    "description": ["description", "details", "item_description", "memo", "notes", "particulars", "line_item"]
}

def clean_amount_value(val: Any) -> Optional[float]:
    """
    Safely sanitizes amounts containing currency signs ($, €, £), commas, quotes, or whitespace.
    Avoids NaN conversion traps in pandas.
    """
    if pd.isna(val) or val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    for char in ["$", "€", "£", "¥", "₹", ",", '"', "'"]:
        s = s.replace(char, "")
    try:
        return float(s)
    except (ValueError, TypeError):
        return None

def auto_map_columns(df_columns: List[str]) -> Dict[str, Optional[str]]:
    mapping = {}
    normalized_source_cols = {col.lower().replace(" ", "_").replace("-", "_").replace(".", "_"): col for col in df_columns}
    
    for target_field, aliases in COLUMN_ALIASES.items():
        matched_source = None
        for alias in aliases:
            if alias in normalized_source_cols:
                matched_source = normalized_source_cols[alias]
                break
        mapping[target_field] = matched_source
        
    return mapping

def load_and_process_dataset(file_path: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Dataset file not found at: {file_path}")
        
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".csv":
        # Handle potential encoding issues (UTF-8, Latin-1)
        try:
            df_raw = pd.read_csv(file_path, encoding="utf-8")
        except UnicodeDecodeError:
            df_raw = pd.read_csv(file_path, encoding="latin1")
    elif ext in [".xls", ".xlsx"]:
        df_raw = pd.read_excel(file_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}")
        
    # Drop completely blank rows
    df_raw = df_raw.dropna(how="all")
    
    column_mapping = auto_map_columns(df_raw.columns.tolist())
    
    df_processed = pd.DataFrame()
    for target_field, source_col in column_mapping.items():
        if source_col and source_col in df_raw.columns:
            df_processed[target_field] = df_raw[source_col]
        else:
            df_processed[target_field] = None
            
    # Clean numeric fields with robust sanitizer
    if "amount" in df_processed.columns:
        df_processed["amount"] = df_processed["amount"].apply(clean_amount_value)
        
    # Clean string fields & normalize 'nan' strings
    for str_col in ["invoice_id", "vendor_name", "category", "employee_id", "description", "invoice_date"]:
        if str_col in df_processed.columns:
            df_processed[str_col] = df_processed[str_col].apply(
                lambda x: None if pd.isna(x) or str(x).strip().lower() in ["nan", "none", "null", ""] else str(x).strip()
            )

    metadata = {
        "source_file": file_path,
        "original_rows": len(df_raw),
        "original_cols": len(df_raw.columns),
        "mapped_schema": column_mapping,
        "unmapped_target_fields": [k for k, v in column_mapping.items() if v is None]
    }
    
    return df_processed, metadata
