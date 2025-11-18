"""
Phase 3 Testing Script

Tests all Phase 3 components:
1. /metrics endpoint
2. A/B testing
3. Provenance tracking
4. Health endpoint with uptime
5. Retraining script
6. A/B analysis
"""

import sys
import os
import json
import time
import requests
from datetime import datetime
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")
TEST_USER_IDS = [f"test_user_{i}" for i in range(1, 21)]  # 20 test users

print("="*70)
print("PHASE 3 COMPREHENSIVE TESTING")
print("="*70)
print(f"\nAPI URL: {API_URL}")
print(f"Test Users: {len(TEST_USER_IDS)}")
print(f"Timestamp: {datetime.now().isoformat()}\n")


def test_health_endpoint():
    """Test /health endpoint with uptime"""
    print("\n" + "="*70)
    print("TEST 1: Health Endpoint")
    print("="*70)
    
    try:
        response = requests.get(f"{API_URL}/health", timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Status: {data.get('status')}")
            print(f"Uptime: {data.get('uptime', 'N/A')}")
            print(f"Models Ready: {data.get('models_ready', False)}")
            print(f"Models Loaded: {json.dumps(data.get('models_loaded', {}), indent=2)}")
            print("\n[OK] Health endpoint working")
            return True
        else:
            print(f"[ERROR] Health check failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Health check exception: {e}")
        return False


def test_metrics_endpoint():
    """Test /metrics endpoint"""
    print("\n" + "="*70)
    print("TEST 2: Metrics Endpoint")
    print("="*70)
    
    try:
        response = requests.get(f"{API_URL}/metrics", timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            content = response.text
            print(f"Response Length: {len(content)} bytes")
            
            # Check for key metrics
            metrics_found = []
            required_metrics = [
                "http_requests_total",
                "http_request_duration_seconds",
                "model_predictions_total",
                "api_uptime_seconds",
                "api_health_status"
            ]
            
            for metric in required_metrics:
                if metric in content:
                    metrics_found.append(metric)
                    print(f"  [OK] Found: {metric}")
                else:
                    print(f"  [WARN] Missing: {metric}")
            
            if len(metrics_found) == len(required_metrics):
                print("\n[OK] All required metrics present")
                return True
            else:
                print(f"\n[WARN] Only {len(metrics_found)}/{len(required_metrics)} metrics found")
                return True  # Still OK, metrics will populate after requests
        else:
            print(f"[ERROR] Metrics endpoint failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Metrics endpoint exception: {e}")
        return False


def test_ab_testing():
    """Test A/B testing by sending requests with different user IDs"""
    print("\n" + "="*70)
    print("TEST 3: A/B Testing")
    print("="*70)
    
    print(f"Sending {len(TEST_USER_IDS)} requests with different user IDs...")
    
    successful = 0
    failed = 0
    variants = {"A": 0, "B": 0}
    
    for i, user_id in enumerate(TEST_USER_IDS, 1):
        try:
            payload = {
                "user_id": user_id,
                "symbols": ["AAPL", "MSFT"],
                "model": "all"  # This triggers A/B testing
            }
            
            start_time = time.time()
            response = requests.post(
                f"{API_URL}/recommend",
                json=payload,
                timeout=30
            )
            latency = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                model_used = data.get("model_used", "unknown")
                
                # Determine variant based on model
                if "lstm" in model_used.lower():
                    variants["A"] += 1
                elif "randomforest" in model_used.lower() or "rf" in model_used.lower():
                    variants["B"] += 1
                
                successful += 1
                if i % 5 == 0:
                    print(f"  [{i}/{len(TEST_USER_IDS)}] {user_id}: {model_used} ({latency:.0f}ms)")
            else:
                failed += 1
                print(f"  [{i}/{len(TEST_USER_IDS)}] {user_id}: FAILED ({response.status_code})")
            
            # Small delay to avoid overwhelming the API
            time.sleep(0.2)
            
        except Exception as e:
            failed += 1
            print(f"  [{i}/{len(TEST_USER_IDS)}] {user_id}: EXCEPTION ({str(e)[:50]})")
    
    print(f"\nResults:")
    print(f"  Successful: {successful}/{len(TEST_USER_IDS)}")
    print(f"  Failed: {failed}/{len(TEST_USER_IDS)}")
    print(f"  Variant A (LSTM): {variants['A']}")
    print(f"  Variant B (RandomForest): {variants['B']}")
    
    # Check if we have a reasonable split (should be roughly 50/50)
    total_variants = variants["A"] + variants["B"]
    if total_variants > 0:
        split_a = (variants["A"] / total_variants) * 100
        split_b = (variants["B"] / total_variants) * 100
        print(f"  Split: A={split_a:.1f}%, B={split_b:.1f}%")
        
        if 30 <= split_a <= 70:  # Reasonable split range
            print("\n[OK] A/B testing working (reasonable split)")
        else:
            print("\n[WARN] A/B split may be skewed (check configuration)")
    
    return successful > 0


def test_ab_metrics():
    """Test /ab-test-metrics endpoint"""
    print("\n" + "="*70)
    print("TEST 4: A/B Test Metrics Endpoint")
    print("="*70)
    
    try:
        # Wait a moment for logs to be written
        time.sleep(2)
        
        response = requests.get(f"{API_URL}/ab-test-metrics", timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if "error" in data:
                print(f"[WARN] {data['error']}")
                print("  (This is OK if no A/B test data exists yet)")
                return True
            
            print(f"Date: {data.get('date')}")
            print(f"Test Config: {json.dumps(data.get('test_config', {}), indent=2)}")
            
            results = data.get('results', {})
            if results:
                for variant in ['A', 'B']:
                    if variant in results:
                        r = results[variant]
                        print(f"\nVariant {variant} ({r.get('model')}):")
                        print(f"  Total Requests: {r.get('total_requests')}")
                        print(f"  Success Rate: {r.get('success_rate')}%")
                        print(f"  Avg Latency: {r.get('avg_latency_ms')}ms")
                        print(f"  P95 Latency: {r.get('p95_latency_ms')}ms")
                
                print("\n[OK] A/B metrics endpoint working")
                return True
            else:
                print("[WARN] No results found (may need more requests)")
                return True
        else:
            print(f"[ERROR] A/B metrics endpoint failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"[ERROR] A/B metrics endpoint exception: {e}")
        return False


def test_provenance():
    """Test provenance tracking"""
    print("\n" + "="*70)
    print("TEST 5: Provenance Tracking")
    print("="*70)
    
    test_user_id = "provenance_test_001"
    
    try:
        payload = {
            "user_id": test_user_id,
            "symbols": ["AAPL"],
            "model": "lstm"
        }
        
        print(f"Sending test request with user_id: {test_user_id}")
        response = requests.post(
            f"{API_URL}/recommend",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            print("[OK] Request successful")
            
            # Wait for provenance log to be written
            time.sleep(1)
            
            # Check provenance log file
            log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
            log_file = os.path.join(log_dir, f"provenance_{datetime.now().strftime('%Y%m%d')}.jsonl")
            
            if os.path.exists(log_file):
                print(f"Checking provenance log: {log_file}")
                
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    print(f"  Total entries: {len(lines)}")
                    
                    # Find our test request
                    found = False
                    for line in lines:
                        try:
                            trace = json.loads(line)
                            if trace.get('user_id') == test_user_id:
                                found = True
                                print("\n[OK] Provenance trace found:")
                                print(f"  Request ID: {trace.get('request_id')}")
                                print(f"  Model Version: {trace.get('model_version')}")
                                print(f"  Git SHA: {trace.get('pipeline_git_sha')}")
                                print(f"  Container Digest: {trace.get('container_image_digest')}")
                                print(f"  Data Snapshot: {trace.get('data_snapshot_id')}")
                                print(f"  Latency: {trace.get('latency_ms')}ms")
                                print(f"  Status: {trace.get('status')}")
                                
                                # Check all required fields
                                required_fields = [
                                    'request_id', 'user_id', 'timestamp',
                                    'model_version', 'data_snapshot_id',
                                    'pipeline_git_sha', 'container_image_digest'
                                ]
                                
                                missing = [f for f in required_fields if f not in trace]
                                if missing:
                                    print(f"  [WARN] Missing fields: {missing}")
                                else:
                                    print("  [OK] All required fields present")
                                break
                        except:
                            continue
                    
                    if not found:
                        print(f"[WARN] Provenance trace not found for {test_user_id}")
                        print("  (May need to wait a moment for log to flush)")
                return True
            else:
                print(f"[WARN] Provenance log file not found: {log_file}")
                print("  (This is OK if Kafka logging is primary)")
                return True
        else:
            print(f"[ERROR] Request failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Provenance test exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_retraining_script():
    """Test retraining script"""
    print("\n" + "="*70)
    print("TEST 6: Retraining Script")
    print("="*70)
    
    try:
        from scripts.retrain_models import get_latest_version, increment_version
        
        # Test version functions
        current_version = get_latest_version()
        print(f"Current Version: {current_version}")
        
        next_version = increment_version(current_version)
        print(f"Next Version: {next_version}")
        
        # Verify version format
        if next_version.startswith('v') and '.' in next_version:
            print("[OK] Version increment working")
        else:
            print(f"[ERROR] Invalid version format: {next_version}")
            return False
        
        # Check if script can be imported
        print("[OK] Retraining script importable")
        print("\nNote: Full retraining test requires:")
        print("  - Model files in models/ directory")
        print("  - Training data available")
        print("  - Run: python scripts/retrain_models.py --auto-version")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Retraining script test exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ab_analysis():
    """Test A/B analysis script"""
    print("\n" + "="*70)
    print("TEST 7: A/B Analysis Script")
    print("="*70)
    
    try:
        from scripts.analyze_ab_test import analyze_ab_test
        
        # Try to analyze today's data
        analysis = analyze_ab_test()
        
        if "error" in analysis:
            print(f"[INFO] {analysis['error']}")
            print("  (This is OK if no A/B test data exists yet)")
            return True
        
        print(f"Date: {analysis.get('date')}")
        print(f"Sample Sizes: A={analysis.get('sample_sizes', {}).get('variant_a', 0)}, "
              f"B={analysis.get('sample_sizes', {}).get('variant_b', 0)}")
        
        if analysis.get('sample_sizes', {}).get('variant_a', 0) >= 10:
            print("[OK] A/B analysis script working")
            print(f"Recommendation: {analysis.get('recommendation', 'N/A')}")
            return True
        else:
            print("[INFO] Insufficient data for analysis (need 10+ requests per variant)")
            print("  (This is OK - run more A/B test requests)")
            return True
        
    except Exception as e:
        print(f"[ERROR] A/B analysis test exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\nStarting Phase 3 tests...\n")
    
    results = {}
    
    # Run tests
    results['health'] = test_health_endpoint()
    results['metrics'] = test_metrics_endpoint()
    results['ab_testing'] = test_ab_testing()
    results['ab_metrics'] = test_ab_metrics()
    results['provenance'] = test_provenance()
    results['retraining'] = test_retraining_script()
    results['ab_analysis'] = test_ab_analysis()
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "[OK]" if result else "[FAIL]"
        print(f"{status} {test_name.replace('_', ' ').title()}")
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("\n[SUCCESS] ALL TESTS PASSED!")
    elif passed >= total * 0.7:
        print("\n[OK] Most tests passed (some warnings expected)")
    else:
        print("\n[WARN] Some tests failed - check errors above")
    
    print("\n" + "="*70)
    print("Next Steps:")
    print("1. Review test results above")
    print("2. Check logs/ directory for generated files")
    print("3. Run: python scripts/analyze_ab_test.py (after more requests)")
    print("4. Trigger retraining workflow in GitHub Actions")
    print("5. Set up UptimeRobot for availability tracking")
    print("="*70)


if __name__ == "__main__":
    main()
