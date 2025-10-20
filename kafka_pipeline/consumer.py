"""
Kafka Consumer - Processes stock data stream and writes snapshots
Validates schemas and stores in object storage (parquet format)

This handles Task 2: Stream ingestor with durable snapshots
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

from config import *
from schemas import StockWatchEvent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StockDataConsumer:
    def __init__(self):
        """Initialize Kafka consumer"""
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
        
        self.buffer = []
        self.snapshot_count = 0
        logger.info(f"✅ Consumer connected, listening to {TOPIC_WATCH}")
    
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
        logger.info(f"📦 Snapshot written: {blob_path} ({len(records)} records)")
    
    def consume_and_validate(self, max_messages=None):
        """
        Consume messages, validate schemas, and write snapshots
        
        Args:
            max_messages: Stop after N messages (None = run forever)
        """
        message_count = 0
        
        try:
            for message in self.consumer:
                try:
                    # Validate schema
                    event = StockWatchEvent(**message.value)
                    
                    # Add to buffer
                    self.buffer.append(event.dict())
                    message_count += 1
                    
                    if message_count % 10 == 0:
                        logger.info(f"📥 Processed {message_count} messages, buffer size: {len(self.buffer)}")
                    
                    # Write snapshot every 50 messages or every hour
                    if len(self.buffer) >= 50:
                        self.write_parquet_snapshot(self.buffer)
                        self.buffer = []
                    
                    if max_messages and message_count >= max_messages:
                        logger.info(f"✅ Reached max messages ({max_messages})")
                        break
                        
                except ValidationError as e:
                    logger.error(f"❌ Schema validation failed: {e}")
                    logger.error(f"Message: {message.value}")
                except Exception as e:
                    logger.error(f"❌ Error processing message: {e}")
        
        finally:
            # Write any remaining buffered records
            if self.buffer:
                self.write_parquet_snapshot(self.buffer)
            
            logger.info(f"🎉 Consumed {message_count} messages, wrote {self.snapshot_count} snapshots")
            self.consumer.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Consume stock data from Kafka")
    parser.add_argument("--max-messages", type=int, help="Max messages to consume", default=None)
    args = parser.parse_args()
    
    consumer = StockDataConsumer()
    consumer.consume_and_validate(max_messages=args.max_messages)

