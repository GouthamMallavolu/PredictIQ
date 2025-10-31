"""
Kafka Consumer - Processes stock data stream, writes snapshots, and makes real-time predictions
Validates schemas, stores in object storage (parquet format), and generates predictions

This handles:
- Task 2: Stream ingestor with durable snapshots
- Real-time predictions using trained ML models
"""
import json
import logging
from datetime import datetime
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from kafka import KafkaConsumer
from azure.storage.blob import BlobServiceClient
from pydantic import ValidationError
import io
import sys
import os

from config import *
from schemas import StockWatchEvent

# Add parent directory to path for predictor import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StockDataConsumer:
    def __init__(self):
        """Initialize Kafka consumer with storage and prediction capability"""
        self.consumer = KafkaConsumer(
            TOPIC_WATCH,
            bootstrap_servers=[KAFKA_BROKER],
            security_protocol='SASL_SSL',
            sasl_mechanism='PLAIN',
            sasl_plain_username=SASL_USERNAME,
            sasl_plain_password=SASL_PASSWORD,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            group_id=CONSUMER_GROUP,
            max_poll_records=100
        )
        
        # Azure Blob Storage for snapshots
        self.blob_service = BlobServiceClient.from_connection_string(STORAGE_CONNECTION)
        self.container_client = self.blob_service.get_container_client(STORAGE_CONTAINER)
        try:
            self.container_client.create_container()
        except:
            pass
        
        # Storage buffer
        self.buffer = []
        self.snapshot_count = 0
        
        # Prediction models and data buffer
        self.predictor = None
        self.data_buffer = {}  # Store recent data for each symbol
        self.buffer_size = 50  # Keep last 50 hours of data for predictions
        
        logger.info(f"SUCCESS: Consumer connected, listening to {TOPIC_WATCH}")
        self.initialize_predictor()
    
    def write_parquet_snapshot(self, records):
        """Write records to parquet in object storage"""
        if not records:
            return
        
        df = pd.DataFrame(records)
        
        # Organize by date and hour for efficient querying
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        date_str = df['timestamp'].iloc[0].strftime('%Y-%m-%d')
        hour_str = df['timestamp'].iloc[0].strftime('%H')
        
        # Path: snapshots/v1/date=YYYY-MM-DD/hour=HH/snapshot_NNN.parquet
        blob_path = f"v1/date={date_str}/hour={hour_str}/snapshot_{self.snapshot_count:03d}.parquet"
        
        # Convert to parquet
        table = pa.Table.from_pandas(df)
        parquet_buffer = io.BytesIO()
        pq.write_table(table, parquet_buffer)
        parquet_buffer.seek(0)
        
        # Upload to blob storage
        blob_client = self.container_client.get_blob_client(blob_path)
        blob_client.upload_blob(parquet_buffer, overwrite=True)
        
        self.snapshot_count += 1
        logger.info(f"SNAPSHOT: Written {blob_path} ({len(records)} records)")
    
    def initialize_predictor(self):
        """Initialize the prediction models"""
        try:
            from api.predictor import ModelPredictor
            self.predictor = ModelPredictor()
            logger.info("SUCCESS: Prediction models loaded")
        except Exception as e:
            logger.error(f"ERROR: Failed to load prediction models: {e}")
            logger.info("INFO: Predictions will be disabled until models are available")
    
    def add_to_buffer(self, symbol, data):
        """Add new data to symbol buffer for predictions"""
        if symbol not in self.data_buffer:
            self.data_buffer[symbol] = []
        
        self.data_buffer[symbol].append(data)
        
        # Keep only last N records
        if len(self.data_buffer[symbol]) > self.buffer_size:
            self.data_buffer[symbol] = self.data_buffer[symbol][-self.buffer_size:]
    
    def get_recent_data(self, symbol):
        """Get recent data for symbol from buffer"""
        if symbol not in self.data_buffer:
            return pd.DataFrame()
        
        # Convert buffer to DataFrame
        data = pd.DataFrame(self.data_buffer[symbol])
        return data
    
    def make_prediction(self, symbol):
        """Make prediction for symbol using recent data"""
        if not self.predictor:
            return None
        
        try:
            recent_data = self.get_recent_data(symbol)
            if recent_data.empty:
                return None
            
            # Make prediction using LSTM model
            prediction = self.predictor.predict_lstm(recent_data)
            
            return {
                'symbol': symbol,
                'predicted_price': prediction,
                'current_price': recent_data['close'].iloc[-1],
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"ERROR: Prediction failed for {symbol}: {e}")
            return None
    
    def consume_and_validate(self, max_messages=None):
        """
        Consume messages, validate schemas, write snapshots, and make real-time predictions
        
        Args:
            max_messages: Stop after N messages (None = run forever)
        """
        message_count = 0
        
        try:
            for message in self.consumer:
                try:
                    # Validate schema
                    event = StockWatchEvent(**message.value)
                    
                    # Add to storage buffer
                    self.buffer.append(event.dict())
                    
                    # Add to prediction buffer
                    self.add_to_buffer(event.symbol, event.dict())
                    
                    message_count += 1
                    
                    if message_count % 10 == 0:
                        logger.info(f"PROCESSED: {message_count} messages, buffer size: {len(self.buffer)}")
                    
                    # Make prediction if we have enough data
                    if len(self.data_buffer[event.symbol]) >= 10:  # At least 10 hours
                        prediction = self.make_prediction(event.symbol)
                        if prediction:
                            logger.info(f"PREDICTION: {event.symbol}: ${prediction['predicted_price']:.2f}")
                    
                    # Write snapshot every 50 messages or every hour
                    if len(self.buffer) >= 50:
                        self.write_parquet_snapshot(self.buffer)
                        self.buffer = []
                    
                    if max_messages and message_count >= max_messages:
                        logger.info(f"SUCCESS: Reached max messages ({max_messages})")
                        break
                        
                except ValidationError as e:
                    logger.error(f"ERROR: Schema validation failed: {e}")
                    logger.error(f"Message: {message.value}")
                except Exception as e:
                    logger.error(f"ERROR: Error processing message: {e}")
        
        finally:
            # Write any remaining buffered records
            if self.buffer:
                self.write_parquet_snapshot(self.buffer)
            
            logger.info(f"SUCCESS: Consumed {message_count} messages, wrote {self.snapshot_count} snapshots")
            self.consumer.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Consume stock data from Kafka")
    parser.add_argument("--max-messages", type=int, help="Max messages to consume", default=None)
    args = parser.parse_args()
    
    consumer = StockDataConsumer()
    consumer.consume_and_validate(max_messages=args.max_messages)

