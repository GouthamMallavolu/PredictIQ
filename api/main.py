from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import logging
import time
from datetime import datetime
import json
import numpy as np

# Import predictor logic
from .predictor import ModelPredictor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="StockRecoAI",
    description="Stock Price Prediction & Recommendation API",
    version="1.0.0"
)

# Initialize model predictor (loads all 3 models)
predictor = ModelPredictor()

# Pydantic models for request/response
class RecommendRequest(BaseModel):
    """Recommendation request schema"""
    user_id: str
    symbols: List[str] = Field(default=["AAPL", "MSFT", "NVDA", "META", "TSLA"], min_length=1)
    top_k: int = Field(default=5, ge=1, le=10)
    model: str = Field(default="lstm", pattern="^(lstm|rf|ma|ensemble)$")

class StockPrediction(BaseModel):
    """Single stock price prediction"""
    symbol: str
    current_price: float
    predicted_price: float
    predicted_change: float  # Dollar change
    predicted_change_pct: float  # Percentage change
    model_confidence: float  # Model's prediction confidence (0-1)

class PredictionResponse(BaseModel):
    """Stock price prediction response schema"""
    request_id: str
    user_id: str
    predictions: List[StockPrediction]
    model_used: str
    latency_ms: float
    timestamp: str
    prediction_horizon: str  # e.g., "1 hour", "next close"

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "StockRecoAI",
        "status": "healthy",
        "version": "1.0.0",
        "models_loaded": predictor.models_loaded
    }

@app.get("/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "models": {
            "lstm": predictor.lstm_loaded,
            "moving_average": predictor.ma_loaded
        },
        "timestamp": datetime.now().isoformat()
    }

@app.post("/recommend", response_model=PredictionResponse)
async def recommend(request: RecommendRequest):
    """
    Generate stock price predictions
    
    This endpoint:
    1. Fetches recent data for requested symbols
    2. Makes next-hour price predictions using selected model
    3. Returns predicted prices with expected changes
    """
    start_time = time.time()
    request_id = f"{request.user_id}_{int(time.time())}"
    
    logger.info(f"📥 Request {request_id}: {request.symbols} (model={request.model})")
    
    try:
        # Make predictions
        predictions = predictor.predict_batch(
            symbols=request.symbols,
            model_name=request.model
        )
        
        # Create stock predictions
        stock_predictions = []
        for symbol, pred in list(predictions.items())[:request.top_k]:
            current = pred.get('current_price', 0.0)
            predicted = pred['predicted_price']
            change = predicted - current
            change_pct = (change / current * 100) if current > 0 else 0.0
            
            stock_predictions.append(StockPrediction(
                symbol=symbol,
                current_price=current,
                predicted_price=predicted,
                predicted_change=round(change, 2),
                predicted_change_pct=round(change_pct, 2),
                model_confidence=pred.get('confidence', 0.75)
            ))
        
        latency_ms = (time.time() - start_time) * 1000
        
        response = PredictionResponse(
            request_id=request_id,
            user_id=request.user_id,
            predictions=stock_predictions,
            model_used=request.model,
            latency_ms=latency_ms,
            timestamp=datetime.now().isoformat(),
            prediction_horizon="next hour (1h ahead)"
        )
        
        logger.info(f"✅ Request {request_id} completed in {latency_ms:.2f}ms")
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Error processing request {request_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/models")
async def list_models():
    """List available models and their info"""
    return {
        "models": [
            {
                "name": "lstm",
                "description": "LSTM Neural Network",
                "loaded": predictor.lstm_loaded,
                "accuracy": "MAE: 2.69"
            },
            {
                "name": "ma",
                "description": "Moving Average Baseline",
                "loaded": predictor.ma_loaded,
                "accuracy": "MAE: 8.45"
            },
            {
                "name": "ensemble",
                "description": "Weighted ensemble of LSTM and Moving Average",
                "loaded": all([predictor.lstm_loaded, predictor.ma_loaded]),
                "accuracy": "MAE: 2.50 (estimated)"
            }
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

