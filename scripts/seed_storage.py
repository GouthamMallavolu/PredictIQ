"""
Seed Azure Blob Storage with historical data from Merged_dataset.csv

This script:
1. Reads the merged historical dataset (up to Oct 10, 2025)
2. Partitions it by date and hour (same structure as consumer snapshots)
3. Uploads to Azure Blob Storage as Parquet files
4. Ensures new real-time data can be appended seamlessly

Usage:
    python scripts/seed_storage.py
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from azure.storage.blob import BlobServiceClient
import io
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_historical_data(csv_path='Merged_dataset.csv'):
    """
    Upload historical data to Azure Blob Storage in the same format as consumer snapshots
    """
    # Load environment variables
    storage_connection = os.getenv('STORAGE_CONNECTION')
    storage_container = os.getenv('STORAGE_CONTAINER', 'snapshots')
    
    if not storage_connection:
        logger.error("ERROR: STORAGE_CONNECTION not found in environment variables")
        return
    
    # Connect to Azure Blob Storage
    logger.info("Connecting to Azure Blob Storage...")
    blob_service = BlobServiceClient.from_connection_string(storage_connection)
    container_client = blob_service.get_container_client(storage_container)
    
    # Create container if it doesn't exist
    try:
        container_client.create_container()
        logger.info(f"Created container: {storage_container}")
    except Exception as e:
        logger.info(f"Container already exists: {storage_container}")
    
    # Load historical data
    logger.info(f"Loading historical data from {csv_path}...")
    df = pd.read_csv(csv_path)
    
    # Rename 'time' to 'timestamp' for consistency with consumer schema
    if 'time' in df.columns:
        df = df.rename(columns={'time': 'timestamp'})
    
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    logger.info(f"Loaded {len(df)} records from {df['timestamp'].min()} to {df['timestamp'].max()}")
    logger.info(f"Symbols: {df['symbol'].unique().tolist()}")
    
    # Add date and hour columns for partitioning
    df['date'] = df['timestamp'].dt.date
    df['hour'] = df['timestamp'].dt.hour
    
    # Group by date and hour
    grouped = df.groupby(['date', 'hour'])
    total_partitions = len(grouped)
    
    logger.info(f"Creating {total_partitions} partitioned snapshots...")
    
    uploaded_count = 0
    for (date, hour), group_df in grouped:
        try:
            # Remove partitioning columns from data
            data_df = group_df.drop(columns=['date', 'hour'])
            
            # Create blob path matching consumer format
            # Path: v1/date=YYYY-MM-DD/hour=HH/historical_snapshot.parquet
            blob_path = f"v1/date={date}/hour={hour:02d}/historical_snapshot.parquet"
            
            # Convert to parquet
            table = pa.Table.from_pandas(data_df)
            parquet_buffer = io.BytesIO()
            pq.write_table(table, parquet_buffer)
            parquet_buffer.seek(0)
            
            # Upload to blob storage
            blob_client = container_client.get_blob_client(blob_path)
            blob_client.upload_blob(parquet_buffer, overwrite=True)
            
            uploaded_count += 1
            
            if uploaded_count % 100 == 0:
                logger.info(f"Progress: {uploaded_count}/{total_partitions} partitions uploaded")
                
        except Exception as e:
            logger.error(f"ERROR: Failed to upload {blob_path}: {e}")
    
    logger.info(f"SUCCESS: Uploaded {uploaded_count} partitions to Azure Blob Storage")
    logger.info(f"Container: {storage_container}")
    logger.info(f"Historical data range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    logger.info(f"Total records: {len(df)}")
    
    # Verify a few uploads
    logger.info("\nVerifying uploads (checking first 3 partitions)...")
    for i, (date, hour) in enumerate(list(grouped.groups.keys())[:3]):
        blob_path = f"v1/date={date}/hour={hour:02d}/historical_snapshot.parquet"
        blob_client = container_client.get_blob_client(blob_path)
        if blob_client.exists():
            props = blob_client.get_blob_properties()
            logger.info(f"✅ {blob_path} - Size: {props.size} bytes")
        else:
            logger.error(f"❌ {blob_path} - NOT FOUND")

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("SEEDING AZURE BLOB STORAGE WITH HISTORICAL DATA")
    logger.info("=" * 60)
    seed_historical_data()
    logger.info("\n" + "=" * 60)
    logger.info("SEEDING COMPLETE - Ready for real-time data ingestion!")
    logger.info("=" * 60)

