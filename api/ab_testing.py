"""
A/B Testing for Model Comparison

Implements 50/50 split based on user_id hash.
Tracks metrics for each variant to enable statistical comparison.

Variant A: LSTM (control)
Variant B: Random Forest (treatment)
"""

import hashlib
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# A/B Test Configuration
AB_TEST_ENABLED = os.getenv('AB_TEST_ENABLED', 'true').lower() == 'true'
CONTROL_MODEL = 'lstm'
TREATMENT_MODEL = 'randomforest'


def get_ab_variant(user_id: str) -> str:
    """
    Assign user to A/B test variant based on user_id hash.
    
    Uses consistent hashing so same user always gets same variant.
    
    Args:
        user_id: User identifier
    
    Returns:
        'A' for control (LSTM) or 'B' for treatment (Random Forest)
    """
    if not AB_TEST_ENABLED:
        return 'A'  # Default to control if A/B testing disabled
    
    # Hash user_id and use last byte for 50/50 split
    hash_bytes = hashlib.md5(user_id.encode()).digest()
    hash_value = hash_bytes[-1]
    
    # Even = A, Odd = B (50/50 split)
    variant = 'A' if hash_value % 2 == 0 else 'B'
    
    logger.debug(f"User {user_id} assigned to variant {variant}")
    return variant


def get_model_for_variant(variant: str) -> str:
    """
    Get model name for a given variant.
    
    Args:
        variant: 'A' or 'B'
    
    Returns:
        Model name
    """
    return CONTROL_MODEL if variant == 'A' else TREATMENT_MODEL


def log_ab_result(
    user_id: str,
    variant: str,
    model: str,
    symbols: list,
    predictions: Dict[str, Any],
    latency_ms: float,
    success: bool,
    error: Optional[str] = None
):
    """
    Log A/B test result for analysis.
    
    Logs to file for later statistical analysis.
    
    Args:
        user_id: User identifier
        variant: 'A' or 'B'
        model: Model used
        symbols: Stock symbols requested
        predictions: Prediction results
        latency_ms: Processing latency
        success: Whether request succeeded
        error: Error message if failed
    """
    result = {
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id,
        "variant": variant,
        "model": model,
        "symbols": symbols,
        "num_predictions": len(predictions) if predictions else 0,
        "latency_ms": round(latency_ms, 2),
        "success": success,
        "error": error
    }
    
    # Count successful predictions (non-error results)
    if success and predictions:
        result["successful_predictions"] = len([
            p for p in predictions.values() 
            if isinstance(p, dict) and 'error' not in p
        ])
    else:
        result["successful_predictions"] = 0
    
    # Log to file
    try:
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f"ab_test_results_{datetime.now().strftime('%Y%m%d')}.jsonl")
        
        with open(log_file, 'a') as f:
            f.write(json.dumps(result) + '\n')
            
        logger.debug(f"A/B result logged for user {user_id}, variant {variant}")
        
    except Exception as e:
        logger.warning(f"Failed to log A/B result: {e}")


def get_ab_metrics(date: Optional[str] = None) -> Dict[str, Any]:
    """
    Calculate A/B test metrics from logs.
    
    Args:
        date: Date string (YYYYMMDD) or None for today
    
    Returns:
        Dictionary with metrics for each variant
    """
    if date is None:
        date = datetime.now().strftime('%Y%m%d')
    
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    log_file = os.path.join(log_dir, f"ab_test_results_{date}.jsonl")
    
    if not os.path.exists(log_file):
        return {
            "error": f"No A/B test results found for {date}",
            "date": date
        }
    
    # Initialize metrics
    metrics = {
        'A': {
            'total_requests': 0,
            'successful_requests': 0,
            'total_predictions': 0,
            'successful_predictions': 0,
            'latencies': [],
            'errors': 0
        },
        'B': {
            'total_requests': 0,
            'successful_requests': 0,
            'total_predictions': 0,
            'successful_predictions': 0,
            'latencies': [],
            'errors': 0
        }
    }
    
    # Read and aggregate results
    try:
        with open(log_file, 'r') as f:
            for line in f:
                result = json.loads(line)
                variant = result.get('variant')
                
                if variant not in metrics:
                    continue
                
                metrics[variant]['total_requests'] += 1
                
                if result.get('success'):
                    metrics[variant]['successful_requests'] += 1
                    metrics[variant]['total_predictions'] += result.get('num_predictions', 0)
                    metrics[variant]['successful_predictions'] += result.get('successful_predictions', 0)
                    metrics[variant]['latencies'].append(result.get('latency_ms', 0))
                else:
                    metrics[variant]['errors'] += 1
        
        # Calculate summary statistics
        summary = {}
        for variant in ['A', 'B']:
            m = metrics[variant]
            
            # Success rate
            success_rate = (m['successful_requests'] / m['total_requests'] * 100) if m['total_requests'] > 0 else 0
            
            # Average latency
            avg_latency = sum(m['latencies']) / len(m['latencies']) if m['latencies'] else 0
            
            # P95 latency
            if m['latencies']:
                sorted_latencies = sorted(m['latencies'])
                p95_idx = int(len(sorted_latencies) * 0.95)
                p95_latency = sorted_latencies[p95_idx] if p95_idx < len(sorted_latencies) else sorted_latencies[-1]
            else:
                p95_latency = 0
            
            model = get_model_for_variant(variant)
            
            summary[variant] = {
                'model': model,
                'total_requests': m['total_requests'],
                'successful_requests': m['successful_requests'],
                'success_rate': round(success_rate, 2),
                'total_predictions': m['total_predictions'],
                'successful_predictions': m['successful_predictions'],
                'errors': m['errors'],
                'avg_latency_ms': round(avg_latency, 2),
                'p95_latency_ms': round(p95_latency, 2)
            }
        
        return {
            'date': date,
            'test_config': {
                'control': CONTROL_MODEL,
                'treatment': TREATMENT_MODEL
            },
            'results': summary
        }
        
    except Exception as e:
        logger.error(f"Error calculating A/B metrics: {e}")
        return {
            "error": str(e),
            "date": date
        }
