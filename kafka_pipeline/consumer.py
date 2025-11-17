import os
import sys
import json
import logging
import argparse
import pandas as pd
from kafka import KafkaConsumer, KafkaProducer
from threading import Lock
import joblib
from tensorflow.keras.models import load_model
from datetime import timedelta, date
from azure.storage.blob import BlobServiceClient
import io

# Append project root to sys.path to allow imports from other directories
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kafka_pipeline.config import *
from kafka_pipeline.schemas import StockWatchEvent
from scripts.feature_engineering import engineer_features
from models.baseline_ma import MovingAveragePredictor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PredictionConsumer:
    def __init__(self, bootstrap_servers, sasl_username, sasl_password, group_id, topics, load_historical=True):
        # Kafka Clients
        self.consumer = KafkaConsumer(
            *topics,
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            sasl_mechanism='PLAIN',
            security_protocol='SASL_SSL',
            sasl_plain_username=sasl_username,
            sasl_plain_password=sasl_password,
            auto_offset_reset='latest',
            value_deserializer=lambda v: json.loads(v.decode('utf-8'))
        )
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            sasl_mechanism='PLAIN',
            security_protocol='SASL_SSL',
            sasl_plain_username=sasl_username,
            sasl_plain_password=sasl_password,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        
        # Azure Blob Client
        self.blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
        self.container_client = self.blob_service_client.get_container_client(AZURE_STORAGE_CONTAINER_NAME)

        # Data Buffers and Models
        self.data_buffer = {symbol: pd.DataFrame() for symbol in SYMBOLS}
        self.buffer_lock = Lock()
        self.pending_predictions = {}
        self.lstm_model = None
        self.rf_model = None
        self.scaler = None
        self.ma_model = MovingAveragePredictor(window=20)
        self.feature_cols = ['open', 'high', 'low', 'close', 'volume', 'sentiment_mean', 'news_count', 'return', 'log_return', 'ema_10', 'ema_50', 'rsi', 'macd', 'bb_high', 'bb_low', 'atr']
        self.sequence_len = 60

        self.online_evaluation = {} 
        # Structure: { 
        #   'AAPL': {
        #       'predictions': [{'timestamp': '2025-10-30 10:00:00', 'predicted_close': 155.5, 'actual_close': None}],
        #       'performance': [{'timestamp': '2025-10-30 10:00:00', 'error': 0.5}]
        #   }
        # }

        try:
            # --- DYNAMIC DATE LOGIC ---
            # Set the buffer end date to yesterday to align with the latest complete trading data.
            self.buffer_end_date = date.today() - timedelta(days=1)
            logger.info(f"Buffer end date set to: {self.buffer_end_date}")
            # --- END DYNAMIC DATE LOGIC ---
            
            self.load_historical_buffer_from_blob()
            self.load_models_and_scaler()
        except Exception as e:
            logger.error(f"Error initializing PredictionConsumer: {e}", exc_info=True)

    def load_models_and_scaler(self):
        """Loads the ML models and the scaler."""
        try:
            logger.info("Loading ML models and scaler...")
            # Model paths - check parent directory if not in current dir
            model_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            lstm_path = 'multi_stock_model_LSTM.keras' if os.path.exists('multi_stock_model_LSTM.keras') else os.path.join(model_dir, 'multi_stock_model_LSTM.keras')
            rf_path = 'random_forest_model.pkl' if os.path.exists('random_forest_model.pkl') else os.path.join(model_dir, 'random_forest_model.pkl')
            scaler_path = 'scaler.pkl' if os.path.exists('scaler.pkl') else os.path.join(model_dir, 'scaler.pkl')
            
            self.lstm_model = load_model(lstm_path)
            self.rf_model = joblib.load(rf_path)
            self.scaler = joblib.load(scaler_path)
            logger.info("Models and scaler loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load models or scaler: {e}", exc_info=True)
            # Depending on the desired behavior, you might want to exit or handle this differently
            raise

    def load_historical_buffer_from_blob(self):
        """Loads historical data from Azure Blob Storage to prime the buffer."""
        logger.info("Attempting to load historical buffer from Azure Blob Storage...")
        
        # Use the dynamic end_date set in the constructor
        end_date = self.buffer_end_date
        
        # Go back up to 90 days to find enough data
        for i in range(90):
            current_date = end_date - timedelta(days=i)
            date_str = current_date.strftime('%Y-%m-%d')
            
            # Assuming data is stored hourly in the blob container
            for hour in range(9, 17): # Trading hours
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
                                # Prepend the historical data
                                self.data_buffer[symbol] = pd.concat([symbol_df, self.data_buffer[symbol]], ignore_index=True)
                                self.data_buffer[symbol].sort_values(by='timestamp', inplace=True)
                except Exception:
                    # It's okay if a blob for a certain hour/day doesn't exist
                    continue
        
        for symbol, df in self.data_buffer.items():
            if not df.empty:
                logger.info(f"Loaded {len(df)} historical records for {symbol} from Blob Storage.")
            else:
                logger.warning(f"Could not find any historical data for {symbol} in Blob Storage.")
    
    def predict_and_store(self, symbol, new_data_df):
        """
        Calculates features for a new data point using historical context,
        appends the featured point to the buffer, and then makes a prediction.
        """
        with self.buffer_lock:
            historical_buffer = self.data_buffer[symbol]

            # For feature calculation, we need historical context + the new point.
            # We take the last ~100 points to ensure indicators can be calculated.
            context_df = pd.concat([historical_buffer.tail(100), new_data_df], ignore_index=True)
            
            # Engineer features on this temporary, combined dataframe.
            featured_context_df = engineer_features(context_df.copy())
            
            # The result we care about is the very last row, which is our new data with features.
            new_featured_row = featured_context_df.tail(1)

            # Append this new, clean, featured row to our main buffer.
            self.data_buffer[symbol] = pd.concat([historical_buffer, new_featured_row], ignore_index=True)

            # Now, the main buffer is updated. Check if we have enough data to predict.
            if self.data_buffer[symbol].shape[0] < self.sequence_len:
                logger.warning(f"Not enough data in main buffer for {symbol} to predict. Need {self.sequence_len}, have {self.data_buffer[symbol].shape[0]}.")
                return

            # The sequence for prediction is the tail of our now-updated main buffer.
            sequence_df = self.data_buffer[symbol].tail(self.sequence_len)
            
            # Ensure no NaNs made it into the final sequence (shouldn't happen with this logic, but as a safeguard)
            if sequence_df.isnull().values.any():
                logger.error(f"NaN values detected in prediction sequence for {symbol}. Skipping prediction.")
                # As a fallback, let's try to clean it just in case.
                sequence_df = sequence_df.fillna(method='ffill').fillna(0)
                if sequence_df.isnull().values.any():
                    return # Still has NaNs, something is very wrong.

            missing_cols = [col for col in self.feature_cols if col not in sequence_df.columns]
            if missing_cols:
                logger.error(f"Missing feature columns for prediction: {missing_cols}")
                return
            
            sequence_scaled = self.scaler.transform(sequence_df[self.feature_cols]).reshape((1, self.sequence_len, len(self.feature_cols)))

            pred_lstm = self.lstm_model.predict(sequence_scaled, verbose=0)[0][0]
            pred_rf = self.rf_model.predict(sequence_df[self.feature_cols].tail(1))[0]
            pred_ma = self.ma_model.predict(self.data_buffer[symbol]) # MA model benefits from the full buffer

            latest_timestamp = sequence_df['timestamp'].iloc[-1]
            target_timestamp = latest_timestamp + pd.Timedelta(hours=1)
            
            # Send separate predictions for each model
            models = [
                ("LSTM", pred_lstm),
                ("RandomForest", pred_rf),
                ("MovingAverage", pred_ma)
            ]
            
            for model_name, prediction in models:
                response_payload = {
                    "symbol": symbol,
                    "predicted_close": float(prediction),
                    "model_version": model_name,
                    "prediction_timestamp": latest_timestamp.isoformat(),
                    "target_timestamp": target_timestamp.isoformat()
                }
                self.producer.send(TOPIC_RECO_RESPONSES, response_payload)
            
            self.producer.flush()

            # Store LSTM prediction for online evaluation (using LSTM as primary)
            prediction_key = f"{symbol}-{target_timestamp.isoformat()}"
            self.pending_predictions[prediction_key] = float(pred_lstm)
            
            logger.info(f"PREDICTIONS for {symbol} targeting {target_timestamp}: LSTM={pred_lstm:.2f}, RF={pred_rf:.2f}, MA={pred_ma:.2f}")
            
            # Trim the buffer to prevent it from growing indefinitely
            self.data_buffer[symbol] = self.data_buffer[symbol].tail(500)

            # --- ONLINE EVALUATION ---
            # The new_data_df contains the ACTUAL data for the current timestamp.
            # We need to find the prediction we made for this timestamp in the *previous* step.
            current_timestamp = new_data_df['timestamp'].iloc[0]
            
            if symbol in self.online_evaluation and 'predictions' in self.online_evaluation[symbol]:
                # Find the prediction for the current timestamp
                for pred_record in self.online_evaluation[symbol]['predictions']:
                    # Timestamps should be compared as datetime objects
                    pred_timestamp = pd.to_datetime(pred_record['timestamp'])
                    if pred_timestamp == current_timestamp and pred_record['actual_close'] is None:
                        actual_close = new_data_df['close'].iloc[0]
                        predicted_close = pred_record['predicted_close_lstm'] # Using LSTM for eval
                        
                        error = actual_close - predicted_close
                        pred_record['actual_close'] = actual_close
                        
                        if 'performance' not in self.online_evaluation[symbol]:
                            self.online_evaluation[symbol]['performance'] = []
                        
                        self.online_evaluation[symbol]['performance'].append({
                            'timestamp': current_timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                            'error': error
                        })
                        
                        logger.info(f"ONLINE EVAL for {symbol} at {current_timestamp}: Actual={actual_close:.2f}, Pred={predicted_close:.2f}, Error={error:.2f}")
                        break # Stop searching once found and updated
            # --- END ONLINE EVALUATION ---


            # Now, make a new prediction for the *next* timestamp
            try:
                # Predict for the next hour
                # The sequence for prediction is the tail of our now-updated main buffer.
                sequence_df_next = self.data_buffer[symbol].tail(self.sequence_len)
                
                # Ensure no NaNs made it into the final sequence (shouldn't happen with this logic, but as a safeguard)
                if sequence_df_next.isnull().values.any():
                    logger.error(f"NaN values detected in prediction sequence for {symbol}. Skipping prediction.")
                    # As a fallback, let's try to clean it just in case.
                    sequence_df_next = sequence_df_next.fillna(method='ffill').fillna(0)
                    if sequence_df_next.isnull().values.any():
                        return # Still has NaNs, something is very wrong.

                missing_cols_next = [col for col in self.feature_cols if col not in sequence_df_next.columns]
                if missing_cols_next:
                    logger.error(f"Missing feature columns for prediction: {missing_cols_next}")
                    return
                
                sequence_scaled_next = self.scaler.transform(sequence_df_next[self.feature_cols]).reshape((1, self.sequence_len, len(self.feature_cols)))

                lstm_pred = self.lstm_model.predict(sequence_scaled_next, verbose=0)[0][0]
                rf_pred = self.rf_model.predict(sequence_df_next[self.feature_cols].tail(1))[0]
                ma_pred = self.ma_model.predict(self.data_buffer[symbol]) # MA model benefits from the full buffer
                
                # The next timestamp is 1 hour after the current one
                next_timestamp = current_timestamp + pd.Timedelta(hours=1)

                logger.info(f"PREDICTION for {symbol} at {next_timestamp}: LSTM={lstm_pred:.2f}, RF={rf_pred:.2f}, MA={ma_pred:.2f}")

                # Store the new prediction for the next timestamp
                if symbol not in self.online_evaluation:
                    self.online_evaluation[symbol] = {'predictions': [], 'performance': []}
                
                self.online_evaluation[symbol]['predictions'].append({
                    'timestamp': next_timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'predicted_close_lstm': lstm_pred,
                    'predicted_close_rf': rf_pred,
                    'predicted_close_ma': ma_pred,
                    'actual_close': None # This will be filled in when the next data point arrives
                })

            except Exception as e:
                logger.error(f"Error during prediction for {symbol}: {e}", exc_info=True)

    def consume_and_validate(self, max_messages=None):
        """Consumes messages, performs online evaluation, and triggers new predictions."""
        from kafka.errors import CorruptRecordError
        import time
        
        message_count = 0
        corrupt_record_count = 0
        last_committed_offsets = {}
        
        try:
            # Use iterator with error handling
            for message in self.consumer:
                if max_messages and message_count >= max_messages:
                    break
                
                try:
                    event = StockWatchEvent(**message.value)
                    
                    prediction_key = f"{event.symbol}-{pd.to_datetime(event.timestamp).isoformat()}"
                    if prediction_key in self.pending_predictions:
                        predicted_price = self.pending_predictions.pop(prediction_key)
                        actual_price = event.close
                        error = actual_price - predicted_price
                        logger.info(f"ONLINE EVAL for {prediction_key}: Actual={actual_price:.2f}, Pred={predicted_price:.2f}, Error={error:+.2f}")

                    new_data_df = pd.DataFrame([event.model_dump()])
                    new_data_df['timestamp'] = pd.to_datetime(new_data_df['timestamp'])
                    
                    self.predict_and_store(event.symbol, new_data_df)
                    message_count += 1
                    
                    # Track successful message processing for offset management
                    from kafka import TopicPartition
                    tp = TopicPartition(message.topic, message.partition)
                    last_committed_offsets[tp] = message.offset + 1
                    
                except (ValueError, KeyError, TypeError) as e:
                    # Schema validation errors - log and skip
                    logger.warning(f"⚠️  Invalid message format, skipping: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)
                    continue
                    
        except CorruptRecordError as e:
            corrupt_record_count += 1
            logger.warning(f"⚠️  Corrupt record encountered (count: {corrupt_record_count})")
            logger.warning(f"   Error: {e}")
            logger.info("   Attempting to skip corrupt record by seeking to next offset...")
            
            try:
                # Get current assignment
                assignment = self.consumer.assignment()
                
                # For each assigned partition, seek to the next offset if we have one
                for tp in assignment:
                    try:
                        # Get the end offset for this partition
                        end_offsets = self.consumer.end_offsets([tp])
                        end_offset = end_offsets.get(tp)
                        
                        if end_offset is not None:
                            # Seek to end to skip corrupt records
                            logger.info(f"   Seeking partition {tp} to offset {end_offset} to skip corrupt records")
                            self.consumer.seek(tp, end_offset)
                        else:
                            # If we can't get end offset, try to commit and let auto-reset handle it
                            logger.info(f"   Committing offsets for {tp}")
                            self.consumer.commit()
                    except Exception as seek_error:
                        logger.warning(f"   Could not seek partition {tp}: {seek_error}")
                
                # Continue consuming after seeking
                logger.info("   Resuming consumption after skipping corrupt record...")
                return self.consume_and_validate(max_messages=max_messages)
                
            except Exception as recovery_error:
                logger.error(f"   Failed to recover from corrupt record: {recovery_error}")
                logger.error("   Consumer will stop. Consider using a different consumer group or cleaning the topic.")
                
        except KeyboardInterrupt:
            logger.info("Consumer interrupted by user")
        except Exception as e:
            error_str = str(e)
            if "corrupt" in error_str.lower() or "CorruptRecordError" in str(type(e)):
                corrupt_record_count += 1
                logger.warning(f"⚠️  Corrupt record error (count: {corrupt_record_count}): {e}")
                logger.info("   Attempting recovery...")
                # Try to continue with a new consumer group or seek past
                try:
                    assignment = self.consumer.assignment()
                    for tp in assignment:
                        end_offsets = self.consumer.end_offsets([tp])
                        end_offset = end_offsets.get(tp)
                        if end_offset:
                            self.consumer.seek(tp, end_offset)
                    logger.info("   Recovery attempted. You may need to use a different consumer group.")
                except:
                    pass
            else:
                logger.error(f"Fatal error in consumer: {e}", exc_info=True)
        finally:
            if corrupt_record_count > 0:
                logger.warning(f"⚠️  Total corrupt records encountered: {corrupt_record_count}")
            logger.info(f"✓ Processed {message_count} messages successfully")
            self.consumer.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Kafka Consumer for Stock Predictions")
    parser.add_argument("--max-messages", type=int, help="Maximum number of messages to consume")
    args = parser.parse_args()

    consumer = PredictionConsumer(
        bootstrap_servers=KAFKA_BROKER,
        sasl_username=SASL_USERNAME,
        sasl_password=SASL_PASSWORD,
        group_id=CONSUMER_GROUP,
        topics=[TOPIC_WATCH],
    )
    consumer.consume_and_validate(max_messages=args.max_messages)
