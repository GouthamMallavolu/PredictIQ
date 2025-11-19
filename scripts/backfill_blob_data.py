"""
Backfill Azure Blob Storage with historical stock data

Fetches data from Alpha Vantage API for dates Oct 31 - Nov 17, 2025
and uploads to Azure Blob Storage in the same format as existing data.
"""
import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
import pandas as pd
import requests
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
import io

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kafka_pipeline.config import SYMBOLS

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
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
        # Alpha Vantage intraday endpoint (month parameter)
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


def process_and_upload_data(df: pd.DataFrame, date: str, blob_service_client: BlobServiceClient, container_name: str):
    """
    Process DataFrame and upload to blob storage by hour.
    
    Args:
        df: DataFrame with stock data
        date: Date in YYYY-MM-DD format
        blob_service_client: Azure Blob Service Client
        container_name: Container name
    """
    if df.empty:
        return
    
    # Group by hour
    df['hour'] = df['time'].dt.hour
    
    container_client = blob_service_client.get_container_client(container_name)
    
    for hour in sorted(df['hour'].unique()):
        hour_df = df[df['hour'] == hour].copy()
        
        if hour_df.empty:
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
        
        logger.info(f"  ✓ Uploaded {blob_path} ({len(hour_df)} records)")


def backfill_date_range(start_date: str, end_date: str):
    """
    Backfill data for a date range.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format (inclusive)
    """
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
        logger.error("STORAGE_CONNECTION not found in environment variables")
        return
    
    # Connect to blob storage
    blob_service_client = BlobServiceClient.from_connection_string(connect_str)
    logger.info(f"Connected to Azure Blob Storage container: {container_name}")
    
    # Generate date range
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    dates = pd.date_range(start, end, freq='D')
    
    logger.info(f"Backfilling data from {start_date} to {end_date} ({len(dates)} days)")
    
    total_requests = 0
    for date in dates:
        date_str = date.strftime('%Y-%m-%d')
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing date: {date_str}")
        logger.info(f"{'='*60}")
        
        # Skip weekends (Saturday=5, Sunday=6)
        if date.weekday() >= 5:
            logger.info(f"  Skipping weekend: {date_str}")
            continue
        
        # Fetch data for all symbols
        all_data = []
        for symbol in SYMBOLS:
            df = fetch_stock_data_for_date(symbol, date_str, api_key)
            if not df.empty:
                all_data.append(df)
            
            # Rate limiting: Alpha Vantage free tier allows 5 calls/minute
            time.sleep(12)  # Wait 12 seconds between requests
            total_requests += 1
            
            # If we hit 25 requests, wait (free tier limit is 25/day)
            if total_requests >= 25:
                logger.warning("⚠️  Reached 25 API requests. Waiting 24 hours...")
                logger.warning("   For production, use premium API key or split across days.")
                break
        
        if all_data:
            # Combine all symbols
            combined_df = pd.concat(all_data, ignore_index=True)
            
            # Process and upload by hour
            process_and_upload_data(combined_df, date_str, blob_service_client, container_name)
        
        logger.info(f"✓ Completed {date_str}")
    
    logger.info(f"\n{'='*60}")
    logger.info("Backfill complete!")
    logger.info(f"{'='*60}")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Backfill Azure Blob Storage with historical stock data')
    parser.add_argument('--start-date', type=str, default='2025-10-31', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, default='2025-11-17', help='End date (YYYY-MM-DD)')
    args = parser.parse_args()
    
    backfill_date_range(args.start_date, args.end_date)


if __name__ == '__main__':
    main()

