"""
Test script for local API testing
"""
import requests
import json
import time
import sys

API_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("=" * 60)
    print("Testing /health endpoint...")
    print("=" * 60)
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Status: {data.get('status')}")
            print(f"Models Loaded:")
            for model, loaded in data.get('models_loaded', {}).items():
                print(f"  {model}: {'OK' if loaded else 'FAIL'}")
            return True
        else:
            print(f"Error: {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        print("[ERROR] Cannot connect to API. Is the server running?")
        print("   Start with: uvicorn api.main:app --host 0.0.0.0 --port 8000")
        return False
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        return False

def test_root():
    """Test root endpoint"""
    print("\n" + "=" * 60)
    print("Testing / endpoint...")
    print("=" * 60)
    try:
        response = requests.get(f"{API_URL}/", timeout=5)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Message: {data.get('message')}")
            print(f"Version: {data.get('version')}")
            return True
        else:
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        return False

def test_models():
    """Test models endpoint"""
    print("\n" + "=" * 60)
    print("Testing /models endpoint...")
    print("=" * 60)
    try:
        response = requests.get(f"{API_URL}/models", timeout=5)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Available Models: {len(data.get('available_models', []))}")
            for model in data.get('available_models', []):
                print(f"  - {model.get('name')}: {model.get('description')}")
            return True
        else:
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        return False

def test_recommend():
    """Test recommend endpoint"""
    print("\n" + "=" * 60)
    print("Testing /recommend endpoint...")
    print("=" * 60)
    
    request_data = {
        "user_id": "test_user_123",
        "symbols": ["AAPL", "MSFT"],
        "model": "all"
    }
    
    print(f"Request: {json.dumps(request_data, indent=2)}")
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{API_URL}/recommend",
            json=request_data,
            timeout=30
        )
        latency_ms = (time.time() - start_time) * 1000
        
        print(f"\nStatus Code: {response.status_code}")
        print(f"Latency: {latency_ms:.2f}ms")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n[SUCCESS] Success!")
            print(f"Request ID: {data.get('request_id')}")
            print(f"Status: {data.get('status')}")
            print(f"Model Used: {data.get('model_used')}")
            print(f"\nPredictions:")
            
            results = data.get('results', {})
            for symbol, pred_data in results.items():
                if 'error' in pred_data:
                    print(f"  {symbol}: [ERROR] {pred_data.get('error')}")
                else:
                    predictions = pred_data.get('predictions', {})
                    current = pred_data.get('current_price', 0)
                    print(f"  {symbol}:")
                    print(f"    Current Price: ${current:.2f}")
                    for model_name, pred_price in predictions.items():
                        change_pct = ((pred_price - current) / current * 100) if current > 0 else 0
                        print(f"    {model_name}: ${pred_price:.2f} ({change_pct:+.2f}%)")
                    print(f"    Target Timestamp: {pred_data.get('target_timestamp')}")
            return True
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Starting API Tests...")
    print(f"API URL: {API_URL}\n")
    
    # Wait a bit for server to be ready
    print("Waiting for API to be ready...")
    for i in range(10):
        try:
            requests.get(f"{API_URL}/health", timeout=2)
            print("[OK] API is ready!")
            break
        except:
            if i < 9:
                time.sleep(1)
            else:
                print("[ERROR] API not responding. Please start the server first:")
                print("   uvicorn api.main:app --host 0.0.0.0 --port 8000")
                sys.exit(1)
    
    # Run tests
    results = []
    results.append(("Health", test_health()))
    results.append(("Root", test_root()))
    results.append(("Models", test_models()))
    results.append(("Recommend", test_recommend()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    for test_name, passed in results:
        status = "[PASSED]" if passed else "[FAILED]"
        print(f"{test_name}: {status}")
    
    all_passed = all(result[1] for result in results)
    if all_passed:
        print("\n[SUCCESS] All tests passed!")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed")
        sys.exit(1)

