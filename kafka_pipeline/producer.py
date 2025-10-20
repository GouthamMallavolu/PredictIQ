"""
Kafka Producer - Simulates real-time stock data streaming
Fetches EOD data from Alpha Vantage and streams hourly to Kafka

This is your DATA SIMULATION component - CRITICAL for project
"""
import json
import time
import logging
from datetime import datetime, timedelta
import pandas as pd
import requests
import rstr
from kafka import KafkaProducer
from kafka.errors import KafkaError
from pydantic import ValidationError

from config import *
from schemas import StockWatchEvent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StockDataProducer:
    def __init__(self):
        """Initialize Kafka producer with Event Hubs Kafka endpoint"""
        self.producer = KafkaProducer(
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
        logger.info(f"✅ Kafka producer connected to {KAFKA_BROKER}")
    
    def fetch_stock_data(self, date):
        """Fetch stock prices for given date from Alpha Vantage"""
        pattern = r'[A-Z0-9]{16}'
        api_key = rstr.xeger(pattern)
        
        stock_dfs = []
        for symbol in SYMBOLS:
            try:
                url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={symbol}&interval=60min&month={date[:7]}&outputsize=full&apikey={api_key}"
                r = requests.get(url, timeout=10)
                
                if r.status_code == 200:
                    data = r.json()
                    time_series_key = next((k for k in data if "Time Series" in k), None)
                    
                    if time_series_key:
                        ts_data = data[time_series_key]
                        df = pd.DataFrame.from_dict(ts_data, orient='index').reset_index()
                        df.columns = ['time', 'open', 'high', 'low', 'close', 'volume']
                        df['time'] = pd.to_datetime(df['time'])
                        df['symbol'] = symbol
                        df = df[df['time'].dt.date == pd.to_datetime(date).date()]
                        stock_dfs.append(df)
                        logger.info(f"✅ Fetched {len(df)} records for {symbol}")
                    time.sleep(0.5)  # Rate limit
            except Exception as e:
                logger.error(f"❌ Error fetching {symbol}: {e}")
        
        return pd.concat(stock_dfs) if stock_dfs else pd.DataFrame()
    
    def fetch_news_sentiment(self, date):
        """Fetch news sentiment for given date"""
        pattern = r'[A-Z0-9]{16}'
        api_key = rstr.xeger(pattern)
        
        time_from = date.replace('-', '') + "T0000"
        next_day = (pd.to_datetime(date) + timedelta(days=1)).strftime("%Y%m%d") + "T0000"
        
        news_dfs = []
        for symbol in SYMBOLS:
            try:
                url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={symbol}&time_from={time_from}&time_to={next_day}&limit=1000&apikey={api_key}"
                r = requests.get(url, timeout=10)
                
                if r.status_code == 200:
                    data = r.json()
                    if "feed" in data and data["feed"]:
                        df = pd.DataFrame(data["feed"])
                        df["symbol"] = symbol
                        df["time_published"] = pd.to_datetime(df["time_published"], format="%Y%m%dT%H%M%S", errors='coerce')
                        df["time"] = df["time_published"].dt.round('h')
                        df["avg_sentiment"] = df["ticker_sentiment"].apply(
                            lambda x: float(x[0]["ticker_sentiment_score"]) if isinstance(x, list) and len(x) > 0 else 0
                        )
                        news_dfs.append(df[["time", "symbol", "avg_sentiment", "title"]])
                    time.sleep(0.5)
            except Exception as e:
                logger.error(f"❌ Error fetching news for {symbol}: {e}")
        
        if news_dfs:
            news_df = pd.concat(news_dfs)
            return news_df.groupby(['symbol', 'time']).agg(
                sentiment_mean=('avg_sentiment', 'mean'),
                news_count=('title', 'count')
            ).reset_index()
        return pd.DataFrame(columns=['symbol', 'time', 'sentiment_mean', 'news_count'])
    
    def simulate_streaming(self, date=None, delay_seconds=10):
        """
        Main simulation function - fetches EOD data and streams hourly
        
        Sends to multiple Kafka topics:
        - team01.watch: Raw stock price + news data
        - team01.rate: Simulated trading signals
        
        Args:
            date: Date to fetch (default: yesterday)
            delay_seconds: Delay between timestamps (10 for testing, 3600 for real-time)
        """
        if date is None:
            date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        logger.info(f"📊 Starting simulation for {date}")
        logger.info(f"⏱️ Using {delay_seconds}s delay between timestamps")
        
        # Fetch data
        logger.info("📥 Fetching stock prices...")
        stock_df = self.fetch_stock_data(date)
        
        if stock_df.empty:
            logger.error("❌ No stock data fetched. Exiting.")
            return
        
        logger.info("📰 Fetching news sentiment...")
        news_agg = self.fetch_news_sentiment(date)
        
        # Merge
        merge_df = pd.merge(stock_df, news_agg, on=['symbol', 'time'], how='left')
        merge_df['sentiment_mean'] = merge_df['sentiment_mean'].fillna(0)
        merge_df['news_count'] = merge_df['news_count'].fillna(0)
        
        logger.info(f"✅ Prepared {len(merge_df)} records across {len(merge_df['time'].unique())} timestamps")
        
        # Stream to Kafka - TWO topics
        unique_times = sorted(merge_df['time'].unique())
        
        for t in unique_times:
            batch = merge_df[merge_df['time'] == t]
            logger.info(f"📤 Streaming {len(batch)} records for {t}")
            
            for _, row in batch.iterrows():
                try:
                    # 1. Send to team01.watch (market data stream)
                    watch_event = StockWatchEvent(
                        symbol=row['symbol'],
                        timestamp=str(row['time']),
                        open=float(row['open']),
                        high=float(row['high']),
                        low=float(row['low']),
                        close=float(row['close']),
                        volume=int(row['volume']),
                        sentiment_mean=float(row['sentiment_mean']),
                        news_count=int(row['news_count'])
                    )
                    
                    self.producer.send(
                        TOPIC_WATCH,
                        key=row['symbol'],
                        value=watch_event.dict()
                    )
                    
                    # 2. Calculate and send price change event -> team01.rate
                    # This shows hourly price movements and volatility
                    price_change = float(row['close']) - float(row['open'])
                    price_change_pct = (price_change / float(row['open'])) * 100 if float(row['open']) > 0 else 0
                    volatility = float(row['high']) - float(row['low'])
                    
                    rate_event = {
                        'symbol': row['symbol'],
                        'timestamp': str(row['time']),
                        'open': float(row['open']),
                        'close': float(row['close']),
                        'price_change': round(price_change, 2),
                        'price_change_pct': round(price_change_pct, 2),
                        'volatility': round(volatility, 2),
                        'volume': int(row['volume']),
                        'signal': 'bullish' if price_change > 0 else 'bearish'
                    }
                    self.producer.send(
                        TOPIC_RATE,
                        key=row['symbol'],
                        value=rate_event
                    )
                    
                except ValidationError as e:
                    logger.error(f"❌ Schema validation failed: {e}")
                except KafkaError as e:
                    logger.error(f"❌ Kafka send failed: {e}")
            
            logger.info(f"✅ Sent {len(batch)} events to {TOPIC_WATCH} and {TOPIC_RATE}")
            
            # Simulate time passing
            if delay_seconds > 0:
                logger.info(f"⏳ Waiting {delay_seconds}s before next timestamp...")
                time.sleep(delay_seconds)
        
        logger.info("🎉 Simulation complete!")
        self.producer.flush()
    
    def close(self):
        """Close producer connection"""
        self.producer.close()
        logger.info("👋 Producer closed")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Stream stock data to Kafka")
    parser.add_argument("--date", help="Date to fetch (YYYY-MM-DD)", default=None)
    parser.add_argument("--delay", type=int, help="Delay between timestamps (seconds)", default=10)
    args = parser.parse_args()
    
    producer = StockDataProducer()
    try:
        producer.simulate_streaming(date=args.date, delay_seconds=args.delay)
    finally:
        producer.close()

