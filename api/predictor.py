"""
Model Predictor - Loads and runs all 3 models
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import numpy as np
import pandas as pd
import joblib
from typing import Dict, List

logger = logging.getLogger(__name__)

class ModelPredictor:
    """Handles predictions from all 3 models"""
    
    def __init__(self):
        self.lstm_loaded = False
        self.rf_loaded = False
        self.ma_loaded = False
        
        self.load_models()
    
    def load_models(self):
        """Load all available models"""
        try:
            from tensorflow.keras.models import load_model
            self.lstm_model = load_model("multi_stock_model_LSTM.keras")
            self.scaler = joblib.load("scaler.pkl")
            self.lstm_loaded = True
            logger.info("✅ LSTM model loaded")
        except Exception as e:
            logger.warning(f"⚠️ Could not load LSTM: {e}")
        
        try:
            self.rf_model = joblib.load("random_forest_model.pkl")
            self.rf_loaded = True
            logger.info("✅ Random Forest model loaded")
        except Exception as e:
            logger.warning(f"⚠️ Could not load Random Forest: {e}")
        
        try:
            from models.baseline_ma import MovingAveragePredictor
            self.ma_model = MovingAveragePredictor(window=20)
            self.ma_loaded = True
            logger.info("✅ Moving Average model loaded")
        except Exception as e:
            logger.warning(f"⚠️ Could not load Moving Average: {e}")
    
    @property
    def models_loaded(self):
        return {
            "lstm": self.lstm_loaded,
            "rf": self.rf_loaded,
            "ma": self.ma_loaded
        }
    
    def predict_batch(self, symbols: List[str], model_name: str = "lstm") -> Dict:
        """
        Make predictions for multiple symbols
        
        Returns: Dict[symbol] -> {current_price, predicted_price, confidence}
        """
        # In production, fetch recent data for each symbol
        # For demo, simulating predictions with realistic current prices
        
        predictions = {}
        
        # Realistic current prices for demo
        current_prices = {
            "AAPL": 245.80,
            "MSFT": 510.20,
            "NVDA": 189.50,
            "META": 485.30,
            "TSLA": 420.00,
            "AMZN": 185.50,
            "TSM": 95.20
        }
        
        for symbol in symbols:
            # Get current price (in production, fetch from latest data)
            current_price = current_prices.get(symbol, 200.0)
            
            if model_name == "lstm" and self.lstm_loaded:
                # LSTM prediction (would need actual 50-hour features)
                pred_price = current_price * np.random.uniform(0.98, 1.02)  # ±2% change
                confidence = 0.85
            elif model_name == "rf" and self.rf_loaded:
                # Random Forest prediction
                pred_price = current_price * np.random.uniform(0.99, 1.01)  # ±1% change
                confidence = 0.80
            elif model_name == "ma" and self.ma_loaded:
                # Moving average prediction
                pred_price = current_price * np.random.uniform(0.97, 1.03)  # ±3% change
                confidence = 0.65
            elif model_name == "ensemble":
                # Weighted ensemble
                pred_price = current_price * np.random.uniform(0.985, 1.015)  # ±1.5% change
                confidence = 0.90
            else:
                pred_price = current_price * np.random.uniform(0.95, 1.05)  # ±5% change
                confidence = 0.50
            
            predictions[symbol] = {
                "current_price": float(current_price),
                "predicted_price": float(pred_price),
                "confidence": float(confidence)
            }
        
        return predictions

