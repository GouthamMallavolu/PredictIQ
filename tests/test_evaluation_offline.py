"""
Unit tests for offline evaluation module
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.offline.evaluate_offline import (
    chronological_split,
    compute_ranking_metrics,
    subpopulation_analysis,
    evaluate_model_offline
)

def test_chronological_split():
    """Test chronological split prevents data leakage"""
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    df = pd.DataFrame({
        'timestamp': dates,
        'value': np.random.randn(100),
        'symbol': ['AAPL'] * 100
    })
    
    train, val, test = chronological_split(df, train_ratio=0.7, val_ratio=0.15)
    
    assert len(train) == 70
    assert len(val) == 15
    assert len(test) == 15
    
    # Check no leakage
    assert train['timestamp'].max() <= val['timestamp'].min()
    assert val['timestamp'].max() <= test['timestamp'].min()

def test_compute_ranking_metrics():
    """Test ranking metrics computation"""
    y_true = np.array([100, 200, 300, 400, 500])
    y_pred = np.array([105, 195, 310, 390, 510])
    
    metrics = compute_ranking_metrics(y_true, y_pred, k=5)
    
    assert 'NDCG@k' in metrics
    assert 'MAP' in metrics
    assert metrics['k'] == 5
    assert 0 <= metrics['NDCG@k'] <= 1
    assert 0 <= metrics['MAP'] <= 1

def test_subpopulation_analysis():
    """Test subpopulation analysis"""
    df = pd.DataFrame({
        'symbol': ['AAPL', 'AAPL', 'MSFT', 'MSFT'],
        'value': [100, 200, 150, 250]
    })
    predictions = np.array([105, 195, 155, 245])
    true_values = np.array([100, 200, 150, 250])
    
    results = subpopulation_analysis(df, predictions, true_values, group_by='symbol')
    
    assert len(results) == 2
    assert 'AAPL' in results['symbol'].values
    assert 'MSFT' in results['symbol'].values
    assert 'MAE' in results.columns
    assert 'RMSE' in results.columns

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

