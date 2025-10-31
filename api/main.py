from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import logging
import time
from datetime import datetime
import json
import numpy as np
import os

# Import predictor logic
from predictor import ModelPredictor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="StockRecoAI",
    description="Stock Price Prediction & Recommendation API",
    version="1.0.0"
)

# Mount static files for React frontend
if os.path.exists("frontend/build"):
    app.mount("/static", StaticFiles(directory="frontend/build/static"), name="static")

# Initialize model predictor (loads all 3 models)
predictor = ModelPredictor()

# Pydantic models for request/response
class RecommendRequest(BaseModel):
    """Recommendation request schema"""
    user_id: str
    symbols: List[str] = Field(default=["AAPL", "MSFT", "NVDA", "META", "TSLA"], min_length=1)
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
    """Serve React frontend or health check"""
    if os.path.exists("frontend/build/index.html"):
        return FileResponse("frontend/build/index.html")
    else:
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
        
        # Create stock predictions (return for all requested symbols)
        stock_predictions = []
        for symbol, pred in predictions.items():
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
    """List available models and their detailed metrics"""
    import joblib
    import os
    
    models = []
    
    # LSTM Model
    if predictor.lstm_loaded:
        try:
            lstm_metrics = joblib.load("lstm_training_metrics.pkl")
            model_size = os.path.getsize("multi_stock_model_LSTM.keras") / (1024 * 1024)
            models.append({
                "name": "lstm",
                "description": "LSTM Neural Network",
                "loaded": True,
                "train_mae": round(lstm_metrics['train_mae'], 2),
                "test_mae": round(lstm_metrics['test_mae'], 2),
                "training_time_min": round(lstm_metrics['training_time_min'], 1),
                "model_size_mb": round(model_size, 1)
            })
        except:
            models.append({
                "name": "lstm",
                "description": "LSTM Neural Network",
                "loaded": True,
                "train_mae": "N/A",
                "test_mae": "N/A",
                "training_time_min": "N/A",
                "model_size_mb": "N/A"
            })
    
    # Random Forest Model
    if predictor.rf_loaded:
        try:
            rf_metrics = joblib.load("rf_training_metrics.pkl")
            model_size = os.path.getsize("random_forest_model.pkl") / (1024 * 1024)
            models.append({
                "name": "rf", 
                "description": "Random Forest Regressor",
                "loaded": True,
                "train_mae": round(rf_metrics['train_mae'], 2),
                "test_mae": round(rf_metrics['test_mae'], 2),
                "training_time_min": round(rf_metrics['training_time_min'], 1),
                "model_size_mb": round(model_size, 1)
            })
        except:
            models.append({
                "name": "rf", 
                "description": "Random Forest Regressor",
                "loaded": True,
                "train_mae": "N/A",
                "test_mae": "N/A",
                "training_time_min": "N/A",
                "model_size_mb": "N/A"
            })
    
    # Moving Average Model
    if predictor.ma_loaded:
        try:
            ma_metrics = joblib.load("ma_training_metrics.pkl")
            models.append({
                "name": "ma",
                "description": "Moving Average Baseline", 
                "loaded": True,
                "train_mae": round(ma_metrics['sample_mae'], 2),
                "test_mae": round(ma_metrics['sample_mae'], 2),
                "training_time_min": round(ma_metrics['training_time_min'], 1),
                "model_size_mb": 0.001
            })
        except:
            models.append({
                "name": "ma",
                "description": "Moving Average Baseline", 
                "loaded": True,
                "train_mae": "N/A",
                "test_mae": "N/A",
                "training_time_min": "N/A",
                "model_size_mb": 0.001
            })
    
    # Ensemble (only if multiple models are loaded)
    if sum([predictor.lstm_loaded, predictor.rf_loaded, predictor.ma_loaded]) >= 2:
        models.append({
            "name": "ensemble",
            "description": "Weighted ensemble of all models",
            "loaded": True,
            "train_mae": "Combined",
            "test_mae": "Combined",
            "training_time_min": "Sum of all",
            "model_size_mb": "Sum of all"
        })
    
    # If no models loaded, show demo mode
    if not models:
        models.append({
            "name": "demo",
            "description": "Demo Model (Mock Predictions)",
            "loaded": True,
            "train_mae": "Demo",
            "test_mae": "Demo",
            "training_time_min": "Demo",
            "model_size_mb": "Demo"
        })
    
    return {"models": models}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

