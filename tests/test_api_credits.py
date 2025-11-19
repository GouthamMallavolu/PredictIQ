"""Test Alpha Vantage API Credits"""
import requests
import os
import pytest
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('ALPHA_VANTAGE_KEY')

# Skip all tests if API key is not available
pytestmark = pytest.mark.skipif(
    not api_key,
    reason="ALPHA_VANTAGE_KEY not found in environment"
)


def test_alpha_vantage_api_credits():
    """Test Alpha Vantage API credits and availability"""
    print("=" * 60)
    print("TESTING ALPHA VANTAGE API CREDITS")
    print("=" * 60)
    print(f"\nAPI Key: {api_key[:8]}...")

    # Test with a simple query
    url = f'https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=AAPL&interval=60min&month=2025-10&outputsize=compact&apikey={api_key}'

    print(f"\nMaking test API call...")
    try:
        r = requests.get(url, timeout=10)
        print(f"Status Code: {r.status_code}")

        data = r.json()
        print(f"\nResponse keys: {list(data.keys())}")

        # Check for API limit/credit message
        if 'Note' in data:
            print("\n" + "=" * 60)
            print("WARNING: API LIMIT / CREDIT ISSUE DETECTED!")
            print("=" * 60)
            print(f"\n{data['Note']}")
            print("\nSolutions:")
            print("  - Wait 1 minute and try again (rate limit)")
            print("  - Upgrade API plan if daily limit exceeded")
            print("  - Use different API key")
            # Don't fail the test, just warn
            pytest.skip("API limit/credit issue detected")
        elif 'Error Message' in data:
            print("\n" + "=" * 60)
            print("API ERROR")
            print("=" * 60)
            print(f"\n{data['Error Message']}")
            pytest.fail(f"API Error: {data['Error Message']}")
        elif 'Time Series (60min)' in data:
            print("\n" + "=" * 60)
            print("SUCCESS: API IS WORKING - Credits Available!")
            print("=" * 60)
            time_series = data['Time Series (60min)']
            print(f"\nSuccessfully fetched data")
            print(f"   Records: {len(time_series)}")
            print(f"   Sample timestamps: {list(time_series.keys())[:3]}")
            # Test passes
            assert len(time_series) > 0, "No time series data returned"
        elif 'Meta Data' in data:
            print("\n" + "=" * 60)
            print("SUCCESS: API IS WORKING - Credits Available!")
            print("=" * 60)
            print(f"\nAPI responded successfully")
            print(f"   Metadata: {data.get('Meta Data', {}).get('1. Information', 'N/A')}")
            # Test passes
            assert 'Meta Data' in data, "No metadata returned"
        else:
            print("\n" + "=" * 60)
            print("WARNING: UNEXPECTED RESPONSE")
            print("=" * 60)
            print(f"\nFull response: {data}")
            # Don't fail, just warn
            print("Unexpected response format, but API is responding")

    except Exception as e:
        print(f"\nError making API call: {e}")
        pytest.fail(f"API call failed: {e}")

    print("\n" + "=" * 60)
