"""
Test Alpha Vantage API key and data fetching
"""
import os
import sys
import requests
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_api_key():
    """Test if API key is valid"""
    api_key = os.getenv('ALPHA_VANTAGE_KEY')
    
    if not api_key:
        print("[ERROR] ALPHA_VANTAGE_KEY not found in environment")
        return False
    
    print(f"[OK] Found API key: {api_key[:8]}...{api_key[-4:]}")
    
    # Test with a simple request
    test_symbol = "AAPL"
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={test_symbol}&interval=60min&month=2025-10&outputsize=compact&apikey={api_key}"
    
    print(f"\nTesting API with symbol: {test_symbol}")
    print(f"URL: {url[:80]}...")
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Check for API errors
            if "Error Message" in data:
                print(f"[ERROR] API Error: {data['Error Message']}")
                return False
            
            if "Note" in data:
                print(f"[WARNING] API Note: {data['Note']}")
                return False
            
            if "Information" in data:
                print(f"[WARNING] API Information: {data['Information']}")
                return False
            
            # Check for time series data
            time_series_key = next((k for k in data.keys() if "Time Series" in k), None)
            if time_series_key:
                ts_data = data[time_series_key]
                print(f"[OK] API Key is valid!")
                print(f"[OK] Found {len(ts_data)} data points")
                
                # Show first few timestamps
                timestamps = list(ts_data.keys())[:5]
                print(f"\nSample timestamps:")
                for ts in timestamps:
                    print(f"  - {ts}")
                
                return True
            else:
                print(f"[WARNING] No time series data found. Response keys: {list(data.keys())}")
                print(f"Full response: {json.dumps(data, indent=2)[:500]}")
                return False
                
        else:
            print(f"[ERROR] HTTP Error: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_stock_data_fetch(date="2025-10-30"):
    """Test fetching stock data for a specific date"""
    api_key = os.getenv('ALPHA_VANTAGE_KEY')
    symbols = ['AAPL', 'MSFT', 'NVDA']
    
    print(f"\n{'='*60}")
    print(f"Testing stock data fetch for date: {date}")
    print(f"{'='*60}\n")
    
    for symbol in symbols:
        print(f"Testing {symbol}...")
        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={symbol}&interval=60min&month={date[:7]}&outputsize=full&apikey={api_key}"
        
        try:
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if "Error Message" in data:
                    print(f"  [ERROR] Error: {data['Error Message']}")
                    continue
                
                if "Note" in data:
                    print(f"  [WARNING] Note: {data['Note']}")
                    continue
                
                time_series_key = next((k for k in data.keys() if "Time Series" in k), None)
                if time_series_key:
                    ts_data = data[time_series_key]
                    df_data = []
                    for timestamp, values in ts_data.items():
                        ts_date = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                        if ts_date.date() == datetime.strptime(date, "%Y-%m-%d").date():
                            df_data.append(timestamp)
                    
                    print(f"  [OK] Found {len(df_data)} records for {date}")
                    if len(df_data) > 0:
                        print(f"    Sample: {df_data[0]}")
                else:
                    print(f"  [WARNING] No time series data found")
                    print(f"    Response keys: {list(data.keys())}")
            
            else:
                print(f"  [ERROR] HTTP {response.status_code}")
            
            # Rate limiting
            import time
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  [ERROR] Exception: {e}")

def test_news_sentiment(date="2025-10-30"):
    """Test fetching news sentiment"""
    api_key = os.getenv('ALPHA_VANTAGE_KEY')
    symbol = "AAPL"
    
    print(f"\n{'='*60}")
    print(f"Testing news sentiment fetch for date: {date}")
    print(f"{'='*60}\n")
    
    time_from = date.replace('-', '') + "T0000"
    next_day = (datetime.strptime(date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y%m%d") + "T0000"
    
    url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={symbol}&time_from={time_from}&time_to={next_day}&limit=10&apikey={api_key}"
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if "Error Message" in data:
                print(f"[ERROR] Error: {data['Error Message']}")
                return False
            
            if "Note" in data:
                print(f"[WARNING] Note: {data['Note']}")
                return False
            
            if "feed" in data:
                print(f"[OK] Found {len(data['feed'])} news articles")
                if len(data['feed']) > 0:
                    print(f"  Sample: {data['feed'][0].get('title', 'N/A')[:60]}...")
                return True
            else:
                print(f"[WARNING] No feed data found. Keys: {list(data.keys())}")
                return False
        else:
            print(f"[ERROR] HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Exception: {e}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("ALPHA VANTAGE API KEY TEST")
    print("="*60)
    
    # Test 1: Verify API key
    api_valid = test_api_key()
    
    if api_valid:
        # Test 2: Fetch stock data
        test_stock_data_fetch("2025-10-30")
        
        # Test 3: Fetch news sentiment
        test_news_sentiment("2025-10-30")
    else:
        print("\n[WARNING] API key test failed. Please check your API key.")
        print("   Free tier API keys have rate limits (5 calls/minute, 500 calls/day)")
        print("   Premium API keys are required for higher limits.")

