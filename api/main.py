"""
FinSightAI API - FastAPI Application
Provides /recommend endpoint for stock predictions
"""
import os
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from api.predictor import get_prediction_service

# Import monitoring
from api.monitoring import (
    PrometheusMiddleware, 
    metrics_endpoint, 
    record_prediction, 
    record_error,
    update_health_status,
    get_uptime_formatted
)

# Import provenance tracking
from api.provenance import log_provenance

# Import A/B testing
from api.ab_testing import get_ab_variant, get_model_for_variant, log_ab_result, get_ab_metrics, AB_TEST_ENABLED

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FinSightAI API",
    description="API for stock price predictions using ML models",
    version="1.0.0"
)

# Add Prometheus monitoring middleware
app.add_middleware(PrometheusMiddleware)


# Request/Response Schemas
class RecommendRequest(BaseModel):
    """Request schema for /recommend endpoint"""
    user_id: str = Field(..., description="User identifier")
    symbols: List[str] = Field(..., description="List of stock symbols to predict")
    model: Optional[str] = Field(
        default="all",
        description="Model to use: 'lstm', 'randomforest', 'movingaverage', or 'all'"
    )


class PredictionResult(BaseModel):
    """Single prediction result"""
    symbol: str
    predictions: dict
    prediction_timestamp: str
    target_timestamp: str
    current_price: float


class RecommendResponse(BaseModel):
    """Response schema for /recommend endpoint"""
    request_id: str
    timestamp: str
    status: str
    results: dict
    model_used: str


@app.on_event("startup")
async def startup_event():
    """Initialize prediction service on startup"""
    logger.info("🚀 Starting FinSightAI API...")
    try:
        service = get_prediction_service()
        logger.info("✅ Prediction service initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize prediction service: {e}", exc_info=True)
        # Don't raise - allow API to start even if models fail to load
        # Health endpoint will report unhealthy status


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "FinSightAI Stock Prediction API",
        "version": "1.0.0",
        "endpoints": {
            "/recommend": "POST - Get stock predictions",
            "/health": "GET - Health check",
            "/models": "GET - List available models"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    try:
        service = get_prediction_service()
        
        # Check if models are loaded
        models_ready = (
            service.lstm_model is not None and 
            service.rf_model is not None and 
            service.scaler is not None
        )
        
        if not models_ready:
            update_health_status(False)
            return JSONResponse(
                status_code=200,  # Return 200 so Container App doesn't mark as unhealthy during startup
                content={
                    "status": "starting",
                    "reason": "Models still loading",
                    "timestamp": datetime.now().isoformat(),
                    "uptime": get_uptime_formatted()
                }
            )
        
        update_health_status(True)
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "uptime": get_uptime_formatted(),
            "models_loaded": {
                "LSTM": service.lstm_model is not None,
                "RandomForest": service.rf_model is not None,
                "MovingAverage": service.ma_model is not None,
                "Scaler": service.scaler is not None
            },
            "models_ready": models_ready
        }
    except Exception as e:
        logger.error(f"Health check error: {e}", exc_info=True)
        update_health_status(False)
        return JSONResponse(
            status_code=200,  # Don't fail health check on errors
            content={
                "status": "error", 
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "uptime": get_uptime_formatted()
            }
        )


@app.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.
    
    Exports metrics:
    - http_requests_total: Total HTTP requests by method, endpoint, status
    - http_request_duration_seconds: Request latency histogram
    - model_predictions_total: Total predictions by model and status
    - model_errors_total: Total errors by model and type
    - api_uptime_seconds: API uptime in seconds
    - api_health_status: Health status (1=healthy, 0=unhealthy)
    """
    return await metrics_endpoint()


@app.get("/ab-test-metrics")
async def ab_test_metrics(date: Optional[str] = None):
    """
    Get A/B test metrics.
    
    Args:
        date: Date string (YYYYMMDD) or None for today
    
    Returns:
        A/B test metrics including success rates, latencies, and error rates for each variant
    """
    return get_ab_metrics(date)


@app.get("/models")
async def list_models():
    """List available models"""
    return {
        "available_models": [
            {
                "name": "LSTM",
                "type": "neural_network",
                "description": "Long Short-Term Memory neural network"
            },
            {
                "name": "RandomForest",
                "type": "ensemble",
                "description": "Random Forest regressor"
            },
            {
                "name": "MovingAverage",
                "type": "baseline",
                "description": "Simple moving average baseline"
            }
        ],
        "default": "all"
    }


@app.post("/recommend", response_model=RecommendResponse)
async def recommend(request: RecommendRequest):
    """Get stock price predictions for a list of symbols."""
    start_time = time.time()
    
    # A/B Testing: Assign variant and model
    ab_variant = None
    model_to_use = request.model
    if AB_TEST_ENABLED and (model_to_use is None or model_to_use == "all"):
        ab_variant = get_ab_variant(request.user_id)
        model_to_use = get_model_for_variant(ab_variant)
        logger.info(f"A/B Test: user={request.user_id}, variant={ab_variant}, model={model_to_use}")

    try:
        logger.info(f"📊 Recommendation request: user={request.user_id}, symbols={request.symbols}, model={model_to_use}")

        predictor = get_prediction_service()
        
        # Validate symbols
        from kafka_pipeline.config import SYMBOLS
        invalid_symbols = [s for s in request.symbols if s.upper() not in SYMBOLS]
        if invalid_symbols:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid symbols: {invalid_symbols}. Valid symbols: {SYMBOLS}"
            )
        
        # Make predictions
        # Use the model determined by the A/B test
        predictions = predictor.predict(symbols=request.symbols, model_name=model_to_use)

        response = RecommendResponse(
            request_id=request.user_id,
            timestamp=datetime.now().isoformat(),
            status="success",
            results=predictions,
            model_used=model_to_use
        )
        
        # Log A/B test result
        if ab_variant:
            log_ab_result(
                user_id=request.user_id,
                variant=ab_variant,
                model=model_to_use,
                symbols=request.symbols,
                predictions=predictions,
                latency_ms=(time.time() - start_time) * 1000,
                success=True
            )
        
        logger.info(f"✅ Successfully generated predictions for {len([r for r in predictions.values() if 'error' not in r])} symbols")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during recommendation: {e}", exc_info=True)
        
        # Log A/B test result for failure
        if ab_variant:
            log_ab_result(
                user_id=request.user_id,
                variant=ab_variant,
                model=model_to_use,
                symbols=request.symbols,
                predictions={},
                latency_ms=(time.time() - start_time) * 1000,
                success=False,
                error=str(e)
            )
            
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

