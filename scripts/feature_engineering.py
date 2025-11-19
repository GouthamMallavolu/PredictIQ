"""
Feature Engineering Utilities

Calculates technical indicators for stock price prediction:
- EMA (Exponential Moving Average)
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- Bollinger Bands
- ATR (Average True Range)
"""
import pandas as pd
import numpy as np

def calculate_ema(df, column='close', span=10):
    """Calculate Exponential Moving Average"""
    return df[column].ewm(span=span, adjust=False).mean()

def calculate_rsi(df, column='close', period=14):
    """Calculate Relative Strength Index"""
    delta = df[column].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(df, column='close', fast=12, slow=26, signal=9):
    """Calculate MACD (Moving Average Convergence Divergence)"""
    ema_fast = df[column].ewm(span=fast, adjust=False).mean()
    ema_slow = df[column].ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    return macd

def calculate_bollinger_bands(df, column='close', period=20, std_dev=2):
    """Calculate Bollinger Bands"""
    sma = df[column].rolling(window=period).mean()
    std = df[column].rolling(window=period).std()
    
    bb_high = sma + (std * std_dev)
    bb_low = sma - (std * std_dev)
    
    return bb_high, bb_low

def calculate_atr(df, period=14):
    """Calculate Average True Range"""
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = true_range.rolling(window=period).mean()
    
    return atr

def engineer_features(df):
    """
    Add all technical indicators to the dataframe
    
    Args:
        df: DataFrame with columns: open, high, low, close, volume
        
    Returns:
        DataFrame with added features: return, log_return, ema_10, ema_50, 
        rsi, macd, bb_high, bb_low, atr
    """
    # Make a copy to avoid modifying original
    df = df.copy()
    
    # Sort by time for each symbol
    if 'symbol' in df.columns:
        df = df.sort_values(['symbol', 'timestamp'])
    else:
        df = df.sort_values('timestamp')
    
    # Calculate returns
    if 'symbol' in df.columns:
        # Group by symbol for proper calculation
        df['return'] = df.groupby('symbol')['close'].pct_change().values
        df['log_return'] = df.groupby('symbol')['close'].transform(lambda x: np.log(x / x.shift(1))).values
    else:
        df['return'] = df['close'].pct_change()
        df['log_return'] = np.log(df['close'] / df['close'].shift(1))
    
    # Calculate technical indicators per symbol
    if 'symbol' in df.columns:
        for symbol in df['symbol'].unique():
            mask = df['symbol'] == symbol
            symbol_df = df[mask].copy()
            
            # EMA
            df.loc[mask, 'ema_10'] = calculate_ema(symbol_df, span=10)
            df.loc[mask, 'ema_50'] = calculate_ema(symbol_df, span=50)
            
            # RSI
            df.loc[mask, 'rsi'] = calculate_rsi(symbol_df)
            
            # MACD
            df.loc[mask, 'macd'] = calculate_macd(symbol_df)
            
            # Bollinger Bands
            bb_high, bb_low = calculate_bollinger_bands(symbol_df)
            df.loc[mask, 'bb_high'] = bb_high
            df.loc[mask, 'bb_low'] = bb_low
            
            # ATR
            df.loc[mask, 'atr'] = calculate_atr(symbol_df)
    else:
        # Single symbol
        df['ema_10'] = calculate_ema(df, span=10)
        df['ema_50'] = calculate_ema(df, span=50)
        df['rsi'] = calculate_rsi(df)
        df['macd'] = calculate_macd(df)
        df['bb_high'], df['bb_low'] = calculate_bollinger_bands(df)
        df['atr'] = calculate_atr(df)
    
    return df

def validate_features(df):
    """
    Check if all required features are present
    
    Returns:
        tuple: (is_valid, missing_features)
    """
    required_features = [
        'return', 'log_return', 'ema_10', 'ema_50', 
        'rsi', 'macd', 'bb_high', 'bb_low', 'atr'
    ]
    
    missing = [f for f in required_features if f not in df.columns]
    
    return len(missing) == 0, missing

if __name__ == "__main__":
    # Test the model
    dates = pd.date_range(start='2025-01-01', periods=100, freq='h')
    
    df = pd.DataFrame({
        'timestamp': dates,
        'symbol': 'TEST',
        'open': np.random.randn(100).cumsum() + 100,
        'high': np.random.randn(100).cumsum() + 102,
        'low': np.random.randn(100).cumsum() + 98,
        'close': np.random.randn(100).cumsum() + 100,
        'volume': np.random.randint(1000, 10000, 100)
    })
    
    # Engineer features
    result_df = engineer_features(df)
    
    print("Engineered Features (tail):")
    print(result_df[['timestamp', 'close', 'ema_10', 'rsi', 'macd']].tail())

