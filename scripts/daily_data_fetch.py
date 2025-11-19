"""
Daily Data Fetch Script for Azure Blob Storage

Fetches yesterday's stock data from Alpha Vantage API
and uploads to Azure Blob Storage.

Designed to run as a cron job daily.
"""
import os
import sys
import time
import logging
import json
from datetime import datetime, timedelta
import pandas as pd
import requests
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
import io
from kafka import KafkaProducer
from kafka.errors import KafkaError
from pydantic import ValidationError

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kafka_pipeline.config import SYMBOLS, KAFKA_BROKER, SASL_USERNAME, SASL_PASSWORD, TOPIC_WATCH
from kafka_pipeline.schemas import StockWatchEvent

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/daily_data_fetch.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def fetch_stock_data_for_date(symbol: str, date: str, api_key: str) -> pd.DataFrame:
    """
    Fetch stock data for a specific symbol and date from Alpha Vantage.
    
    Args:
        symbol: Stock symbol (e.g., 'AAPL')
        date: Date in YYYY-MM-DD format
        api_key: Alpha Vantage API key
    
    Returns:
        DataFrame with stock data for that date
    """
    try:
        month = date[:7]  # YYYY-MM
        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={symbol}&interval=60min&month={month}&outputsize=full&apikey={api_key}"
        
        logger.info(f"Fetching {symbol} for {date}...")
        r = requests.get(url, timeout=30)
        
        if r.status_code != 200:
            logger.error(f"HTTP {r.status_code} for {symbol} on {date}")
            return pd.DataFrame()
        
        data = r.json()
        
        # Check for API errors
        if "Error Message" in data:
            logger.error(f"API Error for {symbol}: {data['Error Message']}")
            return pd.DataFrame()
        
        if "Note" in data or "Information" in data:
            msg = data.get("Note") or data.get("Information", "")
            logger.warning(f"API Note for {symbol}: {msg}")
            if "rate limit" in msg.lower():
                logger.error("Rate limit hit!")
                return pd.DataFrame()
            return pd.DataFrame()
        
        # Find time series key
        time_series_key = next((k for k in data.keys() if "Time Series" in k), None)
        if not time_series_key:
            logger.warning(f"No time series data for {symbol} on {date}")
            return pd.DataFrame()
        
        # Convert to DataFrame
        ts_data = data[time_series_key]
        df = pd.DataFrame.from_dict(ts_data, orient='index').reset_index()
        df.columns = ['time', 'open', 'high', 'low', 'close', 'volume']
        df['time'] = pd.to_datetime(df['time'])
        df['symbol'] = symbol
        
        # Filter for specific date
        target_date = pd.to_datetime(date).date()
        df = df[df['time'].dt.date == target_date].copy()
        
        # Convert numeric columns
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        logger.info(f"  ✓ Fetched {len(df)} records for {symbol} on {date}")
        return df
        
    except Exception as e:
        logger.error(f"Error fetching {symbol} for {date}: {e}", exc_info=True)
        return pd.DataFrame()


def send_hour_to_kafka(hour_df: pd.DataFrame, kafka_producer: KafkaProducer):
    """
    Send hour's data to Kafka topic.
    
    Args:
        hour_df: DataFrame with one hour's data
        kafka_producer: Kafka producer instance
    """
    if hour_df.empty or kafka_producer is None:
        return
    
    sent_count = 0
    for _, row in hour_df.iterrows():
        try:
            # Ensure required fields exist with defaults
            sentiment_mean = float(row.get('sentiment_mean', 0.0)) if 'sentiment_mean' in row else 0.0
            news_count = int(row.get('news_count', 0)) if 'news_count' in row else 0
            
            # Create StockWatchEvent (similar to producer.py)
            watch_event = StockWatchEvent(
                symbol=str(row['symbol']),
                timestamp=str(row['time']),
                open=float(row['open']),
                high=float(row['high']),
                low=float(row['low']),
                close=float(row['close']),
                volume=int(row['volume']),
                sentiment_mean=sentiment_mean,
                news_count=news_count
            )
            
            kafka_producer.send(
                TOPIC_WATCH,
                key=row['symbol'],
                value=watch_event.model_dump()
            )
            sent_count += 1
        except (ValidationError, KeyError, ValueError) as e:
            logger.warning(f"  ⚠️  Failed to send record to Kafka: {e}")
        except KafkaError as e:
            logger.error(f"  ❌ Kafka send error: {e}")
    
    if sent_count > 0:
        kafka_producer.flush()
        logger.info(f"  📤 Sent {sent_count} records to Kafka topic: {TOPIC_WATCH}")


