"""
Prediction Service for FinSightAI API
Handles model loading and prediction logic
"""
import os
import sys
import logging
import pandas as pd
import numpy as np
from datetime import timedelta, date
from threading import Lock
import joblib
from tensorflow.keras.models import load_model
from azure.storage.blob import BlobServiceClient
import io

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kafka_pipeline.config import *
from scripts.feature_engineering import engineer_features
from models.baseline_ma import MovingAveragePredictor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Constants ---
LOCAL_MODEL_DIR = "models"
MODEL_FILES = {
    "lstm": "multi_stock_model_LSTM.keras",
    "random_forest": "random_forest_model.pkl",
    "scaler": "scaler.pkl"
}

# --- Model Loading Functions ---
def load_model_from_local(file_key: str):
    """Loads a model file from the local 'models' directory."""
    model_path = os.path.join(LOCAL_MODEL_DIR, MODEL_FILES.get(file_key))
    if os.path.exists(model_path):
        logger.info(f"Loading {file_key} from local: {model_path}")
        if file_key == 'lstm':
            return load_model(model_path, compile=False) # Skip compilation for faster loading
        return joblib.load(model_path)
    return None

def download_and_load_model_from_azure(model_version: str, file_key: str):
    """Downloads a model file from Azure Blob Storage and loads it into memory."""
    try:
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        if not connection_string:
            logger.warning("AZURE_STORAGE_CONNECTION_STRING not set. Cannot download from Azure.")
            return None

        container_name = "model-registry"
        file_name = MODEL_FILES.get(file_key)
        blob_path = f"{model_version}/{file_name}"

        logger.info(f"Downloading model '{blob_path}' from Azure Blob Storage...")
        
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_path)
        
        if not blob_client.exists():
            logger.error(f"Model blob not found in Azure: {blob_path}")
            return None

        downloader = blob_client.download_blob()
        blob_bytes = downloader.readall()
        
        with open(file_name, "wb") as f:
            f.write(blob_bytes)

        if file_key == 'lstm':
            return load_model(file_name)
        else:
            return joblib.load(file_name)

    except Exception as e:
        logger.error(f"Failed to download/load model '{file_key}' from Azure: {e}")
        import traceback
        traceback.print_exc()
        return None

