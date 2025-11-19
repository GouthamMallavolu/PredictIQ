"""
Generate Mock Probe Data for Nov 1-7, 2024
Creates probe records without calling the real API (to avoid rate limits)
Writes directly to Kafka for online evaluation
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from datetime import datetime, timedelta
from kafka import KafkaProducer
from kafka_pipeline.config import *
import numpy as np
import time

def create_kafka_producer():
    """Create Kafka producer for reco topics"""
    print("[INFO] Creating Kafka producer...")
    try:
        producer = KafkaProducer(
            bootstrap_servers=[KAFKA_BROKER],
            security_protocol='SASL_SSL',
            sasl_mechanism='PLAIN',
            sasl_plain_username=SASL_USERNAME,
            sasl_plain_password=SASL_PASSWORD,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            api_version=(0, 10, 1),
            request_timeout_ms=60000,
            max_block_ms=60000
        )
        print("[OK] Kafka producer created")
        return producer
    except Exception as e:
        print(f"[ERROR] Failed to create Kafka producer: {e}")
        raise

def generate_mock_predictions(symbols, base_prices=None):
    """
    Generate mock prediction results
    
    Args:
        symbols: List of stock symbols
        base_prices: Dict of base prices (optional)
    
    Returns:
        Mock results dictionary
    """
    if base_prices is None:
        # Default base prices for common symbols
        base_prices = {
            'AAPL': 180.0,
            'MSFT': 420.0,
            'NVDA': 480.0,
            'META': 520.0,
            'TSLA': 240.0,
            'AMZN': 180.0
        }
    
    results = {}
    for symbol in symbols:
        current_price = base_prices.get(symbol, 100.0)
        
        # Add some random variation
        current_price += np.random.uniform(-5, 5)
        
        # Generate predictions with realistic variation
        lstm_pred = current_price * (1 + np.random.uniform(-0.02, 0.03))
        rf_pred = current_price * (1 + np.random.uniform(-0.025, 0.025))
        ma_pred = current_price * (1 + np.random.uniform(-0.015, 0.02))
        
        results[symbol] = {
            "current_price": round(current_price, 2),
            "predictions": {
                "LSTM": round(lstm_pred, 2),
                "RandomForest": round(rf_pred, 2),
                "MovingAverage": round(ma_pred, 2)
            }
        }
    
    return results

def create_mock_probe(target_datetime, producer, symbols=['AAPL', 'MSFT', 'NVDA']):
    """
    Create a mock probe record at a specific datetime
    
    Args:
        target_datetime: Target timestamp for the probe
        producer: Kafka producer
        symbols: List of symbols to probe
    
    Returns:
        Success status
    """
    probe_id = f"probe_{target_datetime.strftime('%Y%m%d_%H%M%S')}"
    
    # Create request payload
    request_payload = {
        "user_id": probe_id,
        "symbols": symbols,
        "model": "lstm",
        "timestamp": target_datetime.isoformat()
    }
    
    print(f"Creating mock probe: {probe_id} at {target_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Send request to Kafka
        producer.send(TOPIC_RECO_REQUESTS, request_payload)
        
        # Generate mock response
        mock_results = generate_mock_predictions(symbols)
        
        # Simulate realistic latency
        latency_ms = np.random.uniform(50, 200)
        
        response_payload = {
            "request_id": probe_id,
            "response": {
                "request_id": probe_id,
                "timestamp": target_datetime.isoformat(),
                "status": "success",
                "results": mock_results,
                "model_used": "lstm"
            },
            "latency_ms": latency_ms,
            "timestamp": target_datetime.isoformat(),
            "num_predictions": len(mock_results),
            "status": "success"
        }
        
        # Send response to Kafka
        producer.send(TOPIC_RECO_RESPONSES, response_payload)
        
        print(f"  [OK] Mock probe created (latency: {latency_ms:.2f}ms)")
        return True
        
    except Exception as e:
        print(f"  [ERROR] Failed to create mock probe: {e}")
        return False

def get_market_hours_utc(date):
    """
    Get market hours in UTC for a given date
    9:30 AM ET = 14:30 UTC (market open)
    4:00 PM ET = 21:00 UTC (market close)
    Returns 2 probes: market open and close
    """
    hours = []
    # Market open
    hours.append(date.replace(hour=14, minute=30, second=0, microsecond=0))
    # Market close
    hours.append(date.replace(hour=21, minute=0, second=0, microsecond=0))
    return hours

def is_trading_day(date):
    """Check if date is a trading day (Monday-Friday)"""
    return date.weekday() < 5  # 0-4 = Monday-Friday

def generate_mock_probe_data():
    """
    Generate mock probe data for Nov 1-7, 2024
    Only trading days with 2 probes per day
    """
    print("=" * 60)
    print("Mock Probe Data Generator for Nov 1-7, 2024")
    print("=" * 60)
    print("\nNote: This generates mock data WITHOUT calling the real API")
    print("to avoid rate limits and API timeouts.\n")
    
    producer = create_kafka_producer()
    
    # Date range: Nov 1-7, 2024
    start_date = datetime(2024, 11, 1)
    end_date = datetime(2024, 11, 7)
    
    total_probes = 0
    successful_probes = 0
    
    current_date = start_date
    while current_date <= end_date:
        if is_trading_day(current_date):
            print(f"\n{current_date.strftime('%A, %B %d, %Y')} (Trading Day)")
            market_hours = get_market_hours_utc(current_date)
            
            for probe_time in market_hours:
                success = create_mock_probe(probe_time, producer)
                total_probes += 1
                if success:
                    successful_probes += 1
                
                # Small delay
                time.sleep(0.1)
        else:
            print(f"\n{current_date.strftime('%A, %B %d, %Y')} (Non-Trading Day - Skipped)")
        
        current_date += timedelta(days=1)
    
    # Flush producer
    try:
        print("\n[INFO] Flushing Kafka producer...")
        producer.flush(timeout=30)
        print("[OK] All messages flushed")
        
        producer.close(timeout=10)
        print("[OK] Kafka producer closed")
    except Exception as e:
        print(f"[WARN] Error during flush/close: {e}")
    
    print("\n" + "=" * 60)
    print("Mock Data Generation Complete!")
    print("=" * 60)
    print(f"  Total probes: {total_probes}")
    print(f"  Successful: {successful_probes}")
    print(f"  Failed: {total_probes - successful_probes}")
    print(f"\nMock probe records written to:")
    print(f"  - {TOPIC_RECO_REQUESTS}")
    print(f"  - {TOPIC_RECO_RESPONSES}")
    print(f"\nYou can now run online evaluation:")
    print(f"  python evaluation/online/evaluate_online.py")

if __name__ == "__main__":
    try:
        generate_mock_probe_data()
    except KeyboardInterrupt:
        print("\n\n[INFO] Interrupted by user")
    except Exception as e:
        print(f"\n[ERROR] Script failed: {e}")
        import traceback
        traceback.print_exc()
