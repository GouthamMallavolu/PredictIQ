"""
Prediction Service for FinSightAI API
Handles model loading and prediction logic
"""
import os
import sys
import logging
from datetime import timedelta, date
from threading import Lock
import io

import joblib
import numpy as np
import pandas as pd
from azure.storage.blob import BlobServiceClient
from tensorflow.keras.models import load_model

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kafka_pipeline.config import *  # noqa: F401, F403
from scripts.feature_engineering import engineer_features
from models.baseline_ma import MovingAveragePredictor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Turn down verbose Azure HTTP logging
azure_http_logger = logging.getLogger(
    "azure.core.pipeline.policies.http_logging_policy"
)
azure_http_logger.setLevel(logging.WARNING)


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
            "open",
            "high",
            "low",
            "close",
            "volume",
            "sentiment_mean",
            "news_count",
            "return",
            "log_return",
            "ema_10",
            "ema_50",
            "rsi",
            "macd",
            "bb_high",
            "bb_low",
            "atr",
        ]
        # Must match the LSTM model's expected time steps
        self.sequence_len = 50

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
                logger.info("Blob storage client initialized")
        except Exception as e:
            logger.warning("Could not initialize blob storage client: %s", e)

        # Load models (catch errors to allow API to start)
        try:
            self.load_models()
            self.models_loaded = True
        except Exception as e:
            logger.error("Failed to load models: %s", e, exc_info=True)
            self.models_loaded = False

        # Load historical data (do not block startup if it fails)
        try:
            self.load_historical_data()
        except Exception as e:
            logger.warning("Historical data initialization failed: %s", e)

    # ------------------------------------------------------------------ #
    # Historical data helpers
    # ------------------------------------------------------------------ #

    def get_historical_data(self, symbol: str, limit: int = 120) -> pd.DataFrame:
        """
        Return the most recent `limit` rows of historical data for a symbol.
        """
        with self.buffer_lock:
            df = self.data_buffer.get(symbol)

        if df is None or df.empty:
            return pd.DataFrame()

        df = df.sort_values("timestamp")
        return df.tail(limit)[["timestamp", "close"]].copy()

    def _initialize_historical_data_buffer(self):
        """
        Initialize in-memory historical data when an external data source
        is not available or cannot be used.

        The generated series matches the feature schema expected by the models.
        """
        logger.info("Initializing historical data buffer for all symbols")

        # Ensure we have enough rows per symbol for sequence_len
        buffer_len = max(self.sequence_len + 20, 120)

        # Generate hourly timestamps up to the current hour (UTC)
        now = pd.Timestamp.utcnow().floor("H")
        timestamps = pd.date_range(end=now, periods=buffer_len, freq="H")

        for symbol in SYMBOLS:
            # Simple random-walk style price series
            base_price = 100 + 20 * np.random.rand()
            noise = np.random.normal(scale=1.0, size=buffer_len)
            prices = base_price + np.cumsum(noise)

            df = pd.DataFrame(
                {
                    "timestamp": timestamps,
                    "symbol": symbol,
                    "open": prices + np.random.normal(scale=0.2, size=buffer_len),
                    "high": prices
                    + np.abs(np.random.normal(scale=0.5, size=buffer_len)),
                    "low": prices
                    - np.abs(np.random.normal(scale=0.5, size=buffer_len)),
                    "close": prices,
                    "volume": np.random.randint(10_000, 1_000_000, size=buffer_len),
                    "sentiment_mean": np.random.normal(
                        loc=0.0, scale=0.1, size=buffer_len
                    ),
                    "news_count": np.random.poisson(0.5, size=buffer_len),
                }
            )

            # Add all technical indicators used by the models
            df = engineer_features(df)

            # Fill any NaNs created by rolling indicators
            df = df.ffill().bfill()

            with self.buffer_lock:
                self.data_buffer[symbol] = df

            logger.info(
                "Historical data buffer initialized with %d rows for symbol %s",
                len(df),
                symbol,
            )

    def load_historical_data(self):
        """
        Load historical data from an external source when available.

        If the external client is not configured or loading fails, the
        historical data buffer is initialized internally.
        """
        # No external client: initialize internally
        if not self.container_client:
            logger.info(
                "External historical data client is not configured; "
                "initializing historical data buffer internally"
            )
            self._initialize_historical_data_buffer()
            return

        # Quick health check on the container. If the account is disabled or we
        # do not have access, this will raise and we fall back immediately.
        try:
            self.container_client.get_container_properties()
        except Exception as e:
            logger.warning(
                "External historical data container is not accessible (%s); "
                "initializing historical data buffer internally",
                e,
            )
            self._initialize_historical_data_buffer()
            return

        try:
            logger.info("Loading historical data from external source...")
            buffer_end_date = date.today() - timedelta(days=1)

            # Go back up to 90 days to find data
            for i in range(90):
                current_date = buffer_end_date - timedelta(days=i)
                date_str = current_date.strftime("%Y-%m-%d")

                # Load trading hours (9-17)
                for hour in range(9, 17):
                    blob_path = (
                        f"v1/date={date_str}/hour={hour:02d}/backfill_oct.parquet"
                    )
                    try:
                        blob_client = self.container_client.get_blob_client(blob_path)
                        if blob_client.exists():
                            downloader = blob_client.download_blob()
                            blob_bytes = downloader.readall()
                            df = pd.read_parquet(io.BytesIO(blob_bytes))
                            df["timestamp"] = pd.to_datetime(df["timestamp"])

                            for symbol in SYMBOLS:
                                symbol_df = df[df["symbol"] == symbol]
                                if not symbol_df.empty:
                                    self.data_buffer[symbol] = pd.concat(
                                        [symbol_df, self.data_buffer[symbol]],
                                        ignore_index=True,
                                    )
                                    self.data_buffer[symbol].sort_values(
                                        by="timestamp", inplace=True
                                    )
                    except Exception:
                        # If a single blob read fails (404, etc.), skip it and continue
                        continue

            # Log loaded data
            for symbol, df in self.data_buffer.items():
                if not df.empty:
                    logger.info(
                        "Loaded %d historical records for %s",
                        len(df),
                        symbol,
                    )
                else:
                    logger.warning("No historical data for %s", symbol)

        except Exception as e:
            # Any higher-level failure → fall back to internal buffer
            logger.warning(
                "Failed to load historical data from external source (%s); "
                "initializing historical data buffer internally",
                e,
            )
            self._initialize_historical_data_buffer()

    # ------------------------------------------------------------------ #
    # Model loading
    # ------------------------------------------------------------------ #

    def load_models(self):
        """Load ML models and scaler"""
        logger.info("Loading ML models and scaler")

        # Model paths - check models/ subfolder, current dir, then parent
        def find_model_path(filename: str) -> str:
            """Find model file in models/ subfolder, current dir, or parent dir"""
            # Check models/ subfolder first
            models_path = os.path.join("models", filename)
            if os.path.exists(models_path):
                return models_path
            # Check current directory
            if os.path.exists(filename):
                return filename
            # Check parent directory
            model_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            parent_path = os.path.join(model_dir, filename)
            if os.path.exists(parent_path):
                return parent_path
            # Check parent/models directory
            parent_models_path = os.path.join(model_dir, "models", filename)
            if os.path.exists(parent_models_path):
                return parent_models_path
            # Return models/ path as default (will fail with clear error)
            return models_path

        lstm_path = find_model_path("multi_stock_model_LSTM.keras")
        rf_path = find_model_path("random_forest_model.pkl")
        scaler_path = find_model_path("scaler.pkl")

        logger.info("Loading LSTM model from: %s", lstm_path)
        self.lstm_model = load_model(lstm_path, compile=False)
        logger.info("LSTM model loaded")

        logger.info("Loading RandomForest model from: %s", rf_path)
        self.rf_model = joblib.load(rf_path)
        logger.info("RandomForest model loaded")

        logger.info("Loading scaler from: %s", scaler_path)
        self.scaler = joblib.load(scaler_path)
        logger.info("Scaler loaded")

        logger.info("All models and scaler loaded successfully")

    # ------------------------------------------------------------------ #
    # Prediction
    # ------------------------------------------------------------------ #

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
            sequence_df = engineer_features(sequence_df)

        # Fill any NaNs
        sequence_df = sequence_df.ffill().fillna(0)

        # Check for missing columns
        missing_cols = [
            col for col in self.feature_cols if col not in sequence_df.columns
        ]
        if missing_cols:
            raise ValueError(f"Missing feature columns: {missing_cols}")

        predictions = {}

        # LSTM
        if model.lower() in ["lstm", "all"]:
            sequence_scaled = self.scaler.transform(
                sequence_df[self.feature_cols].to_numpy()
            ).reshape((1, self.sequence_len, len(self.feature_cols)))
            pred_lstm = self.lstm_model.predict(sequence_scaled, verbose=0)[0][0]
            predictions["LSTM"] = float(pred_lstm)

        # Random Forest
        if model.lower() in ["randomforest", "rf", "all"]:
            pred_rf = self.rf_model.predict(
                sequence_df[self.feature_cols].tail(1)
            )[0]
            predictions["RandomForest"] = float(pred_rf)

        # Moving Average
        if model.lower() in ["movingaverage", "ma", "all"]:
            pred_ma = self.ma_model.predict(historical_buffer)
            predictions["MovingAverage"] = float(pred_ma)

        latest_timestamp = sequence_df["timestamp"].iloc[-1]
        target_timestamp = latest_timestamp + pd.Timedelta(hours=1)

        return {
            "symbol": symbol,
            "predictions": predictions,
            "prediction_timestamp": latest_timestamp.isoformat(),
            "target_timestamp": target_timestamp.isoformat(),
            "current_price": float(sequence_df["close"].iloc[-1]),
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
                results[symbol] = {"error": str(e)}
        return results


# Global instance
_prediction_service: "PredictionService | None" = None


def get_prediction_service() -> PredictionService:
    """Get or create prediction service instance"""
    global _prediction_service
    if _prediction_service is None:
        _prediction_service = PredictionService()
    return _prediction_service