# --- Predictor Class ---
class Predictor:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            print("Creating new Predictor instance")
            cls._instance = super(Predictor, cls).__new__(cls)
            cls._instance.model_version = os.getenv("MODEL_VERSION", "v1.0") # Default to v1.0
            print(f"Initializing Predictor for model version: {cls._instance.model_version}")
            cls._instance.lstm_model = None
            cls._instance.rf_model = None
            cls._instance.scaler = None
            cls._instance.buffer = {}  # In-memory buffer for historical data
            cls._instance.load_models()
        return cls._instance

    def load_models(self):
        """Loads all models into memory, trying Azure first then local."""
        logger.info(f"--- Loading models for version: {self.model_version} ---")
        
        # Try loading from Azure first
        self.lstm_model = download_and_load_model_from_azure(self.model_version, 'lstm')
        self.rf_model = download_and_load_model_from_azure(self.model_version, 'random_forest')
        self.scaler = download_and_load_model_from_azure(self.model_version, 'scaler')
        
        # Fallback to local if Azure download failed
        if self.lstm_model is None:
            logger.warning("Falling back to local LSTM model...")
            self.lstm_model = load_model_from_local('lstm')
        if self.rf_model is None:
            logger.warning("Falling back to local Random Forest model...")
            self.rf_model = load_model_from_local('random_forest')
        if self.scaler is None:
            logger.warning("Falling back to local scaler...")
            self.scaler = load_model_from_local('scaler')

        if self.lstm_model and self.rf_model and self.scaler:
            logger.info(f"✅ All models for version '{self.model_version}' loaded successfully.")
        else:
            logger.error("❌ Critical error: Failed to load one or more models.")

    def load_historical_data(self):
        """Load historical data from blob storage"""
        if not self.container_client:
            logger.warning("⚠️  Blob storage not configured, skipping historical data load")
            return
        
        try:
            logger.info("📊 Loading historical data from blob storage...")
            buffer_end_date = date.today() - timedelta(days=1)
            
            # Go back up to 90 days to find data
            for i in range(90):
                current_date = buffer_end_date - timedelta(days=i)
                date_str = current_date.strftime('%Y-%m-%d')
                
                # Load trading hours (9-17)
                for hour in range(9, 17):
                    blob_path = f"v1/date={date_str}/hour={hour:02d}/backfill_oct.parquet"
                    try:
                        blob_client = self.container_client.get_blob_client(blob_path)
                        if blob_client.exists():
                            downloader = blob_client.download_blob()
                            blob_bytes = downloader.readall()
                            df = pd.read_parquet(io.BytesIO(blob_bytes))
                            df['timestamp'] = pd.to_datetime(df['timestamp'])
                            
                            for symbol in SYMBOLS:
                                symbol_df = df[df['symbol'] == symbol]
                                if not symbol_df.empty:
                                    self.data_buffer[symbol] = pd.concat(
                                        [symbol_df, self.data_buffer[symbol]], 
                                        ignore_index=True
                                    )
                                    self.data_buffer[symbol].sort_values(by='timestamp', inplace=True)
                    except Exception:
                        continue
            
            # Log loaded data
            for symbol, df in self.data_buffer.items():
                if not df.empty:
                    logger.info(f"✅ Loaded {len(df)} historical records for {symbol}")
                else:
                    logger.warning(f"⚠️  No historical data for {symbol}")
        except Exception as e:
            logger.error(f"Error loading historical data: {e}", exc_info=True)

    def _ensure_buffer(self, symbol: str, required_length: int = 50):
        """Ensures the buffer for a symbol has enough historical data."""
        # For now, this is a placeholder. In a real system, this would
        # fetch data from a database or a fast-access cache like Redis.
        if symbol not in self.buffer or len(self.buffer.get(symbol, [])) < required_length:
            logger.warning(f"Buffer for {symbol} has insufficient data ({len(self.buffer.get(symbol, []))}/{required_length}). Predictions may be inaccurate.")
            # Create dummy data if buffer is empty to prevent crashes
            if symbol not in self.buffer:
                dummy_data = {
                    'open': [150]*required_length, 'high': [151]*required_length,
                    'low': [149]*required_length, 'close': [150.5]*required_length,
                    'volume': [1000000]*required_length, 'sentiment_mean': [0.1]*required_length,
                    'news_count': [5]*required_length, 'return': [0.001]*required_length,
                    'log_return': [0.001]*required_length, 'ema_10': [150]*required_length,
                    'ema_50': [149]*required_length, 'rsi': [55]*required_length,
                    'macd': [0.5]*required_length, 'bb_high': [152]*required_length,
                    'bb_low': [148]*required_length, 'atr': [1.5]*required_length
                }
                self.buffer[symbol] = pd.DataFrame(dummy_data)
            self.buffer[symbol] = self.buffer[symbol].iloc[-required_length:]

    def _update_buffer(self, new_data: dict):
        """Updates the buffer with a new data point."""
        symbol = new_data['symbol']
        new_df = pd.DataFrame([new_data])
        if symbol not in self.buffer:
            self.buffer[symbol] = new_df
        else:
            self.buffer[symbol] = pd.concat([self.buffer[symbol], new_df], ignore_index=True)
        
        # Keep buffer size fixed
        self.buffer[symbol] = self.buffer[symbol].iloc[-50:]

    def predict(self, new_data: dict) -> float:
        """
        Make prediction for a symbol using specified model(s)
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            model: Model to use ('lstm', 'randomforest', 'movingaverage', or 'all')
        
        Returns:
            Dictionary with predictions
        """
        symbol = new_data['symbol']
        
        self._update_buffer(new_data)
        
        if not all([self.lstm_model, self.rf_model, self.scaler]):
            logger.error("Models not loaded, cannot predict.")
            return 0.0

        # Ensure buffer has enough data
        self._ensure_buffer(symbol)

        # Prepare features from buffer
        sequence_df = self.buffer[symbol].tail(60).copy() # Use 60 as sequence length
        
        # Ensure features are calculated
        if not all(col in sequence_df.columns for col in self.feature_cols):
            # Re-engineer features if missing
            sequence_df = engineer_features(sequence_df)
        
        # Fill any NaNs
        sequence_df = sequence_df.ffill().fillna(0)
        
        # Check for missing columns
        missing_cols = [col for col in self.feature_cols if col not in sequence_df.columns]
        if missing_cols:
            raise ValueError(f"Missing feature columns: {missing_cols}")
        
        # Make predictions
        predictions = {}
        
        # LSTM prediction
        if self.lstm_model:
            sequence_scaled = self.scaler.transform(
                sequence_df[self.feature_cols]
            ).reshape((1, 60, len(self.feature_cols)))
            pred_lstm = self.lstm_model.predict(sequence_scaled, verbose=0)[0][0]
            predictions['LSTM'] = float(pred_lstm)
        
        # Random Forest prediction
        if self.rf_model:
            pred_rf = self.rf_model.predict(
                sequence_df[self.feature_cols].tail(1)
            )[0]
            predictions['RandomForest'] = float(pred_rf)
        
        # Moving Average prediction
        if self.ma_model: # Assuming ma_model is an instance of MovingAveragePredictor
            pred_ma = self.ma_model.predict(self.buffer[symbol])
            predictions['MovingAverage'] = float(pred_ma)
        
        latest_timestamp = sequence_df['timestamp'].iloc[-1]
        target_timestamp = latest_timestamp + pd.Timedelta(hours=1)
        
        return {
            'symbol': symbol,
            'predictions': predictions,
            'prediction_timestamp': latest_timestamp.isoformat(),
            'target_timestamp': target_timestamp.isoformat(),
            'current_price': float(sequence_df['close'].iloc[-1])
        }


# Global instance
_prediction_service = None

def get_prediction_service() -> PredictionService:
    """Get or create prediction service instance"""
    global _prediction_service
    if _prediction_service is None:
        _prediction_service = PredictionService()
    return _prediction_service

