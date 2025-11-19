"""
PHASE 2: Backfill Oct 11-30 Data & Run Predictions

This script:
1. Fetches data from Alpha Vantage for Oct 11-30, 2025
2. Runs predictions using the trained models
3. Compares predictions vs actual prices (validation)
4. Appends validated data to Azure Blob Storage

Usage:
    python scripts/phase2_backfill_oct11_30.py
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
from datetime import datetime, timedelta
import requests
import time

# Import feature engineering utilities
from feature_engineering import engineer_features, validate_features

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_alpha_vantage_data(symbol, start_date, end_date, api_key):
    """
    Fetch intraday data from Alpha Vantage for a date range
    """
    logger.info(f"  Fetching {symbol} data from {start_date} to {end_date}...")
    
    # Alpha Vantage requires month parameter
    month = start_date[:7]  # YYYY-MM
    
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={symbol}&interval=60min&month={month}&outputsize=full&apikey={api_key}"
    
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            time_series_key = next((k for k in data if "Time Series" in k), None)
            
            if time_series_key:
                ts_data = data[time_series_key]
                df = pd.DataFrame.from_dict(ts_data, orient='index').reset_index()
                df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df['symbol'] = symbol
                
                # Filter to date range
                start_dt = pd.to_datetime(start_date)
                end_dt = pd.to_datetime(end_date) + timedelta(days=1)
                df = df[(df['timestamp'] >= start_dt) & (df['timestamp'] < end_dt)]
                
                # Convert types
                df['open'] = df['open'].astype(float)
                df['high'] = df['high'].astype(float)
                df['low'] = df['low'].astype(float)
                df['close'] = df['close'].astype(float)
                df['volume'] = df['volume'].astype(int)
                
                logger.info(f"    ✅ Fetched {len(df)} records for {symbol}")
                return df
            else:
                logger.error(f"    ❌ No time series data in response for {symbol}")
                return pd.DataFrame()
        else:
            logger.error(f"    ❌ API request failed: {r.status_code}")
            return pd.DataFrame()
    except Exception as e:
        logger.error(f"    ❌ Error fetching {symbol}: {e}")
        return pd.DataFrame()

def fetch_news_sentiment(symbol, start_date, end_date, api_key):
    """
    Fetch news sentiment from Alpha Vantage
    """
    time_from = start_date.replace('-', '') + "T0000"
    time_to = end_date.replace('-', '') + "T2359"
    
    url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={symbol}&time_from={time_from}&time_to={time_to}&limit=1000&apikey={api_key}"
    
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if "feed" in data and data["feed"]:
                df = pd.DataFrame(data["feed"])
                df["symbol"] = symbol
                df["time_published"] = pd.to_datetime(df["time_published"], format="%Y%m%dT%H%M%S", errors='coerce')
                df["timestamp"] = df["time_published"].dt.floor('h')
                df["avg_sentiment"] = df["ticker_sentiment"].apply(
                    lambda x: float(x[0]["ticker_sentiment_score"]) if isinstance(x, list) and len(x) > 0 else 0
                )
                
                # Aggregate by hour
                news_agg = df.groupby(['symbol', 'timestamp']).agg(
                    sentiment_mean=('avg_sentiment', 'mean'),
                    news_count=('title', 'count')
                ).reset_index()
                
                return news_agg
        return pd.DataFrame(columns=['symbol', 'timestamp', 'sentiment_mean', 'news_count'])
    except Exception as e:
        logger.error(f"    ❌ Error fetching news for {symbol}: {e}")
        return pd.DataFrame(columns=['symbol', 'timestamp', 'sentiment_mean', 'news_count'])

def backfill_oct11_30():
    """
    Backfill Oct 11-30 data with predictions and validation
    """
    # Load config
    api_key = os.getenv('ALPHA_VANTAGE_KEY')
    symbols = os.getenv('SYMBOLS', 'AAPL,MSFT,NVDA,META,TSLA').split(',')
    storage_connection = os.getenv('STORAGE_CONNECTION')
    storage_container = os.getenv('STORAGE_CONTAINER', 'snapshots')
    
    if not api_key or not storage_connection:
        logger.error("ERROR: Missing ALPHA_VANTAGE_KEY or STORAGE_CONNECTION in .env")
        return
    
    logger.info("=" * 70)
    logger.info("PHASE 2: BACKFILL OCT 11-30 WITH PREDICTIONS")
    logger.info("=" * 70)
    
    # Date range
    start_date = "2025-10-11"
    end_date = "2025-10-30"
    
    logger.info(f"\n📅 Backfill period: {start_date} to {end_date}")
    logger.info(f"📊 Symbols: {symbols}")
    
    # Fetch data from Alpha Vantage
    logger.info(f"\n📥 Fetching data from Alpha Vantage...")
    
    all_stock_data = []
    all_news_data = []
    
    for symbol in symbols:
        # Fetch stock data
        stock_df = fetch_alpha_vantage_data(symbol, start_date, end_date, api_key)
        if not stock_df.empty:
            all_stock_data.append(stock_df)
        
        time.sleep(12)  # Alpha Vantage rate limit: 5 calls/min
        
        # Fetch news sentiment
        news_df = fetch_news_sentiment(symbol, start_date, end_date, api_key)
        if not news_df.empty:
            all_news_data.append(news_df)
        
        time.sleep(12)
    
    if not all_stock_data:
        logger.error("❌ No stock data fetched. Exiting.")
        return
    
    # Combine data
    logger.info(f"\n🔗 Merging stock and news data...")
    stock_df = pd.concat(all_stock_data, ignore_index=True)
    
    if all_news_data:
        news_df = pd.concat(all_news_data, ignore_index=True)
        merged_df = pd.merge(stock_df, news_df, on=['symbol', 'timestamp'], how='left')
    else:
        merged_df = stock_df.copy()
        merged_df['sentiment_mean'] = 0
        merged_df['news_count'] = 0
    
    merged_df['sentiment_mean'] = merged_df['sentiment_mean'].fillna(0)
    merged_df['news_count'] = merged_df['news_count'].fillna(0)
    
    logger.info(f"  ✅ Merged {len(merged_df)} records")
    
    # Engineer features (EMA, RSI, MACD, Bollinger Bands, ATR)
    logger.info(f"\n🔧 Engineering technical indicators...")
    try:
        merged_df = engineer_features(merged_df)
        
        # Validate features
        is_valid, missing = validate_features(merged_df)
        if is_valid:
            logger.info(f"  ✅ All features engineered successfully")
            logger.info(f"     Features: return, log_return, ema_10, ema_50, rsi, macd, bb_high, bb_low, atr")
        else:
            logger.error(f"  ❌ Missing features: {missing}")
            return
    except Exception as e:
        logger.error(f"  ❌ Feature engineering failed: {e}")
        return
    
    # Run predictions and validation
    logger.info(f"\n🤖 Running predictions and validation...")
    
    try:
        # Load predictor
        from api.predictor import ModelPredictor
        predictor = ModelPredictor()
        logger.info(f"  ✅ Models loaded (LSTM, RF, MA)")
        
        # Sort by timestamp for sequential prediction
        merged_df = merged_df.sort_values(['symbol', 'timestamp']).reset_index(drop=True)
        
        # For each symbol, make predictions
        predictions_list = []
        errors_list = []
        
        for symbol in symbols:
            symbol_df = merged_df[merged_df['symbol'] == symbol].copy()
            
            if len(symbol_df) < 10:
                logger.warning(f"  ⚠️ {symbol}: Not enough data ({len(symbol_df)} records)")
                continue
            
            logger.info(f"  🔮 {symbol}: Making predictions on {len(symbol_df)} records...")
            
            # Use sliding window: predict each hour using previous hours
            for i in range(10, len(symbol_df)):
                try:
                    # Get historical window (last 50 hours or available)
                    window_start = max(0, i - 50)
                    historical_data = symbol_df.iloc[window_start:i]
                    
                    # Make predictions with ALL 3 models
                    pred_lstm = predictor.predict_lstm(historical_data)
                    pred_rf = predictor.predict_random_forest(historical_data)
                    pred_ma = predictor.predict_moving_average(historical_data)
                    
                    # Ensemble prediction (average of 3 models)
                    pred_ensemble = (pred_lstm + pred_rf + pred_ma) / 3
                    
                    # Get actual price
                    actual_price = symbol_df.iloc[i]['close']
                    
                    # Calculate errors for each model
                    error_lstm = abs(pred_lstm - actual_price)
                    error_rf = abs(pred_rf - actual_price)
                    error_ma = abs(pred_ma - actual_price)
                    error_ensemble = abs(pred_ensemble - actual_price)
                    
                    error_pct_lstm = (error_lstm / actual_price * 100) if actual_price > 0 else 0
                    error_pct_rf = (error_rf / actual_price * 100) if actual_price > 0 else 0
                    error_pct_ma = (error_ma / actual_price * 100) if actual_price > 0 else 0
                    error_pct_ensemble = (error_ensemble / actual_price * 100) if actual_price > 0 else 0
                    
                    predictions_list.append({
                        'symbol': symbol,
                        'timestamp': symbol_df.iloc[i]['timestamp'],
                        'actual': actual_price,
                        'pred_lstm': pred_lstm,
                        'pred_rf': pred_rf,
                        'pred_ma': pred_ma,
                        'pred_ensemble': pred_ensemble,
                        'error_lstm': error_lstm,
                        'error_rf': error_rf,
                        'error_ma': error_ma,
                        'error_ensemble': error_ensemble,
                        'error_pct_lstm': error_pct_lstm,
                        'error_pct_rf': error_pct_rf,
                        'error_pct_ma': error_pct_ma,
                        'error_pct_ensemble': error_pct_ensemble
                    })
                    
                    errors_list.append(error_ensemble)  # Use ensemble for overall metrics
                    
                except Exception as e:
                    logger.error(f"    ❌ Prediction failed at index {i}: {e}")
                    continue
        
        # Calculate validation metrics
        if predictions_list:
            pred_df = pd.DataFrame(predictions_list)
            
            # Calculate metrics for each model
            mae_lstm = pred_df['error_lstm'].mean()
            mae_rf = pred_df['error_rf'].mean()
            mae_ma = pred_df['error_ma'].mean()
            mae_ensemble = pred_df['error_ensemble'].mean()
            
            mape_lstm = pred_df['error_pct_lstm'].mean()
            mape_rf = pred_df['error_pct_rf'].mean()
            mape_ma = pred_df['error_pct_ma'].mean()
            mape_ensemble = pred_df['error_pct_ensemble'].mean()
            
            logger.info(f"\n📊 VALIDATION METRICS (All Models):")
            logger.info(f"  Total predictions: {len(predictions_list)}")
            logger.info(f"\n  LSTM Model:")
            logger.info(f"    MAE: ${mae_lstm:.2f}, MAPE: {mape_lstm:.2f}%")
            logger.info(f"  Random Forest Model:")
            logger.info(f"    MAE: ${mae_rf:.2f}, MAPE: {mape_rf:.2f}%")
            logger.info(f"  Moving Average Model:")
            logger.info(f"    MAE: ${mae_ma:.2f}, MAPE: {mape_ma:.2f}%")
            logger.info(f"  🏆 Ensemble (Average):")
            logger.info(f"    MAE: ${mae_ensemble:.2f}, MAPE: {mape_ensemble:.2f}%")
            
            # Determine best model
            best_model = min([
                ('LSTM', mae_lstm),
                ('Random Forest', mae_rf),
                ('Moving Average', mae_ma),
                ('Ensemble', mae_ensemble)
            ], key=lambda x: x[1])
            logger.info(f"\n  ⭐ Best Model: {best_model[0]} (MAE: ${best_model[1]:.2f})")
            
            # Show sample predictions
            logger.info(f"\n📈 Sample Predictions (First 5):")
            for _, row in pred_df.head(5).iterrows():
                logger.info(f"  {row['timestamp']} | {row['symbol']}: Actual=${row['actual']:.2f}")
                logger.info(f"    LSTM=${row['pred_lstm']:.2f}, RF=${row['pred_rf']:.2f}, MA=${row['pred_ma']:.2f}, Ensemble=${row['pred_ensemble']:.2f}")
            
            # Save predictions to CSV for analysis (optional - can be disabled)
            csv_file = 'phase2_model_comparison.csv'
            pred_df.to_csv(csv_file, index=False)
            logger.info(f"\n💾 Detailed predictions saved to {csv_file} (for analysis)")
        else:
            logger.warning(f"  ⚠️ No predictions were made")
            
    except Exception as e:
        logger.error(f"  ❌ Prediction validation failed: {e}")
        logger.info(f"  Continuing with data upload...")
    
    # Upload to Azure Blob Storage
    logger.info(f"\n📤 Uploading to Azure Blob Storage...")
    blob_service = BlobServiceClient.from_connection_string(storage_connection)
    container_client = blob_service.get_container_client(storage_container)
    
    # Partition by date and hour
    merged_df['date'] = merged_df['timestamp'].dt.date
    merged_df['hour'] = merged_df['timestamp'].dt.hour
    
    grouped = merged_df.groupby(['date', 'hour'])
    uploaded_count = 0
    
    for (date, hour), group_df in grouped:
        try:
            data_df = group_df.drop(columns=['date', 'hour'])
            blob_path = f"v1/date={date}/hour={hour:02d}/backfill_oct.parquet"
            
            table = pa.Table.from_pandas(data_df)
            parquet_buffer = io.BytesIO()
            pq.write_table(table, parquet_buffer)
            parquet_buffer.seek(0)
            
            blob_client = container_client.get_blob_client(blob_path)
            blob_client.upload_blob(parquet_buffer, overwrite=True)
            
            uploaded_count += 1
        except Exception as e:
            logger.error(f"ERROR: Failed to upload {blob_path}: {e}")
    
    logger.info(f"  ✅ Uploaded {uploaded_count} partitions")
    
    logger.info("\n" + "=" * 70)
    logger.info("PHASE 2 COMPLETE - Ready for Phase 3 (Live Streaming)")
    logger.info("=" * 70)

if __name__ == "__main__":
    backfill_oct11_30()

