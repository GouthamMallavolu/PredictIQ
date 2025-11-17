"""
Batch Probe Simulation - Generate multiple probes quickly
Useful for testing and generating probe records
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

API_URL = os.getenv("API_URL", "http://localhost:8000")

def create_kafka_producer():
    """Create Kafka producer"""
    return KafkaProducer(
        bootstrap_servers=[KAFKA_BROKER],
        security_protocol='SASL_SSL',
        sasl_mechanism='PLAIN',
        sasl_plain_username=SASL_USERNAME,
        sasl_plain_password=SASL_PASSWORD,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )

def batch_probe(count=20, interval_seconds=5):
    """
    Run multiple probes quickly for testing
    
    Args:
        count: Number of probes to run
        interval_seconds: Delay between probes
    """
    print(f"🚀 Running {count} batch probes (interval: {interval_seconds}s)")
    print("=" * 60)
    
    producer = create_kafka_producer()
    successful = 0
    
    for i in range(count):
        probe_id = f"batch_probe_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        request_payload = {
            "user_id": probe_id,
            "symbols": ["AAPL", "MSFT", "NVDA"],
            "model": "lstm"
        }
        
        print(f"\n[{i+1}/{count}] Probe: {probe_id}")
        
        try:
            # Send request to Kafka
            producer.send(TOPIC_RECO_REQUESTS, request_payload)
            
            # Call API
            start_time = datetime.now()
            response = requests.post(
                f"{API_URL}/recommend",
                json=request_payload,
                timeout=10
            )
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            if response.status_code == 200:
                result = response.json()
                response_payload = {
                    "request_id": probe_id,
                    "response": result,
                    "latency_ms": latency_ms,
                    "timestamp": datetime.now().isoformat(),
                    "num_predictions": len(result.get("results", {})),
                    "status": "success"
                }
                producer.send(TOPIC_RECO_RESPONSES, response_payload)
                print(f"  ✅ Success (latency: {latency_ms:.2f}ms)")
                successful += 1
            else:
                print(f"  ⚠️  Error: {response.status_code}")
        
        except Exception as e:
            print(f"  ❌ Failed: {e}")
        
        if i < count - 1:
            time.sleep(interval_seconds)
    
    producer.flush()
    producer.close()
    
    print("\n" + "=" * 60)
    print(f"✅ Batch Complete: {successful}/{count} successful")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--count', type=int, default=20, help='Number of probes')
    parser.add_argument('--interval', type=int, default=5, help='Seconds between probes')
    args = parser.parse_args()
    
    batch_probe(count=args.count, interval_seconds=args.interval)