def process_and_upload_data_hourly(df: pd.DataFrame, date: str, blob_service_client: BlobServiceClient, container_name: str, simulate_realtime: bool = True, hour_delay_seconds: int = 60, kafka_producer: KafkaProducer = None):
    """
    Process DataFrame and upload to blob storage by hour, simulating real-time streaming.
    
    Args:
        df: DataFrame with stock data
        date: Date in YYYY-MM-DD format
        blob_service_client: Azure Blob Service Client
        container_name: Container name
        simulate_realtime: If True, upload hour by hour with delays to simulate real-time
        hour_delay_seconds: Seconds to wait between each hour upload
    """
    if df.empty:
        logger.warning(f"No data to upload for {date}")
        return
    
    # Group by hour
    df['hour'] = df['time'].dt.hour
    hours = sorted(df['hour'].unique())
    
    if not hours:
        logger.warning(f"No hourly data found for {date}")
        return
    
    container_client = blob_service_client.get_container_client(container_name)
    uploaded_count = 0
    
    logger.info(f"Processing {len(hours)} hours of data for {date}")
    
    for hour in hours:
        hour_df = df[df['hour'] == hour].copy()
        
        if hour_df.empty:
            logger.warning(f"  No data for hour {hour:02d}")
            continue
        
        # Drop hour column before saving
        hour_df = hour_df.drop('hour', axis=1)
        
        # Create blob path: v1/date=YYYY-MM-DD/hour=HH/training_data.parquet
        blob_path = f"v1/date={date}/hour={hour:02d}/training_data.parquet"
        
        # Convert to parquet in memory
        parquet_buffer = io.BytesIO()
        hour_df.to_parquet(parquet_buffer, engine='pyarrow', index=False)
        parquet_buffer.seek(0)
        
        # Upload to blob storage
        blob_client = container_client.get_blob_client(blob_path)
        blob_client.upload_blob(parquet_buffer.read(), overwrite=True)
        
        logger.info(f"  ✓ Uploaded hour {hour:02d}: {blob_path} ({len(hour_df)} records)")
        uploaded_count += 1
        
        # Send to Kafka producer (simulating real-time streaming)
        if kafka_producer is not None:
            send_hour_to_kafka(hour_df, kafka_producer)
        
        # Simulate real-time: wait before uploading next hour
        # This simulates data arriving hourly throughout the day
        if simulate_realtime and hour < hours[-1]:  # Don't wait after last hour
            logger.info(f"  ⏳ Waiting {hour_delay_seconds} seconds before next hour (simulating real-time)...")
            time.sleep(hour_delay_seconds)
    
    logger.info(f"✓ Uploaded {uploaded_count} hour files for {date}")


def create_kafka_producer():
    """
    Create and return Kafka producer instance.
    Returns None if Kafka is not configured.
    """
    try:
        if not KAFKA_BROKER or not SASL_PASSWORD:
            logger.warning("Kafka not configured (missing KAFKA_BROKER or KAFKA_PASSWORD). Skipping Kafka producer.")
            return None
        
        producer = KafkaProducer(
            bootstrap_servers=[KAFKA_BROKER],
            security_protocol='SASL_SSL',
            sasl_mechanism='PLAIN',
            sasl_plain_username=SASL_USERNAME,
            sasl_plain_password=SASL_PASSWORD,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            retries=3,
            max_in_flight_requests_per_connection=1
        )
        logger.info(f"✓ Kafka producer connected to {KAFKA_BROKER}")
        return producer
    except Exception as e:
        logger.warning(f"Failed to create Kafka producer: {e}. Continuing without Kafka.")
        return None


