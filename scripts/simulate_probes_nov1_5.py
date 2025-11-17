"""
Simulate Probe Records for Nov 1-5, 2024
Generates probe requests/responses to Kafka with historical timestamps
During stock market hours (9:30 AM - 4:00 PM ET) with 1-hour gaps
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import json
from datetime import datetime, timedelta
from kafka import KafkaProducer
from kafka_pipeline.config import *
import time

# API URL
API_URL = os.getenv("API_URL", "http://localhost:8000")

def create_kafka_producer():
    """Create Kafka producer for reco topics"""
    return KafkaProducer(
        bootstrap_servers=[KAFKA_BROKER],
        security_protocol='SASL_SSL',
        sasl_mechanism='PLAIN',
        sasl_plain_username=SASL_USERNAME,
        sasl_plain_password=SASL_PASSWORD,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )

def simulate_probe_for_datetime(target_datetime, producer):
    """
    Simulate a probe at a specific datetime
    Creates probe records with the target timestamp
    """
    # Format timestamp for probe ID
    probe_id = f"probe_{target_datetime.strftime('%Y%m%d_%H%M%S')}"
    
    # Create probe request
    request_payload = {
        "user_id": probe_id,
        "symbols": ["AAPL", "MSFT", "NVDA"],
        "model": "lstm",
        "timestamp": target_datetime.isoformat()
    }
    
    print(f"Simulating probe: {probe_id} at {target_datetime.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    try:
        # Log request to Kafka
        producer.send(TOPIC_RECO_REQUESTS, request_payload)
        print(f"  [OK] Request sent to {TOPIC_RECO_REQUESTS}")
        
        # Call API (use current API, but log with historical timestamp)
        start_time = datetime.now()
        try:
            response = requests.post(
                f"{API_URL}/recommend",
                json={
                    "user_id": probe_id,
                    "symbols": ["AAPL", "MSFT", "NVDA"],
                    "model": "lstm"
                },
                timeout=10
            )
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            if response.status_code == 200:
                result = response.json()
                
                # Log response to Kafka with historical timestamp
                response_payload = {
                    "request_id": probe_id,
                    "response": result,
                    "latency_ms": latency_ms,
                    "timestamp": target_datetime.isoformat(),  # Use historical timestamp
                    "num_predictions": len(result.get("results", {})),
                    "status": "success",
                    "simulated": True  # Flag to indicate this is simulated data
                }
                
                producer.send(TOPIC_RECO_RESPONSES, response_payload)
                print(f"  [OK] Response sent to {TOPIC_RECO_RESPONSES} (latency: {latency_ms:.2f}ms)")
                return True
            else:
                error_payload = {
                    "request_id": probe_id,
                    "error": response.text,
                    "status_code": response.status_code,
                    "timestamp": target_datetime.isoformat(),
                    "status": "error",
                    "simulated": True
                }
                producer.send(TOPIC_RECO_RESPONSES, error_payload)
                print(f"  [WARN] API error: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            error_payload = {
                "request_id": probe_id,
                "error": str(e),
                "timestamp": target_datetime.isoformat(),
                "status": "error",
                "simulated": True
            }
            producer.send(TOPIC_RECO_RESPONSES, error_payload)
            print(f"  [ERROR] Request failed: {e}")
            return False
            
    except Exception as e:
        print(f"  [ERROR] Error: {e}")
        return False

def get_market_hours_utc(date):
    """
    Get market hours in UTC for a given date
    Market hours: 9:30 AM - 4:00 PM ET
    For Nov 2024, EST is UTC-5, so:
    - 9:30 AM ET = 14:30 UTC
    - 4:00 PM ET = 21:00 UTC
    """
    # Start: 9:30 AM ET = 14:30 UTC
    # End: 4:00 PM ET = 21:00 UTC
    # Probes every hour: 14:30, 15:30, 16:30, 17:30, 18:30, 19:30, 20:30 UTC
    
    base_date = date.replace(hour=14, minute=30, second=0, microsecond=0)
    hours = []
    
    # Generate hourly probes from 14:30 to 20:30 UTC (7 probes)
    for hour_offset in range(7):
        probe_time = base_date + timedelta(hours=hour_offset)
        hours.append(probe_time)
    
    return hours

def is_trading_day(date):
    """Check if date is a trading day (Monday-Friday)"""
    # Nov 1-5, 2024: Nov 1 (Fri), Nov 2 (Sat), Nov 3 (Sun), Nov 4 (Mon), Nov 5 (Tue)
    return date.weekday() < 5  # 0-4 = Monday-Friday

def simulate_nov1_5_probes():
    """
    Simulate probes for Nov 1-5, 2024
    Only trading days (Nov 1, 4, 5)
    During market hours with 1-hour gaps
    """
    print("Starting Probe Simulation for Nov 1-5, 2024")
    print("=" * 60)
    
    producer = create_kafka_producer()
    
    # Define date range: Nov 1-5, 2024
    start_date = datetime(2024, 11, 1)
    end_date = datetime(2024, 11, 5)
    
    total_probes = 0
    successful_probes = 0
    
    current_date = start_date
    while current_date <= end_date:
        if is_trading_day(current_date):
            print(f"\n{current_date.strftime('%A, %B %d, %Y')} (Trading Day)")
            market_hours = get_market_hours_utc(current_date)
            
            for probe_time in market_hours:
                success = simulate_probe_for_datetime(probe_time, producer)
                total_probes += 1
                if success:
                    successful_probes += 1
                
                # Small delay between probes
                time.sleep(0.5)
        else:
            print(f"\n{current_date.strftime('%A, %B %d, %Y')} (Non-Trading Day - Skipped)")
        
        current_date += timedelta(days=1)
    
    # Flush producer
    producer.flush()
    producer.close()
    
    print("\n" + "=" * 60)
    print(f"Simulation Complete!")
    print(f"   Total probes: {total_probes}")
    print(f"   Successful: {successful_probes}")
    print(f"   Failed: {total_probes - successful_probes}")
    print(f"\nProbe records written to:")
    print(f"   - {TOPIC_RECO_REQUESTS}")
    print(f"   - {TOPIC_RECO_RESPONSES}")
    print(f"\nNote: Timestamps are set to Nov 1-5, 2024 for historical simulation")

if __name__ == "__main__":
    simulate_nov1_5_probes()

