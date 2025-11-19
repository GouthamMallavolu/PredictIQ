"""
API Monitoring with Prometheus Metrics

Exports metrics at /metrics endpoint:
- http_requests_total: Total HTTP requests
- http_request_duration_seconds: Request latency
- model_predictions_total: Total predictions by model
- model_errors_total: Total errors by model
- api_uptime_seconds: API uptime
"""

import time
from datetime import datetime
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# Prometheus Metrics
# ============================================================================

# HTTP Request metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0)
)

# Model prediction metrics
model_predictions_total = Counter(
    'model_predictions_total',
    'Total predictions by model',
    ['model', 'status']
)

model_errors_total = Counter(
    'model_errors_total',
    'Total errors by model',
    ['model', 'error_type']
)

# API uptime
api_start_time = time.time()
api_uptime_seconds = Gauge(
    'api_uptime_seconds',
    'API uptime in seconds'
)

# Health status
api_health_status = Gauge(
    'api_health_status',
    'API health status (1=healthy, 0=unhealthy)'
)

# ============================================================================
# Metrics Middleware
# ============================================================================

class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware to collect HTTP request metrics"""
    
    async def dispatch(self, request: Request, call_next):
        # Skip metrics endpoint to avoid recursion
        if request.url.path == "/metrics":
            return await call_next(request)
        
        # Record request start time
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Record metrics
        duration = time.time() - start_time
        
        http_requests_total.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        
        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)
        
        # Update uptime
        api_uptime_seconds.set(time.time() - api_start_time)
        
        return response


# ============================================================================
# Metrics Endpoint
# ============================================================================

async def metrics_endpoint():
    """
    Prometheus metrics endpoint.
    
    Returns:
        Prometheus-formatted metrics
    """
    # Update uptime before serving metrics
    api_uptime_seconds.set(time.time() - api_start_time)
    
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


# ============================================================================
# Helper Functions
# ============================================================================

def record_prediction(model: str, success: bool):
    """Record a prediction attempt"""
    status = "success" if success else "failure"
    model_predictions_total.labels(model=model, status=status).inc()


def record_error(model: str, error_type: str):
    """Record an error"""
    model_errors_total.labels(model=model, error_type=error_type).inc()


def update_health_status(is_healthy: bool):
    """Update health status metric"""
    api_health_status.set(1 if is_healthy else 0)


def get_uptime() -> float:
    """Get current API uptime in seconds"""
    return time.time() - api_start_time


def get_uptime_formatted() -> str:
    """Get formatted uptime string"""
    uptime = get_uptime()
    days = int(uptime // 86400)
    hours = int((uptime % 86400) // 3600)
    minutes = int((uptime % 3600) // 60)
    seconds = int(uptime % 60)
    
    if days > 0:
        return f"{days}d {hours}h {minutes}m {seconds}s"
    elif hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"
