"""
Validate Predictions on Oct 11-30 Data (Already in Azure)

This script reads the Oct 11-30 data that was already uploaded to Azure,
runs predictions, and calculates validation metrics.

Usage:
    python scripts/validate_oct11_30.py
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import pyarrow.parquet as pq
from azure.storage.blob import BlobServiceClient
import io
import logging
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Import feature engineering utilities
from feature_engineering import engineer_features, validate_features

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_predictions():
    """
    Read Oct 11-30 data from Azure, run predictions, calculate metrics
    """
    # Load config
    symbols = os.getenv('SYMBOLS', 'AAPL,MSFT,NVDA,META,TSLA').split(',')
    storage_connection = os.getenv('STORAGE_CONNECTION')
    storage_container = os.getenv('STORAGE_CONTAINER', 'snapshots')
    
    if not storage_connection:
        logger.error("ERROR: Missing STORAGE_CONNECTION in .env")
        return
    
    logger.info("=" * 70)
    logger.info("VALIDATION: OCT 11-30 PREDICTIONS")
    logger.info("=" * 70)
    
    # Connect to Azure
    logger.info(f"\n📥 Loading historical buffer (before Oct 11) + Oct 11-30 data...")
    blob_service = BlobServiceClient.from_connection_string(storage_connection)
    container_client = blob_service.get_container_client(storage_container)
    
    # STEP 1: Load historical buffer (last 60 days before Oct 11 for context)
    logger.info(f"  📚 Loading historical buffer from Merged_dataset.csv...")
    historical_df = None
    if os.path.exists('Merged_dataset.csv'):
        df = pd.read_csv('Merged_dataset.csv')
        if 'time' in df.columns:
            df = df.rename(columns={'time': 'timestamp'})
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Get last 60 days before Oct 11, 2025
        buffer_start = datetime(2025, 8, 11)  # ~60 days before
        buffer_end = datetime(2025, 10, 10, 23, 59, 59)
        
        historical_df = df[(df['timestamp'] >= buffer_start) & (df['timestamp'] <= buffer_end)].copy()
        logger.info(f"     ✅ Loaded {len(historical_df)} historical records ({buffer_start.date()} to {buffer_end.date()})")
    else:
        logger.warning(f"     ⚠️ Merged_dataset.csv not found - predictions may be less accurate")
    
    # STEP 2: Read Oct 11-30 data from Azure
    logger.info(f"  📥 Loading Oct 11-30 data from Azure Blob Storage...")
    all_data = []
    start_date = datetime(2025, 10, 11)
    end_date = datetime(2025, 10, 30)
    
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        
        # Check all hours for this date
        for hour in range(24):
            blob_path = f"v1/date={date_str}/hour={hour:02d}/backfill_oct.parquet"
            
            try:
                blob_client = container_client.get_blob_client(blob_path)
                if blob_client.exists():
                    # Download and read parquet
                    blob_data = blob_client.download_blob().readall()
                    table = pq.read_table(io.BytesIO(blob_data))
                    df = table.to_pandas()
                    all_data.append(df)
            except Exception as e:
                # Blob doesn't exist or error reading - skip
                pass
        
        current_date += timedelta(days=1)
    
    if not all_data:
        logger.error("❌ No Oct 11-30 data found in Azure Blob Storage")
        logger.info("💡 Run Phase 2 first: python scripts/phase2_backfill_oct11_30.py")
        return
    
    oct_df = pd.concat(all_data, ignore_index=True)
    oct_df['timestamp'] = pd.to_datetime(oct_df['timestamp'])
    logger.info(f"     ✅ Loaded {len(oct_df)} Oct 11-30 records")
    
    # STEP 3: Combine historical buffer + Oct 11-30 data
    if historical_df is not None:
        merged_df = pd.concat([historical_df, oct_df], ignore_index=True)
        logger.info(f"  ✅ Combined: {len(merged_df)} total records (historical + Oct 11-30)")
    else:
        merged_df = oct_df
        logger.info(f"  ✅ Using only Oct 11-30 data: {len(merged_df)} records")
    
    merged_df = merged_df.sort_values(['symbol', 'timestamp']).reset_index(drop=True)
    logger.info(f"  Date range: {merged_df['timestamp'].min()} to {merged_df['timestamp'].max()}")
    logger.info(f"  Symbols: {merged_df['symbol'].unique().tolist()}")
    
    # Engineer features if not present
    logger.info(f"\n🔧 Checking and engineering features...")
    is_valid, missing = validate_features(merged_df)
    
    if not is_valid:
        logger.info(f"  Missing features: {missing}")
        logger.info(f"  Engineering technical indicators...")
        try:
            merged_df = engineer_features(merged_df)
            is_valid, missing = validate_features(merged_df)
            if is_valid:
                logger.info(f"  ✅ All features engineered successfully")
            else:
                logger.error(f"  ❌ Still missing features: {missing}")
                return
        except Exception as e:
            logger.error(f"  ❌ Feature engineering failed: {e}")
            return
    else:
        logger.info(f"  ✅ All required features already present")
    
    # Load predictor
    logger.info(f"\n🤖 Loading ML models...")
    try:
        from api.predictor import ModelPredictor
        predictor = ModelPredictor()
        logger.info(f"  ✅ Models loaded (LSTM, RF, MA)")
    except Exception as e:
        logger.error(f"  ❌ Failed to load models: {e}")
        return
    
    # Make predictions for each symbol
    logger.info(f"\n🔮 Running predictions on Oct 11-30 data...")
    predictions_list = []
    
    # Define Oct 11-30 range for predictions
    oct_start = pd.Timestamp('2025-10-11 00:00:00')
    oct_end = pd.Timestamp('2025-10-30 23:59:59')
    
    for symbol in merged_df['symbol'].unique():
        symbol_df = merged_df[merged_df['symbol'] == symbol].copy().reset_index(drop=True)
        
        if len(symbol_df) < 10:
            logger.warning(f"  ⚠️ {symbol}: Not enough data ({len(symbol_df)} records)")
            continue
        
        # Find the index where Oct 11 starts
        oct_start_idx = symbol_df[symbol_df['timestamp'] >= oct_start].index.min()
        
        if pd.isna(oct_start_idx):
            logger.warning(f"  ⚠️ {symbol}: No Oct 11-30 data found")
            continue
        
        # Count predictions for this symbol
        symbol_predictions = 0
        
        # Predict only for Oct 11-30 timestamps (using historical buffer before each)
        for i in range(oct_start_idx, len(symbol_df)):
            # Only predict if timestamp is in Oct 11-30 range
            if symbol_df.iloc[i]['timestamp'] < oct_start or symbol_df.iloc[i]['timestamp'] > oct_end:
                continue
            
            try:
                # Get historical window (last 50 hours or available) - this includes pre-Oct-11 data!
                window_start = max(0, i - 50)
                historical_data = symbol_df.iloc[window_start:i]
                
                if len(historical_data) < 10:
                    continue
                
                # Make prediction
                predicted_price = predictor.predict_lstm(historical_data)
                
                # Get actual price
                actual_price = symbol_df.iloc[i]['close']
                
                # Calculate error
                error = abs(predicted_price - actual_price)
                error_pct = (error / actual_price * 100) if actual_price > 0 else 0
                
                predictions_list.append({
                    'symbol': symbol,
                    'timestamp': symbol_df.iloc[i]['timestamp'],
                    'actual': actual_price,
                    'predicted': predicted_price,
                    'error': error,
                    'error_pct': error_pct
                })
                
                symbol_predictions += 1
                
            except Exception as e:
                logger.error(f"    ❌ Prediction failed at index {i}: {e}")
                continue
        
        logger.info(f"  {symbol}: Made {symbol_predictions} predictions")
    
    # Calculate validation metrics
    if not predictions_list:
        logger.error("❌ No predictions were made")
        return
    
    pred_df = pd.DataFrame(predictions_list)
    
    # Overall metrics
    mae = pred_df['error'].mean()
    rmse = (pred_df['error'] ** 2).mean() ** 0.5
    mape = pred_df['error_pct'].mean()
    
    logger.info(f"\n" + "=" * 70)
    logger.info(f"📊 OVERALL VALIDATION METRICS")
    logger.info(f"=" * 70)
    logger.info(f"  MAE (Mean Absolute Error): ${mae:.2f}")
    logger.info(f"  RMSE (Root Mean Squared Error): ${rmse:.2f}")
    logger.info(f"  MAPE (Mean Absolute Percentage Error): {mape:.2f}%")
    logger.info(f"  Total predictions: {len(predictions_list)}")
    
    # Per-symbol metrics
    logger.info(f"\n📈 PER-SYMBOL METRICS:")
    for symbol in pred_df['symbol'].unique():
        symbol_pred = pred_df[pred_df['symbol'] == symbol]
        symbol_mae = symbol_pred['error'].mean()
        symbol_mape = symbol_pred['error_pct'].mean()
        logger.info(f"  {symbol}: MAE=${symbol_mae:.2f}, MAPE={symbol_mape:.2f}% ({len(symbol_pred)} predictions)")
    
    # Show sample predictions
    logger.info(f"\n🎯 SAMPLE PREDICTIONS:")
    for _, row in pred_df.head(10).iterrows():
        logger.info(f"  {row['timestamp']} | {row['symbol']}: Predicted ${row['predicted']:.2f}, Actual ${row['actual']:.2f} (Error: {row['error_pct']:.2f}%)")
    
    # Save predictions to CSV for analysis
    pred_df.to_csv('validation_oct11_30.csv', index=False)
    logger.info(f"\n💾 Full predictions saved to validation_oct11_30.csv")
    
    logger.info(f"\n" + "=" * 70)
    logger.info(f"✅ VALIDATION COMPLETE")
    logger.info(f"=" * 70)

if __name__ == "__main__":
    validate_predictions()

