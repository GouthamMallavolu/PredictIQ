"""
Provenance Tracking for FinSightAI

Logs complete trace of each prediction:
- request_id: Unique request identifier
- model_version: Model version used
- data_snapshot_id: Data snapshot identifier
- pipeline_git_sha: Git commit SHA
- container_image_digest: Docker image hash
- timestamp: Request timestamp
- user_id: User identifier
- input_symbols: Input stock symbols
- predictions: Model predictions
- latency_ms: Processing latency
"""

import os
import json
import time
import subprocess
from datetime import datetime
from typing import Dict, List, Any, Optional
from kafka import KafkaProducer
import logging

logger = logging.getLogger(__name__)

# Git SHA - try to get from environment or git
def get_git_sha() -> str:
    """Get current git commit SHA"""
    # Try environment variable first (set during CI/CD)
    git_sha = os.getenv('GIT_SHA', '')
    if git_sha:
        return git_sha
    
    # Try git command
    try:
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()[:12]  # Short SHA
    except:
        pass
    
    return "unknown"


# Container image digest
def get_container_digest() -> str:
    """Get container image digest"""
    # Try environment variable (set by container runtime)
    return os.getenv('CONTAINER_IMAGE_DIGEST', os.getenv('IMAGE_TAG', 'dev'))


# Model version
def get_model_version() -> str:
    """Get current model version"""
    return os.getenv('MODEL_VERSION', 'v1.0')


# Data snapshot ID
def get_data_snapshot_id() -> str:
    """Get data snapshot identifier"""
    # This would typically come from blob storage metadata
    return os.getenv('DATA_SNAPSHOT_ID', datetime.now().strftime('%Y%m%d'))


# Kafka producer for provenance logs (singleton)
_provenance_producer: Optional[KafkaProducer] = None


def get_provenance_producer() -> Optional[KafkaProducer]:
    """Get or create Kafka producer for provenance logs"""
    global _provenance_producer
    
    if _provenance_producer is not None:
        return _provenance_producer
    
    try:
        from kafka_pipeline.config import (
            KAFKA_BROKER,
            KAFKA_USERNAME,
            KAFKA_PASSWORD
        )
        
        _provenance_producer = KafkaProducer(
            bootstrap_servers=KAFKA_BROKER,
            security_protocol='SASL_SSL',
            sasl_mechanism='PLAIN',
            sasl_plain_username=KAFKA_USERNAME,
            sasl_plain_password=KAFKA_PASSWORD,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            acks=1,
            retries=3,
            max_in_flight_requests_per_connection=5,
            request_timeout_ms=30000
        )
        
        logger.info("Provenance Kafka producer initialized")
        return _provenance_producer
        
    except Exception as e:
        logger.warning(f"Could not initialize provenance Kafka producer: {e}")
        return None


def log_provenance(
    request_id: str,
    user_id: str,
    input_symbols: List[str],
    model: str,
    predictions: Dict[str, Any],
    latency_ms: float,
    status: str = "success",
    error: Optional[str] = None
):
    """
    Log complete provenance trace for a prediction.
    
    Args:
        request_id: Unique request identifier
        user_id: User identifier
        input_symbols: List of stock symbols requested
        model: Model name used
        predictions: Prediction results
        latency_ms: Processing latency in milliseconds
        status: Request status (success/error)
        error: Error message if status is error
    """
    trace = {
        # Request identification
        "request_id": request_id,
        "user_id": user_id,
        "timestamp": datetime.now().isoformat(),
        
        # Input data
        "input_symbols": input_symbols,
        "model_requested": model,
        
        # Processing results
        "predictions": predictions,
        "latency_ms": round(latency_ms, 2),
        "status": status,
        
        # Provenance metadata
        "model_version": get_model_version(),
        "data_snapshot_id": get_data_snapshot_id(),
        "pipeline_git_sha": get_git_sha(),
        "container_image_digest": get_container_digest(),
        
        # Additional context
        "environment": os.getenv('ENVIRONMENT', 'production'),
        "api_version": "1.0.0"
    }
    
    if error:
        trace["error"] = error
    
    # Log to Kafka
    try:
        producer = get_provenance_producer()
        if producer:
            producer.send(
                'team05.provenance',
                key=request_id,
                value=trace
            )
            logger.debug(f"Provenance logged for request {request_id}")
    except Exception as e:
        logger.warning(f"Failed to log provenance to Kafka: {e}")
    
    # Also log to file as backup
    try:
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f"provenance_{datetime.now().strftime('%Y%m%d')}.jsonl")
        
        with open(log_file, 'a') as f:
            f.write(json.dumps(trace) + '\n')
            
    except Exception as e:
        logger.warning(f"Failed to log provenance to file: {e}")


def get_provenance_trace(request_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve provenance trace for a specific request.
    
    Args:
        request_id: Request identifier to look up
    
    Returns:
        Provenance trace dict or None if not found
    """
    try:
        # Search in today's log file
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        log_file = os.path.join(log_dir, f"provenance_{datetime.now().strftime('%Y%m%d')}.jsonl")
        
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                for line in f:
                    trace = json.loads(line)
                    if trace.get('request_id') == request_id:
                        return trace
        
        return None
        
    except Exception as e:
        logger.error(f"Error retrieving provenance trace: {e}")
        return None


def flush_provenance():
    """Flush provenance logs to Kafka"""
    if _provenance_producer:
        try:
            _provenance_producer.flush(timeout=5)
        except Exception as e:
            logger.warning(f"Error flushing provenance producer: {e}")
