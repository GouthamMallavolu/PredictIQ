"""Test Alpha Vantage API Credits"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('ALPHA_VANTAGE_KEY')
if not api_key:
    print("❌ ALPHA_VANTAGE_KEY not found in .env")
    exit(1)

print("=" * 60)
print("TESTING ALPHA VANTAGE API CREDITS")
print("=" * 60)
print(f"\nAPI Key: {api_key[:8]}...")

# Test with a simple query
url = f'https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=AAPL&interval=60min&month=2025-10&outputsize=compact&apikey={api_key}'

print(f"\n📡 Making test API call...")
try:
    r = requests.get(url, timeout=10)
    print(f"Status Code: {r.status_code}")
    
    data = r.json()
    print(f"\nResponse keys: {list(data.keys())}")
    
    # Check for API limit/credit message
    if 'Note' in data:
        print("\n" + "=" * 60)
        print("⚠️ API LIMIT / CREDIT ISSUE DETECTED!")
        print("=" * 60)
        print(f"\n{data['Note']}")
        print("\n💡 Solutions:")
        print("  - Wait 1 minute and try again (rate limit)")
        print("  - Upgrade API plan if daily limit exceeded")
        print("  - Use different API key")
    elif 'Error Message' in data:
        print("\n" + "=" * 60)
        print("❌ API ERROR")
        print("=" * 60)
        print(f"\n{data['Error Message']}")
    elif 'Time Series (60min)' in data:
        print("\n" + "=" * 60)
        print("✅ API IS WORKING - Credits Available!")
        print("=" * 60)
        time_series = data['Time Series (60min)']
        print(f"\n✅ Successfully fetched data")
        print(f"   Records: {len(time_series)}")
        print(f"   Sample timestamps: {list(time_series.keys())[:3]}")
    elif 'Meta Data' in data:
        print("\n" + "=" * 60)
        print("✅ API IS WORKING - Credits Available!")
        print("=" * 60)
        print(f"\n✅ API responded successfully")
        print(f"   Metadata: {data.get('Meta Data', {}).get('1. Information', 'N/A')}")
    else:
        print("\n" + "=" * 60)
        print("⚠️ UNEXPECTED RESPONSE")
        print("=" * 60)
        print(f"\nFull response: {data}")
        
except Exception as e:
    print(f"\n❌ Error making API call: {e}")

print("\n" + "=" * 60)

