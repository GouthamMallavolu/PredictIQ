"""
A/B Testing Framework for FinSightAI API
"""
import os
import json
import logging
import hashlib
from datetime import datetime
from typing import Dict, Any, List

# --- Configuration ---
LOG_FILE_PATH = "logs/ab_test_results.jsonl"
AB_TEST_ENABLED = os.environ.get("AB_TEST_ENABLED", "true").lower() == "true"

# --- Setup Logging ---
logger = logging.getLogger(__name__)
os.makedirs("logs", exist_ok=True)

# --- A/B Test Logic ---

def get_ab_variant(user_id: str) -> str:
    """
    Assigns a user to a variant (A or B) based on their user ID.

    This uses a hashing function to ensure consistent assignment.
    - Variant A: Control (e.g., Random Forest model)
    - Variant B: Challenger (e.g., LSTM model)

    Args:
        user_id: The user's identifier.

    Returns:
        'A' or 'B'.
    """
    if not isinstance(user_id, str) or not user_id:
        return 'A'  # Default to control for invalid user IDs
    
    # Hash the user ID and take the modulo to split into two groups
    hash_val = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
    if hash_val % 2 == 0:
        return 'B'  # Challenger
    else:
        return 'A'  # Control

def get_model_for_variant(variant: str) -> str:
    """Maps a variant to a specific model."""
    if variant == 'B':
        return "lstm"  # Challenger model
    else:
        return "random_forest"  # Control model

def log_ab_result(
    user_id: str,
    variant: str,
    model: str,
    symbols: List[str],
    predictions: Dict[str, Any],
    latency_ms: float,
    success: bool,
    error: str = None
):
    """
    Logs the result of an A/B test interaction to a file.

    Args:
        user_id: The user's identifier.
        variant: The assigned variant ('A' or 'B').
        model: The model used for the prediction.
        symbols: The symbols requested.
        predictions: The prediction results.
        latency_ms: The request latency in milliseconds.
        success: Whether the request was successful.
        error: The error message, if any.
    """
    if not AB_TEST_ENABLED:
        return

    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "user_id": user_id,
        "variant": variant,
        "model_used": model,
        "input_symbols": symbols,
        "latency_ms": latency_ms,
        "success": success,
        "error": error,
    }

    try:
        with open(LOG_FILE_PATH, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        logger.error(f"Failed to write A/B test log: {e}")

def get_ab_metrics(date: str = None) -> Dict[str, Any]:
    """
    Analyzes A/B test logs for a given date.
    
    This is a simplified analysis for a potential admin endpoint.
    The main analysis is done by the `scripts/analyze_ab_test.py` script.
    """
    if date is None:
        date = datetime.utcnow().strftime("%Y-%m-%d")
        
    results = {'A': [], 'B': []}
    try:
        with open(LOG_FILE_PATH, "r") as f:
            for line in f:
                entry = json.loads(line)
                if entry["timestamp"].startswith(date):
                    variant = entry.get("variant", "A")
                    results[variant].append(entry)
    except FileNotFoundError:
        return {"error": "Log file not found."}

    report = {}
    for variant, entries in results.items():
        if not entries:
            report[variant] = {"requests": 0}
            continue
        
        total_requests = len(entries)
        successful_requests = sum(1 for e in entries if e["success"])
        error_rate = (1 - (successful_requests / total_requests)) * 100 if total_requests > 0 else 0
        avg_latency = sum(e["latency_ms"] for e in entries) / total_requests if total_requests > 0 else 0
        
        report[variant] = {
            "requests": total_requests,
            "success_rate": 100 - error_rate,
            "error_rate": error_rate,
            "average_latency_ms": avg_latency
        }
    return report
