import os
from typing import Dict, Any, List, Optional

def generate_ai_explanation(violation: Dict[str, Any], invoice: Optional[Dict[str, Any]] = None) -> str:
    """
    Generates human-readable audit explanation based strictly on supplied evidence.
    Falls back to deterministic rule-based generator if Azure OpenAI is unavailable.
    """
    rule = violation.get("rule", "Compliance Check")
    reason = violation.get("reason", "Rule threshold exceeded")
    evidence = violation.get("evidence", "N/A")
    inv_id = violation.get("invoice_id", "UNKNOWN")
    severity = violation.get("severity", "MEDIUM")
    
    # Check for Azure OpenAI environment variables
    azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    
    if azure_api_key and azure_endpoint and deployment_name:
        try:
            from openai import AzureOpenAI
            client = AzureOpenAI(
                api_key=azure_api_key,
                api_version="2024-02-15-preview",
                azure_endpoint=azure_endpoint
            )
            prompt = (
                f"You are an AI Compliance Auditor. Translate the following evidence into a concise, professional audit explanation.\n"
                f"RULES: Do NOT invent facts or add unstated details.\n"
                f"Invoice ID: {inv_id}\n"
                f"Rule Violated: {rule}\n"
                f"Severity: {severity}\n"
                f"Reason: {reason}\n"
                f"Evidence: {evidence}\n"
            )
            response = client.chat.completions.create(
                model=deployment_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.2
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            # Safe fallback if API call fails
            pass
            
    # Deterministic Rule-Based Generator (Fallback)
    return (
        f"[AUDIT FINDING - {severity} SEVERITY]: Flagged by '{rule}'. "
        f"Details: {reason}. Evidence provided: {evidence}."
    )
