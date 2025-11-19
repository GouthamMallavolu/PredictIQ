"""
Unit tests for schema validation module
"""
import pytest
import pandas as pd
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quality.schemas.validate_schemas import (
    validate_stock_data,
    validate_api_request,
    validate_api_response,
    validate_kafka_reco_request,
    validate_kafka_reco_response
)

def test_validate_stock_data_valid():
    """Test valid stock data passes validation"""
    df = pd.DataFrame({
        'symbol': ['AAPL', 'MSFT'],
        'date': pd.to_datetime(['2024-01-01', '2024-01-02']),
        'open': [100.0, 200.0],
        'high': [105.0, 205.0],
        'low': [95.0, 195.0],
        'close': [102.0, 202.0],
        'volume': [1000000, 2000000],
        'adjusted_close': [102.0, 202.0]
    })
    
    is_valid, error = validate_stock_data(df)
    assert is_valid
    assert error is None

def test_validate_stock_data_invalid():
    """Test invalid stock data fails validation"""
    df = pd.DataFrame({
        'symbol': ['AAPL'],
        'date': pd.to_datetime(['2024-01-01']),
        'open': [-100.0],  # Negative price - invalid
        'high': [105.0],
        'low': [95.0],
        'close': [102.0],
        'volume': [1000000],
        'adjusted_close': [102.0]  # Add required column
    })
    
    is_valid, error = validate_stock_data(df)
    assert not is_valid  # Should fail because open is negative
    assert error is not None
    assert 'open' in error.lower() or 'greater_than' in error.lower()

def test_validate_api_request():
    """Test API request validation"""
    request = {
        'user_id': 'user123',
        'symbols': ['AAPL', 'MSFT'],
        'model': 'lstm'
    }
    
    is_valid, error = validate_api_request(request)
    assert is_valid
    assert error is None

def test_validate_api_response():
    """Test API response validation"""
    response = {
        'request_id': 'req123',
        'timestamp': '2024-01-01T00:00:00',
        'status': 'success',
        'results': {},
        'model_used': 'lstm',
        'latency_ms': 100.0
    }
    
    is_valid, error = validate_api_response(response)
    assert is_valid
    assert error is None

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

