"""
Quick Test Script - Verify everything works before submission
Run this to test all components in 5 minutes
"""
import subprocess
import sys
import os
import time

def run_cmd(cmd, description, timeout=60):
    """Run command and report status"""
    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"Command: {cmd}")
    print('='*60)
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        if result.returncode == 0:
            print(f"✅ SUCCESS")
            if result.stdout:
                print(result.stdout[:500])  # First 500 chars
            return True
        else:
            print(f"❌ FAILED (exit code: {result.returncode})")
            if result.stderr:
                print(result.stderr[:500])
            return False
    except subprocess.TimeoutExpired:
        print(f"⏱️ TIMEOUT after {timeout}s")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def main():
    print("""
    ╔═══════════════════════════════════════════════════════╗
    ║        STOCKRECOAI - QUICK TEST SUITE                ║
    ║     Run before final submission tomorrow             ║
    ╚═══════════════════════════════════════════════════════╝
    """)
    
    results = {}
    
    # Test 1: Check dependencies
    results['dependencies'] = run_cmd(
        'pip list | grep -E "(kafka|pandas|tensorflow|fastapi)"',
        "Check Python dependencies installed",
        timeout=10
    )
    
    # Test 2: Check model files exist
    results['model_files'] = run_cmd(
        'ls -lh multi_stock_model_LSTM.keras scaler.pkl',
        "Check model files exist",
        timeout=5
    )
    
    # Test 3: Test schema validation
    results['schemas'] = run_cmd(
        'python -c "from kafka_pipeline.schemas import StockWatchEvent; print(StockWatchEvent.schema())"',
        "Test Pydantic schemas",
        timeout=10
    )
    
    # Test 4: Test baseline model
    results['baseline'] = run_cmd(
        'python models/baseline_ma.py',
        "Test Moving Average baseline",
        timeout=10
    )
    
    # Test 5: Run model comparison (quick)
    results['comparison'] = run_cmd(
        'python scripts/compare_models.py',
        "Run model comparison",
        timeout=30
    )
    
    # Test 6: Check Docker
    results['docker'] = run_cmd(
        'docker --version',
        "Check Docker installed",
        timeout=5
    )
    
    # Test 7: Build Docker image (optional, takes time)
    build_docker = input("\nBuild Docker image? (takes 2-3 mins) [y/N]: ").lower() == 'y'
    if build_docker:
        results['docker_build'] = run_cmd(
            'docker build -t stockrecoai:test .',
            "Build Docker image",
            timeout=300
        )
    
    # Test 8: Check Kafka config
    results['kafka_config'] = run_cmd(
        'python -c "from kafka_pipeline.config import *; print(f\'Broker: {KAFKA_BROKER}\')"',
        "Check Kafka configuration",
        timeout=5
    )
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print('='*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test:20s}: {status}")
    
    print('='*60)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Ready for submission tomorrow!")
    elif passed >= total * 0.8:
        print("\n⚠️ Most tests passed. Fix failing tests before submission.")
    else:
        print("\n❌ Multiple tests failed. Review errors above.")
    
    print("\nNext steps:")
    print("1. Fix any failing tests")
    print("2. Test Kafka producer/consumer manually")
    print("3. Deploy Docker to Azure tomorrow")
    print("4. Create PDF report")

if __name__ == "__main__":
    main()

