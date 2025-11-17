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


class PredictionService:
    """Service for loading models and making predictions"""
    
    def __init__(self):
        """Initialize models and load historical data"""
        self.lstm_model = None
        self.rf_model = None
        self.scaler = None
        self.ma_model = MovingAveragePredictor(window=20)
        self.models_loaded = False
        
        self.feature_cols = [
            'open', 'high', 'low', 'close', 'volume', 'sentiment_mean', 
            'news_count', 'return', 'log_return', 'ema_10', 'ema_50', 
            'rsi', 'macd', 'bb_high', 'bb_low', 'atr'
        ]
        self.sequence_len = 60
        
        # Data buffers per symbol
        self.data_buffer = {symbol: pd.DataFrame() for symbol in SYMBOLS}
        self.buffer_lock = Lock()
        
        # Azure Blob Client
        self.blob_service_client = None
        self.container_client = None
        
        try:
            if AZURE_STORAGE_CONNECTION_STRING:
                self.blob_service_client = BlobServiceClient.from_connection_string(
                    AZURE_STORAGE_CONNECTION_STRING
                )
                self.container_client = self.blob_service_client.get_container_client(
                    AZURE_STORAGE_CONTAINER_NAME
                )
                logger.info("✅ Blob storage client initialized")
        except Exception as e:
            logger.warning(f"⚠️  Could not initialize blob storage client: {e}")
        
        # Load models (catch errors to allow API to start)
        try:
            self.load_models()
            self.models_loaded = True
        except Exception as e:
            logger.error(f"❌ Failed to load models during init: {e}", exc_info=True)
            self.models_loaded = False
        
        # Load historical data in background (don't block startup)
        try:
            self.load_historical_data()
        except Exception as e:
            logger.warning(f"⚠️  Could not load historical data: {e}")
    
    def load_models(self):
        """Load ML models and scaler"""
        logger.info("📦 Loading ML models and scaler...")
        model_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Try current directory first, then parent
        lstm_path = 'multi_stock_model_LSTM.keras' if os.path.exists('multi_stock_model_LSTM.keras') else os.path.join(model_dir, 'multi_stock_model_LSTM.keras')
        rf_path = 'random_forest_model.pkl' if os.path.exists('random_forest_model.pkl') else os.path.join(model_dir, 'random_forest_model.pkl')
        scaler_path = 'scaler.pkl' if os.path.exists('scaler.pkl') else os.path.join(model_dir, 'scaler.pkl')
        
        logger.info(f"  Loading LSTM from: {lstm_path}")
        self.lstm_model = load_model(lstm_path, compile=False)  # Skip compilation for faster loading
        logger.info("  ✓ LSTM loaded")
        
        logger.info(f"  Loading RandomForest from: {rf_path}")
        self.rf_model = joblib.load(rf_path)
        logger.info("  ✓ RandomForest loaded")
        
        logger.info(f"  Loading Scaler from: {scaler_path}")
        self.scaler = joblib.load(scaler_path)
        logger.info("  ✓ Scaler loaded")
        
        logger.info("✅ All models and scaler loaded successfully")
    
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
    
    def predict(self, symbol: str, model: str = "all") -> dict:
        """
        Make prediction for a symbol using specified model(s)
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            model: Model to use ('lstm', 'randomforest', 'movingaverage', or 'all')
        
        Returns:
            Dictionary with predictions
        """
        if symbol not in SYMBOLS:
            raise ValueError(f"Invalid symbol: {symbol}. Valid symbols: {SYMBOLS}")
        
        with self.buffer_lock:
            historical_buffer = self.data_buffer[symbol]
            
            if historical_buffer.empty:
                raise ValueError(f"No historical data available for {symbol}")
            
            # Check if we have enough data
            if len(historical_buffer) < self.sequence_len:
                raise ValueError(
                    f"Insufficient data for {symbol}. Need {self.sequence_len}, "
                    f"have {len(historical_buffer)}"
                )
            
            # Get the sequence for prediction
            sequence_df = historical_buffer.tail(self.sequence_len).copy()
            
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
            
            if model.lower() in ['lstm', 'all']:
                sequence_scaled = self.scaler.transform(
                    sequence_df[self.feature_cols]
                ).reshape((1, self.sequence_len, len(self.feature_cols)))
                pred_lstm = self.lstm_model.predict(sequence_scaled, verbose=0)[0][0]
                predictions['LSTM'] = float(pred_lstm)
            
            if model.lower() in ['randomforest', 'rf', 'all']:
                pred_rf = self.rf_model.predict(
                    sequence_df[self.feature_cols].tail(1)
                )[0]
                predictions['RandomForest'] = float(pred_rf)
            
            if model.lower() in ['movingaverage', 'ma', 'all']:
                pred_ma = self.ma_model.predict(historical_buffer)
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
    
    def predict_multiple(self, symbols: list, model: str = "all") -> dict:
        """
        Make predictions for multiple symbols
        
        Args:
            symbols: List of stock symbols
            model: Model to use
        
        Returns:
            Dictionary mapping symbol -> prediction results
        """
        results = {}
        for symbol in symbols:
            try:
                results[symbol] = self.predict(symbol, model)
            except Exception as e:
                results[symbol] = {'error': str(e)}
        return results


# Global instance
_prediction_service = None

def get_prediction_service() -> PredictionService:
    """Get or create prediction service instance"""
    global _prediction_service
    if _prediction_service is None:
        _prediction_service = PredictionService()
    return _prediction_service