def fetch_yesterday_data(simulate_realtime: bool = True, hour_delay_seconds: int = 60):
    """
    Fetch yesterday's stock data and upload to blob storage.
    
    Args:
        simulate_realtime: If True, upload hour by hour with delays to simulate real-time
        hour_delay_seconds: Seconds to wait between each hour upload (if simulate_realtime=True)
    """
    # Get yesterday's date
    yesterday = datetime.now() - timedelta(days=1)
    date_str = yesterday.strftime('%Y-%m-%d')
    
    # Skip weekends
    if yesterday.weekday() >= 5:
        logger.info(f"Skipping weekend: {date_str}")
        return
    
    logger.info(f"{'='*60}")
    logger.info(f"Fetching data for: {date_str}")
    logger.info(f"{'='*60}")
    
    api_key = os.getenv('ALPHA_VANTAGE_KEY')
    if not api_key:
        logger.error("ALPHA_VANTAGE_KEY not found in environment variables")
        return
    
    # Support both naming conventions for compatibility
    connect_str = (os.getenv('STORAGE_CONNECTION') or 
                   os.getenv('AZURE_STORAGE_CONNECTION_STRING') or '').strip()
    container_name = (os.getenv('STORAGE_CONTAINER') or 
                     os.getenv('AZURE_STORAGE_CONTAINER') or 'data').strip()

    if not connect_str:
        logger.error("Azure Storage connection string not found in environment variables")
        logger.error("Set either STORAGE_CONNECTION or AZURE_STORAGE_CONNECTION_STRING")
        return
    
    # Connect to blob storage
    blob_service_client = BlobServiceClient.from_connection_string(connect_str)
    logger.info(f"Connected to Azure Blob Storage container: {container_name}")
    
    # Create Kafka producer (if configured)
    kafka_producer = create_kafka_producer()
    
    # Fetch data for all symbols
    all_data = []
    for i, symbol in enumerate(SYMBOLS):
        df = fetch_stock_data_for_date(symbol, date_str, api_key)
        if not df.empty:
            all_data.append(df)
        
        # Rate limiting: Alpha Vantage free tier allows 5 calls/minute
        # Wait 12 seconds between requests (except for last one)
        if i < len(SYMBOLS) - 1:
            time.sleep(12)
    
    if all_data:
        # Combine all symbols
        combined_df = pd.concat(all_data, ignore_index=True)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Fetched complete data for {date_str}: {len(combined_df)} total records")
        logger.info(f"Now uploading hour by hour to simulate real-time streaming...")
        logger.info(f"{'='*60}\n")
        
        # Process and upload by hour (simulating real-time)
        process_and_upload_data_hourly(combined_df, date_str, blob_service_client, container_name, 
                                      simulate_realtime=simulate_realtime, hour_delay_seconds=hour_delay_seconds,
                                      kafka_producer=kafka_producer)
        
        # Close Kafka producer if it was created
        if kafka_producer is not None:
            kafka_producer.close()
            logger.info("✓ Kafka producer closed")
        
        logger.info(f"\n{'='*60}")
        logger.info(f"✓ Successfully fetched and uploaded data for {date_str}")
        logger.info(f"{'='*60}")
    else:
        logger.warning(f"No data fetched for {date_str}")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Fetch yesterday\'s stock data and upload to blob storage')
    parser.add_argument('--no-simulate-realtime', action='store_true', 
                       help='Upload all hours immediately without delays')
    parser.add_argument('--hour-delay', type=int, default=60,
                       help='Seconds to wait between each hour upload (default: 60)')
    args = parser.parse_args()
    
    try:
        # Ensure logs directory exists
        os.makedirs('logs', exist_ok=True)
        
        simulate_realtime = not args.no_simulate_realtime
        fetch_yesterday_data(simulate_realtime=simulate_realtime, hour_delay_seconds=args.hour_delay)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()

