"""
Unit tests for drift detection module
"""
import pytest
import pandas as pd
import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quality.drift.detect_drift import (
    detect_distribution_drift,
    detect_symbol_distribution_drift,
    detect_feature_drift
)

def test_detect_distribution_drift_no_drift():
    """Test drift detection when distributions are similar"""
    reference = np.random.normal(100, 10, 1000)
    current = np.random.normal(100, 10, 1000)
    
    result = detect_distribution_drift(
        pd.Series(reference),
        pd.Series(current),
        test_name="KS"
    )
    
    assert 'drift_detected' in result
    assert 'p_value' in result
    # With similar distributions, drift should not be detected (or p-value should be high)
    assert result['p_value'] > 0.01  # Very similar distributions

def test_detect_symbol_distribution_drift():
    """Test symbol distribution drift detection"""
    reference_df = pd.DataFrame({
        'symbol': ['AAPL'] * 50 + ['MSFT'] * 50
    })
    current_df = pd.DataFrame({
        'symbol': ['AAPL'] * 50 + ['MSFT'] * 50
    })
    
    result = detect_symbol_distribution_drift(reference_df, current_df)
    
    assert 'drift_detected' in result
    assert 'p_value' in result
    # Same distribution, so drift should not be detected
    assert result['p_value'] > 0.05

def test_detect_feature_drift():
    """Test feature drift detection"""
    reference_df = pd.DataFrame({
        'feature1': np.random.normal(100, 10, 100),
        'feature2': np.random.normal(50, 5, 100)
    })
    current_df = pd.DataFrame({
        'feature1': np.random.normal(100, 10, 100),
        'feature2': np.random.normal(50, 5, 100)
    })
    
    result = detect_feature_drift(reference_df, current_df)
    
    assert 'overall_drift_detected' in result
    assert 'features_checked' in result
    assert 'feature_results' in result
    assert len(result['feature_results']) == 2

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

