"""
Load historical data into consumer's prediction buffer

This script helps the consumer initialize its in-memory buffer with historical data
so predictions can start immediately when real-time data arrives.

Usage:
    python scripts/load_historical_buffer.py --days 7
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_recent_historical_data(csv_path='Merged_dataset.csv', days=7):
    """
    Load the most recent N days of historical data for buffer initialization
    
    Args:
        csv_path: Path to merged dataset
        days: Number of recent days to load (default: 7)
    
    Returns:
        DataFrame with recent data, grouped by symbol
    """
    logger.info(f"Loading last {days} days of historical data from {csv_path}...")
    
    # Load full dataset
    df = pd.read_csv(csv_path)
    
    # Rename 'time' to 'timestamp' for consistency
    if 'time' in df.columns:
        df = df.rename(columns={'time': 'timestamp'})
    
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Get the most recent date in the dataset
    max_date = df['timestamp'].max()
    cutoff_date = max_date - timedelta(days=days)
    
    # Filter to recent data
    recent_df = df[df['timestamp'] >= cutoff_date].copy()
    recent_df = recent_df.sort_values('timestamp')
    
    logger.info(f"Loaded {len(recent_df)} records from {recent_df['timestamp'].min()} to {recent_df['timestamp'].max()}")
    
    # Group by symbol
    buffer_data = {}
    for symbol in recent_df['symbol'].unique():
        symbol_df = recent_df[recent_df['symbol'] == symbol]
        buffer_data[symbol] = symbol_df.to_dict('records')
        logger.info(f"  {symbol}: {len(symbol_df)} records")
    
    return buffer_data

def export_buffer_data(buffer_data, output_path='data_buffer_init.json'):
    """Export buffer data to JSON for easy loading"""
    import json
    
    # Convert timestamps to strings for JSON serialization
    serializable_data = {}
    for symbol, records in buffer_data.items():
        serializable_data[symbol] = []
        for record in records:
            record_copy = record.copy()
            if 'timestamp' in record_copy:
                record_copy['timestamp'] = str(record_copy['timestamp'])
            serializable_data[symbol].append(record_copy)
    
    with open(output_path, 'w') as f:
        json.dump(serializable_data, f, indent=2)
    
    logger.info(f"Exported buffer initialization data to {output_path}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Load historical data for buffer initialization")
    parser.add_argument("--days", type=int, default=7, help="Number of recent days to load")
    parser.add_argument("--csv", default="Merged_dataset.csv", help="Path to merged dataset")
    parser.add_argument("--output", default="data_buffer_init.json", help="Output JSON file")
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("LOADING HISTORICAL DATA FOR PREDICTION BUFFER")
    logger.info("=" * 60)
    
    buffer_data = load_recent_historical_data(csv_path=args.csv, days=args.days)
    export_buffer_data(buffer_data, output_path=args.output)
    
    logger.info("\n" + "=" * 60)
    logger.info("BUFFER DATA READY")
    logger.info("=" * 60)
    logger.info(f"\nTo use this data, update the consumer to load from {args.output}")

