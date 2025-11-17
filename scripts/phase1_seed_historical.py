"""
PHASE 1: Seed Historical Data (Till Oct 10, 2025)

This script uploads the training data baseline to Azure Blob Storage.
Data range: March 2022 - October 10, 2025

Usage:
    python scripts/phase1_seed_historical.py
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

def seed_historical_till_oct10(csv_path='Merged_dataset.csv'):
    """
    Upload historical data (till Oct 10, 2025) to Azure Blob Storage
    This is the TRAINING DATA baseline
    """
    # Load environment variables
    storage_connection = os.getenv('STORAGE_CONNECTION')
    storage_container = os.getenv('STORAGE_CONTAINER', 'snapshots')
    
    if not storage_connection:
        logger.error("ERROR: STORAGE_CONNECTION not found in .env file")
        return
    
    # Connect to Azure Blob Storage
    logger.info("=" * 70)
    logger.info("PHASE 1: SEEDING HISTORICAL DATA (TRAINING BASELINE)")
    logger.info("=" * 70)
    logger.info("Connecting to Azure Blob Storage...")
    
    blob_service = BlobServiceClient.from_connection_string(storage_connection)
    container_client = blob_service.get_container_client(storage_container)
    
    # Create container if it doesn't exist
    try:
        container_client.create_container()
        logger.info(f"Created container: {storage_container}")
    except Exception:
        logger.info(f"Container already exists: {storage_container}")
    
    # Load historical data
    logger.info(f"\nLoading historical data from {csv_path}...")
    df = pd.read_csv(csv_path)
    
    # Rename 'time' to 'timestamp' for consistency
    if 'time' in df.columns:
        df = df.rename(columns={'time': 'timestamp'})
    
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Filter to Oct 10, 2025 and earlier (TRAINING DATA ONLY)
    cutoff_date = pd.Timestamp('2025-10-10 23:59:59')
    df = df[df['timestamp'] <= cutoff_date].copy()
    
    logger.info(f"\n📊 DATA SUMMARY:")
    logger.info(f"  Total records: {len(df):,}")
    logger.info(f"  Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    logger.info(f"  Symbols: {df['symbol'].unique().tolist()}")
    logger.info(f"  Cutoff: October 10, 2025 (Training data only)")
    
    # Add date and hour columns for partitioning
    df['date'] = df['timestamp'].dt.date
    df['hour'] = df['timestamp'].dt.hour
    
    # Group by date and hour
    grouped = df.groupby(['date', 'hour'])
    total_partitions = len(grouped)
    
    logger.info(f"\n📦 Creating {total_partitions} partitioned snapshots...")
    
    uploaded_count = 0
    for (date, hour), group_df in grouped:
        try:
            # Remove partitioning columns from data
            data_df = group_df.drop(columns=['date', 'hour'])
            
            # Create blob path: v1/date=YYYY-MM-DD/hour=HH/training_data.parquet
            blob_path = f"v1/date={date}/hour={hour:02d}/training_data.parquet"
            
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
                logger.info(f"  Progress: {uploaded_count}/{total_partitions} partitions ({uploaded_count/total_partitions*100:.1f}%)")
                
        except Exception as e:
            logger.error(f"ERROR: Failed to upload {blob_path}: {e}")
    
    logger.info(f"\n✅ SUCCESS: Phase 1 Complete!")
    logger.info(f"  Uploaded: {uploaded_count} partitions")
    logger.info(f"  Container: {storage_container}")
    logger.info(f"  Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    logger.info(f"  Total records: {len(df):,}")
    
    # Verify a few uploads
    logger.info(f"\n🔍 Verifying uploads (checking first 3 partitions)...")
    for i, (date, hour) in enumerate(list(grouped.groups.keys())[:3]):
        blob_path = f"v1/date={date}/hour={hour:02d}/training_data.parquet"
        blob_client = container_client.get_blob_client(blob_path)
        if blob_client.exists():
            props = blob_client.get_blob_properties()
            logger.info(f"  ✅ {blob_path} - Size: {props.size:,} bytes")
        else:
            logger.error(f"  ❌ {blob_path} - NOT FOUND")
    
    logger.info("\n" + "=" * 70)
    logger.info("PHASE 1 COMPLETE - Ready for Phase 2 (Backfill Oct 11-30)")
    logger.info("=" * 70)

if __name__ == "__main__":
    seed_historical_till_oct10()

