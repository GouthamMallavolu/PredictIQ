"""
ModelPredictor - Loads trained models and makes predictions
Supports LSTM, Random Forest, and Moving Average models
"""
import pandas as pd
import numpy as np
import joblib
import os
import sys
from datetime import datetime

# Add parent directory to path for model imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from tensorflow.keras.models import load_model
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    print("WARNING: TensorFlow not available - LSTM predictions will be disabled")

try:
    from models.baseline_ma import MovingAveragePredictor
    MA_MODEL_AVAILABLE = True
except ImportError:
    MA_MODEL_AVAILABLE = False
    print("WARNING: Moving Average model not available")

class ModelPredictor:
    def __init__(self):
        """Initialize predictor and load all available models"""
        self.lstm_model = None
        self.rf_model = None
        self.ma_model = None
        self.scaler = None
        self.lstm_loaded = False
        self.rf_loaded = False
        self.ma_loaded = False
        self.models_loaded = False
        
        self.load_models()
    
    def load_models(self):
        """Load all trained models from files"""
        # Load LSTM model
        if TENSORFLOW_AVAILABLE:
            try:
                if os.path.exists("multi_stock_model_LSTM.keras"):
                    self.lstm_model = load_model("multi_stock_model_LSTM.keras")
                    self.scaler = joblib.load("scaler.pkl")
                    self.lstm_loaded = True
                    print("SUCCESS: LSTM model loaded")
                else:
                    print("WARNING: LSTM model file not found: multi_stock_model_LSTM.keras")
            except Exception as e:
                print(f"ERROR: LSTM model failed to load: {e}")
        else:
            print("WARNING: TensorFlow not available - LSTM model disabled")
        
        # Load Random Forest model
        try:
            if os.path.exists("random_forest_model.pkl"):
                self.rf_model = joblib.load("random_forest_model.pkl")
                self.rf_loaded = True
                print("SUCCESS: Random Forest model loaded")
            else:
                print("WARNING: Random Forest model file not found: random_forest_model.pkl")
        except Exception as e:
            print(f"ERROR: Random Forest model failed to load: {e}")
        
        # Load Moving Average model
        if MA_MODEL_AVAILABLE:
            try:
                self.ma_model = MovingAveragePredictor(window=20)
                self.ma_loaded = True
                print("SUCCESS: Moving Average model loaded")
            except Exception as e:
                print(f"ERROR: Moving Average model failed to load: {e}")
        else:
            print("WARNING: Moving Average model not available")
        
        self.models_loaded = self.lstm_loaded or self.rf_loaded or self.ma_loaded
        
        if not self.models_loaded:
            print("WARNING: No models loaded - predictions will use demo mode")
    
    def predict_lstm(self, data):
        """Predict using LSTM model"""
        if not self.lstm_loaded:
            raise Exception("LSTM model not loaded")
        
        if data.empty:
            raise Exception("No data available for prediction")
        
        # Prepare features (same as training)
        feature_cols = [
            'open', 'high', 'low', 'close', 'volume', 
            'sentiment_mean', 'news_count', 'return', 'log_return',
            'ema_10', 'ema_50', 'rsi', 'macd', 'bb_high', 'bb_low', 'atr'
        ]
        
        # Check if all required features exist
        missing_features = [col for col in feature_cols if col not in data.columns]
        if missing_features:
            raise Exception(f"Missing features for LSTM: {missing_features}")
        
        # Scale features
        X = data[feature_cols].values
        X_scaled = self.scaler.transform(X)
        
        # Reshape for LSTM (sequence_length, features)
        X_reshaped = X_scaled.reshape(-1, 1, X_scaled.shape[1])
        
        # Make prediction
        prediction = self.lstm_model.predict(X_reshaped)
        return prediction[0][0]
    
    def predict_random_forest(self, data):
        """Predict using Random Forest model"""
        if not self.rf_loaded:
            raise Exception("Random Forest model not loaded")
        
        if data.empty:
            raise Exception("No data available for prediction")
        
        # Prepare features (same as training)
        feature_cols = [
            'open', 'high', 'low', 'close', 'volume', 
            'sentiment_mean', 'news_count', 'return', 'log_return',
            'ema_10', 'ema_50', 'rsi', 'macd', 'bb_high', 'bb_low', 'atr'
        ]
        
        # Check if all required features exist
        missing_features = [col for col in feature_cols if col not in data.columns]
        if missing_features:
            raise Exception(f"Missing features for Random Forest: {missing_features}")
        
        X = data[feature_cols].values
        prediction = self.rf_model.predict(X)
        return prediction[0]
    
    def predict_moving_average(self, data):
        """Predict using Moving Average model"""
        if not self.ma_loaded:
            raise Exception("Moving Average model not loaded")
        
        if data.empty:
            raise Exception("No data available for prediction")
        
        return self.ma_model.predict(data)
    
    def predict_batch(self, symbols, model_name="lstm"):
        """Generate predictions for multiple symbols"""
        predictions = {}
        
        for symbol in symbols:
            try:
                # Get recent data for symbol (this would come from consumer buffer)
                recent_data = self.get_recent_data(symbol)
                
                if model_name == "lstm" and self.lstm_loaded:
                    pred_price = self.predict_lstm(recent_data)
                elif model_name == "rf" and self.rf_loaded:
                    pred_price = self.predict_random_forest(recent_data)
                elif model_name == "ma" and self.ma_loaded:
                    pred_price = self.predict_moving_average(recent_data)
                else:
                    raise Exception(f"Model {model_name} not available")
                
                predictions[symbol] = {
                    'predicted_price': pred_price,
                    'current_price': recent_data['close'].iloc[-1] if not recent_data.empty else 100.0,
                    'confidence': self.calculate_confidence(recent_data, pred_price)
                }
                
            except Exception as e:
                print(f"ERROR: Prediction failed for {symbol}: {e}")
                # Fallback to demo prediction
                predictions[symbol] = {
                    'predicted_price': 100.0 * (1 + np.random.normal(0, 0.02)),
                    'current_price': 100.0,
                    'confidence': 0.5
                }
        
        return predictions
    
    def get_recent_data(self, symbol):
        """Get recent data for symbol (placeholder - would be implemented by consumer)"""
        # This is a placeholder - in real implementation, this would be called
        # by the consumer with actual data from the buffer
        return pd.DataFrame()
    
    def calculate_confidence(self, data, prediction):
        """Calculate prediction confidence based on data quality"""
        if data.empty:
            return 0.5
        
        # Simple confidence calculation based on data completeness
        required_features = ['open', 'high', 'low', 'close', 'volume']
        available_features = sum(1 for col in required_features if col in data.columns)
        completeness = available_features / len(required_features)
        
        # Base confidence on completeness and data recency
        base_confidence = completeness * 0.8
        
        # Add some randomness for demo
        confidence = min(0.95, max(0.5, base_confidence + np.random.normal(0, 0.1)))
        
        return confidence

if __name__ == "__main__":
    # Test the predictor
    predictor = ModelPredictor()
    print(f"Models loaded: {predictor.models_loaded}")
    print(f"LSTM: {predictor.lstm_loaded}")
    print(f"Random Forest: {predictor.rf_loaded}")
    print(f"Moving Average: {predictor.ma_loaded}")
