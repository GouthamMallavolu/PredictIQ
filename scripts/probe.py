"""
Probing Script for StockRecoAI API
Periodically tests the API and writes requests/responses to Kafka

This is Task 5: Probing pipeline
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import json
from datetime import datetime
from kafka import KafkaProducer
from kafka_pipeline.config import *

# API URL (update after deployment)
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

def probe_api():
    """Send probe request to API and log to Kafka"""
    producer = create_kafka_producer()
    
    # Create probe request
    request_payload = {
        "user_id": f"probe_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "symbols": ["AAPL", "MSFT", "NVDA"],
        "top_k": 5,
        "model": "lstm"
    }
    
    print(f"Sending probe request: {request_payload['user_id']}")
    
    try:
        # Log request to Kafka
        producer.send(TOPIC_PREDICT_REQUESTS, request_payload)
        
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
            
            # Log response to Kafka
            response_payload = {
                "request_id": request_payload["user_id"],
                "response": result,
                "latency_ms": latency_ms,
                "timestamp": datetime.now().isoformat(),
                "num_predictions": len(result.get("predictions", [])),
                "status": "success"
            }
            
            producer.send(TOPIC_PREDICT_RESPONSES, response_payload)
            
            print(f"Probe successful:")
            print(f"   Latency: {latency_ms:.2f}ms")
            print(f"   Predictions: {len(result.get('predictions', []))}")
            print(f"   Model used: {result.get('model_used')}")
            
            # Show predicted prices
            for pred in result.get('predictions', [])[:3]:
                print(f"   {pred['symbol']}: ${pred['current_price']:.2f} -> ${pred['predicted_price']:.2f} ({pred['predicted_change_pct']:+.2f}%)")
            
            return response_payload
        else:
            print(f"API error: {response.status_code}")
            error_payload = {
                "request_id": request_payload["user_id"],
                "error": response.text,
                "status_code": response.status_code,
                "timestamp": datetime.now().isoformat(),
                "status": "error"
            }
            producer.send(TOPIC_PREDICT_RESPONSES, error_payload)
            return error_payload
            
    except Exception as e:
        print(f"Probe failed: {e}")
        error_payload = {
            "request_id": request_payload["user_id"],
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "status": "error"
        }
        producer.send(TOPIC_PREDICT_RESPONSES, error_payload)
        return error_payload
    finally:
        producer.flush()
        producer.close()

if __name__ == "__main__":
    probe_api()

