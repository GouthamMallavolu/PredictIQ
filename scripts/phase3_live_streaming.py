import os
import sys
import json
import time
import logging
from datetime import date
from kafka import KafkaProducer
import pandas as pd
from azure.storage.blob import BlobServiceClient
import io
from dotenv import load_dotenv

# Load environment variables from .env file FIRST
load_dotenv()

# Append project root to sys.path to allow imports from other directories
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kafka_pipeline.config import (
    KAFKA_BROKER, SASL_USERNAME, SASL_PASSWORD, TOPIC_WATCH,
    AZURE_STORAGE_CONNECTION_STRING, AZURE_STORAGE_CONTAINER_NAME
)
from kafka_pipeline.schemas import StockWatchEvent

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Producer and Blob Service Setup ---
def initialize_clients():
    """Initializes and returns KafkaProducer and Azure ContainerClient."""
    try:
        if not AZURE_STORAGE_CONNECTION_STRING:
            raise ValueError("AZURE_STORAGE_CONNECTION_STRING ('STORAGE_CONNECTION' in .env) is not set.")

        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BROKER,
            sasl_mechanism='PLAIN',
            security_protocol='SASL_SSL',
            sasl_plain_username=SASL_USERNAME,
            sasl_plain_password=SASL_PASSWORD,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
        container_client = blob_service_client.get_container_client(AZURE_STORAGE_CONTAINER_NAME)
        return producer, container_client
    except Exception as e:
        logger.error(f"FATAL: Could not connect to services. Exiting. Error: {e}")
        sys.exit(1)


def stream_data_from_blob(target_date, producer, container_client):
    """
    Streams data from Azure Blob Storage snapshots for a specific date.
    """
    logger.info(f"📡 Simulating trading day for: {target_date} from Azure Blob Storage")
    logger.info(f"⏰ Streaming hourly data with a 1-minute delay between hours.")
    
    trading_hours = range(9, 17) # 9 AM to 4 PM

    for hour in trading_hours:
        logger.info(f"\n--- Processing {target_date} hour {hour:02d}:00 ---")
        
        # Corrected path format (no container name)
        blob_path = f"v1/date={target_date}/hour={hour:02d}/backfill_oct.parquet"
        
        try:
            blob_client = container_client.get_blob_client(blob_path)
            if not blob_client.exists():
                logger.warning(f"Blob not found, skipping: {blob_path}")
                # Try the other filename format just in case
                blob_path_alt = f"v1/date={target_date}/hour={hour:02d}/snapshot_000.parquet"
                blob_client = container_client.get_blob_client(blob_path_alt)
                if not blob_client.exists():
                    logger.warning(f"Also not found, skipping for real: {blob_path_alt}")
                    continue
                else:
                    logger.info(f"Found data at alternate path: {blob_path_alt}")


            downloader = blob_client.download_blob()
            blob_bytes = downloader.readall()
            df = pd.read_parquet(io.BytesIO(blob_bytes))

            if df.empty:
                logger.warning(f"No data in snapshot for hour {hour:02d}:00.")
                continue

            df['timestamp'] = pd.to_datetime(df['timestamp'])

            for _, row in df.iterrows():
                event = StockWatchEvent(
                    symbol=row['symbol'],
                    timestamp=row['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=int(row["volume"]),
                    sentiment_mean=float(row.get("sentiment_mean", 0.0)),
                    news_count=int(row.get("news_count", 0))
                )
                producer.send(TOPIC_WATCH, event.dict())
                logger.info(f"✅ Sent data for {row['symbol']} at {event.timestamp}")

        except Exception as e:
            logger.error(f"Could not process blob for hour {hour}. Error: {e}", exc_info=True)
        
        producer.flush()
        logger.info(f"--- Finished hour {hour:02d}:00. Waiting 1 minute... ---")
        if hour < 16:
            time.sleep(60)


def main():
    logger.info("======================================================================")
    logger.info("PHASE 3: SIMULATED LIVE STREAMING from Azure Blob Storage")
    logger.info("======================================================================")
    
    producer, container_client = initialize_clients()
    target_date = date(2025, 10, 30)

    try:
        stream_data_from_blob(target_date, producer, container_client)
        logger.info("\n✅ Full trading day simulation complete.")
    except KeyboardInterrupt:
        logger.info("\n👋 Simulation stopped by user.")
    finally:
        if producer:
            producer.close()
            logger.info("Producer connection closed.")


if __name__ == "__main__":
    main()
