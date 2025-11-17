"""
Test Probing Setup
Verifies that all components for probing are configured correctly
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import json
from datetime import datetime
from kafka import KafkaProducer, KafkaConsumer
from kafka_pipeline.config import *

def test_api_endpoint():
    """Test if API endpoint is accessible"""
    api_url = os.getenv("API_URL", "http://localhost:8000")
    print(f"\n[TEST] API Endpoint: {api_url}")
    
    try:
        # Test health endpoint
        response = requests.get(f"{api_url}/health", timeout=5)
        if response.status_code == 200:
            print(f"  [OK] API is accessible (status: {response.status_code})")
            return True
        else:
            print(f"  [WARN] API returned status: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"  [ERROR] Cannot reach API: {e}")
        return False

def test_kafka_connection():
    """Test Kafka connection"""
    print(f"\n[TEST] Kafka Connection: {KAFKA_BROKER}")
    
    try:
        producer = KafkaProducer(
            bootstrap_servers=[KAFKA_BROKER],
            security_protocol='SASL_SSL',
            sasl_mechanism='PLAIN',
            sasl_plain_username=SASL_USERNAME,
            sasl_plain_password=SASL_PASSWORD,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            request_timeout_ms=5000
        )
        
        # Test connection by getting metadata
        metadata = producer.list_topics(timeout=5)
        print(f"  [OK] Kafka connection successful")
        print(f"  [INFO] Found {len(metadata)} topics")
        producer.close()
        return True
    except Exception as e:
        print(f"  [ERROR] Kafka connection failed: {e}")
        return False

def test_kafka_topics():
    """Test if required Kafka topics exist"""
    print(f"\n[TEST] Kafka Topics")
    required_topics = [TOPIC_RECO_REQUESTS, TOPIC_RECO_RESPONSES]
    
    try:
        producer = KafkaProducer(
            bootstrap_servers=[KAFKA_BROKER],
            security_protocol='SASL_SSL',
            sasl_mechanism='PLAIN',
            sasl_plain_username=SASL_USERNAME,
            sasl_plain_password=SASL_PASSWORD,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            request_timeout_ms=5000
        )
        
        metadata = producer.list_topics(timeout=5)
        available_topics = list(metadata.topics.keys())
        
        all_exist = True
        for topic in required_topics:
            if topic in available_topics:
                print(f"  [OK] {topic} exists")
            else:
                print(f"  [ERROR] {topic} NOT FOUND")
                all_exist = False
        
        producer.close()
        return all_exist
    except Exception as e:
        print(f"  [ERROR] Cannot check topics: {e}")
        return False

def test_probe_script():
    """Test if probe script can send a test message"""
    print(f"\n[TEST] Probe Script Functionality")
    
    try:
        producer = KafkaProducer(
            bootstrap_servers=[KAFKA_BROKER],
            security_protocol='SASL_SSL',
            sasl_mechanism='PLAIN',
            sasl_plain_username=SASL_USERNAME,
            sasl_plain_password=SASL_PASSWORD,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        
        # Send test request
        test_request = {
            "user_id": f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "symbols": ["AAPL"],
            "model": "lstm"
        }
        
        producer.send(TOPIC_RECO_REQUESTS, test_request)
        producer.flush()
        print(f"  [OK] Test request sent to {TOPIC_RECO_REQUESTS}")
        
        # Send test response
        test_response = {
            "request_id": test_request["user_id"],
            "status": "test",
            "timestamp": datetime.now().isoformat()
        }
        
        producer.send(TOPIC_RECO_RESPONSES, test_response)
        producer.flush()
        print(f"  [OK] Test response sent to {TOPIC_RECO_RESPONSES}")
        
        producer.close()
        return True
    except Exception as e:
        print(f"  [ERROR] Probe script test failed: {e}")
        return False

def test_api_recommend_endpoint():
    """Test if /recommend endpoint works"""
    api_url = os.getenv("API_URL", "http://localhost:8000")
    print(f"\n[TEST] API /recommend Endpoint")
    
    try:
        request_payload = {
            "user_id": "test_user",
            "symbols": ["AAPL", "MSFT"],
            "model": "lstm"
        }
        
        response = requests.post(
            f"{api_url}/recommend",
            json=request_payload,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"  [OK] /recommend endpoint works")
            print(f"  [INFO] Response status: {result.get('status', 'N/A')}")
            print(f"  [INFO] Results: {len(result.get('results', {}))} symbols")
            return True
        else:
            print(f"  [WARN] /recommend returned status: {response.status_code}")
            print(f"  [INFO] Response: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"  [ERROR] /recommend endpoint test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("PROBING SETUP VERIFICATION")
    print("=" * 60)
    
    results = {}
    
    results['api_endpoint'] = test_api_endpoint()
    results['kafka_connection'] = test_kafka_connection()
    results['kafka_topics'] = test_kafka_topics()
    results['probe_script'] = test_probe_script()
    results['api_recommend'] = test_api_recommend_endpoint()
    
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "[OK]" if passed else "[FAIL]"
        print(f"{status} {test_name}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 60)
    if all_passed:
        print("[SUCCESS] All tests passed! Probing setup is ready.")
    else:
        print("[WARNING] Some tests failed. Please fix issues before running probes.")
    print("=" * 60)
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

