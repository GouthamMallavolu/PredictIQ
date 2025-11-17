"""
Test script for FinSightAI API
"""
import requests
import json
from datetime import datetime

API_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("=" * 60)
    print("Testing /health endpoint")
    print("=" * 60)
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_models():
    """Test models endpoint"""
    print("\n" + "=" * 60)
    print("Testing /models endpoint")
    print("=" * 60)
    try:
        response = requests.get(f"{API_URL}/models", timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_recommend():
    """Test recommend endpoint"""
    print("\n" + "=" * 60)
    print("Testing /recommend endpoint")
    print("=" * 60)
    
    request_payload = {
        "user_id": "test_user_123",
        "symbols": ["AAPL", "MSFT"],
        "model": "all"
    }
    
    print(f"Request: {json.dumps(request_payload, indent=2)}")
    
    try:
        response = requests.post(
            f"{API_URL}/recommend",
            json=request_payload,
            timeout=30
        )
        print(f"\nStatus: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\nResponse:")
            print(json.dumps(result, indent=2))
            
            # Show predictions summary
            print("\n" + "-" * 60)
            print("Predictions Summary:")
            print("-" * 60)
            results = result.get('results', {})
            for symbol, pred_data in results.items():
                if 'error' not in pred_data:
                    preds = pred_data.get('predictions', {})
                    current = pred_data.get('current_price', 0)
                    print(f"\n{symbol}:")
                    print(f"  Current Price: ${current:.2f}")
                    print(f"  Predictions:")
                    for model_name, predicted_price in preds.items():
                        change_pct = ((predicted_price - current) / current * 100) if current > 0 else 0
                        print(f"    {model_name}: ${predicted_price:.2f} ({change_pct:+.2f}%)")
                    print(f"  Target Timestamp: {pred_data.get('target_timestamp')}")
                else:
                    print(f"\n{symbol}: Error - {pred_data.get('error')}")
            
            return True
        else:
            print(f"Error Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n[START] Starting API Tests\n")
    
    health_ok = test_health()
    models_ok = test_models()
    recommend_ok = test_recommend()
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    print(f"Health Check: {'[PASS]' if health_ok else '[FAIL]'}")
    print(f"Models Endpoint: {'[PASS]' if models_ok else '[FAIL]'}")
    print(f"Recommend Endpoint: {'[PASS]' if recommend_ok else '[FAIL]'}")
    
    if all([health_ok, models_ok, recommend_ok]):
        print("\n[SUCCESS] All tests passed!")
    else:
        print("\n[WARNING] Some tests failed")

