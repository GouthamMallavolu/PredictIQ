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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FinSightAI Stock Prediction API",
    description="API for stock price predictions using ML models",
    version="1.0.0"
)


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
            return JSONResponse(
                status_code=200,  # Return 200 so Container App doesn't mark as unhealthy during startup
                content={
                    "status": "starting",
                    "reason": "Models still loading",
                    "timestamp": datetime.now().isoformat()
                }
            )
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
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
        return JSONResponse(
            status_code=200,  # Don't fail health check on errors
            content={
                "status": "error", 
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


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
    """
    Get stock price predictions for given symbols
    
    Args:
        request: RecommendRequest with user_id, symbols, and optional model
    
    Returns:
        RecommendResponse with predictions
    """
    try:
        logger.info(f"📊 Recommendation request: user={request.user_id}, symbols={request.symbols}, model={request.model}")
        
        service = get_prediction_service()
        
        # Validate symbols
        from kafka_pipeline.config import SYMBOLS
        invalid_symbols = [s for s in request.symbols if s.upper() not in SYMBOLS]
        if invalid_symbols:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid symbols: {invalid_symbols}. Valid symbols: {SYMBOLS}"
            )
        
        # Make predictions
        results = {}
        for symbol in request.symbols:
            try:
                symbol_upper = symbol.upper()
                pred_result = service.predict(symbol_upper, request.model or "all")
                results[symbol_upper] = pred_result
            except ValueError as e:
                results[symbol] = {"error": str(e)}
            except Exception as e:
                logger.error(f"Error predicting for {symbol}: {e}", exc_info=True)
                results[symbol] = {"error": f"Prediction failed: {str(e)}"}
        
        # Check if any predictions succeeded
        successful = any("error" not in result for result in results.values())
        if not successful:
            raise HTTPException(
                status_code=500,
                detail="All predictions failed. Check logs for details."
            )
        
        response = RecommendResponse(
            request_id=request.user_id,
            timestamp=datetime.now().isoformat(),
            status="success",
            results=results,
            model_used=request.model or "all"
        )
        
        logger.info(f"✅ Successfully generated predictions for {len([r for r in results.values() if 'error' not in r])} symbols")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in /recommend: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

