"""
Offline Evaluation for Stock Prediction Models
Implements chronological split, ranking metrics, and subpopulation analysis
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.metrics import mean_absolute_error, mean_squared_error
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def chronological_split(df, train_ratio=0.7, val_ratio=0.15):
    """
    Split data chronologically to avoid data leakage
    Ensures no future data leaks into training set
    
    Args:
        df: DataFrame with timestamp column
        train_ratio: Proportion for training (default 0.7)
        val_ratio: Proportion for validation (default 0.15)
    
    Returns:
        train_df, val_df, test_df
    """
    # Ensure data is sorted by timestamp
    if 'timestamp' in df.columns:
        df = df.sort_values('timestamp')
    elif 'date' in df.columns:
        df = df.sort_values('date')
        df['timestamp'] = pd.to_datetime(df['date'])
    else:
        # Use index as proxy for chronological order
        df = df.sort_index()
        df['timestamp'] = pd.to_datetime(df.index)
    
    n = len(df)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))
    
    train_df = df.iloc[:train_end].copy()
    val_df = df.iloc[train_end:val_end].copy()
    test_df = df.iloc[val_end:].copy()
    
    print(f"Chronological Split:")
    print(f"  Training: {len(train_df)} samples ({train_df['timestamp'].min()} to {train_df['timestamp'].max()})")
    print(f"  Validation: {len(val_df)} samples ({val_df['timestamp'].min()} to {val_df['timestamp'].max()})")
    print(f"  Test: {len(test_df)} samples ({test_df['timestamp'].min()} to {test_df['timestamp'].max()})")
    
    # Verify no leakage
    assert train_df['timestamp'].max() <= val_df['timestamp'].min(), "Data leakage detected!"
    assert val_df['timestamp'].max() <= test_df['timestamp'].min(), "Data leakage detected!"
    
    return train_df, val_df, test_df

def compute_ranking_metrics(y_true, y_pred, k=10):
    """
    Compute ranking metrics: NDCG@k and MAP
    
    Args:
        y_true: True values
        y_pred: Predicted values
        k: Top-k items to consider
    
    Returns:
        dict with NDCG@k and MAP scores
    """
    # Convert to ranking problem: rank predictions by error
    errors = np.abs(y_true - y_pred)
    
    # Sort by error (lower is better)
    ranked_indices = np.argsort(errors)
    
    # NDCG@k: Normalized Discounted Cumulative Gain
    def dcg_at_k(scores, k):
        scores = scores[:k]
        return np.sum(scores / np.log2(np.arange(2, len(scores) + 2)))
    
    # Ideal ranking (perfect predictions)
    ideal_errors = np.sort(errors)
    ideal_scores = 1 / (1 + ideal_errors)  # Convert errors to relevance scores
    
    # Actual ranking
    actual_scores = 1 / (1 + errors[ranked_indices[:k]])
    
    dcg = dcg_at_k(actual_scores, k)
    idcg = dcg_at_k(ideal_scores, k)
    
    ndcg = dcg / idcg if idcg > 0 else 0.0
    
    # MAP: Mean Average Precision (simplified for regression)
    # For regression, we use precision@k based on error threshold
    threshold = np.percentile(errors, 20)  # Top 20% most accurate
    relevant = errors <= threshold
    relevant_ranked = relevant[ranked_indices[:k]]
    
    if np.sum(relevant_ranked) > 0:
        precisions = []
        for i in range(1, min(k + 1, len(relevant_ranked) + 1)):
            if relevant_ranked[i-1]:
                precisions.append(np.sum(relevant_ranked[:i]) / i)
        map_score = np.mean(precisions) if precisions else 0.0
    else:
        map_score = 0.0
    
    return {
        'NDCG@k': ndcg,
        'MAP': map_score,
        'k': k
    }

def subpopulation_analysis(df, predictions, true_values, group_by='symbol'):
    """
    Analyze model performance across different subpopulations
    
    Args:
        df: DataFrame with grouping column
        predictions: Array of predictions
        true_values: Array of true values
        group_by: Column to group by (default 'symbol')
    
    Returns:
        DataFrame with metrics per subpopulation
    """
    results = []
    
    for group_value in df[group_by].unique():
        mask = df[group_by] == group_value
        group_pred = predictions[mask]
        group_true = true_values[mask]
        
        if len(group_pred) == 0:
            continue
        
        mae = mean_absolute_error(group_true, group_pred)
        rmse = np.sqrt(mean_squared_error(group_true, group_pred))
        mape = np.mean(np.abs((group_true - group_pred) / group_true)) * 100
        
        results.append({
            group_by: group_value,
            'samples': len(group_pred),
            'MAE': mae,
            'RMSE': rmse,
            'MAPE': mape,
            'mean_true': np.mean(group_true),
            'mean_pred': np.mean(group_pred)
        })
    
    results_df = pd.DataFrame(results)
    return results_df

def evaluate_model_offline(df, model_predictions, model_name='Model'):
    """
    Complete offline evaluation pipeline
    
    Args:
        df: DataFrame with features and targets
        model_predictions: Dictionary with 'train', 'val', 'test' predictions
        model_name: Name of the model
    
    Returns:
        Dictionary with evaluation results
    """
    print(f"\n{'='*60}")
    print(f"Offline Evaluation: {model_name}")
    print(f"{'='*60}")
    
    # Chronological split
    train_df, val_df, test_df = chronological_split(df)
    
    # Extract predictions
    train_pred = model_predictions.get('train', [])
    val_pred = model_predictions.get('val', [])
    test_pred = model_predictions.get('test', [])
    
    # Extract true values
    target_col = 'close' if 'close' in df.columns else df.columns[-1]
    train_true = train_df[target_col].values
    val_true = val_df[target_col].values
    test_true = test_df[target_col].values
    
    results = {}
    
    # Standard regression metrics
    for split_name, y_true, y_pred in [('train', train_true, train_pred),
                                        ('val', val_true, val_pred),
                                        ('test', test_true, test_pred)]:
        if len(y_pred) == 0:
            continue
            
        mae = mean_absolute_error(y_true, y_pred)
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
        
        # Ranking metrics
        ranking = compute_ranking_metrics(y_true, y_pred, k=10)
        
        results[split_name] = {
            'MAE': mae,
            'RMSE': rmse,
            'MAPE': mape,
            **ranking
        }
        
        print(f"\n{split_name.upper()} Set:")
        print(f"  MAE: {mae:.4f}")
        print(f"  RMSE: {rmse:.4f}")
        print(f"  MAPE: {mape:.2f}%")
        print(f"  NDCG@10: {ranking['NDCG@k']:.4f}")
        print(f"  MAP: {ranking['MAP']:.4f}")
    
    # Subpopulation analysis
    if 'symbol' in df.columns:
        print(f"\nSubpopulation Analysis (by symbol):")
        subpop_results = subpopulation_analysis(
            test_df, test_pred, test_true, group_by='symbol'
        )
        print(subpop_results.to_string(index=False))
        results['subpopulations'] = subpop_results.to_dict('records')
    
    return results

if __name__ == "__main__":
    # Example usage
    print("Offline Evaluation Module")
    print("Import this module to use evaluation functions")

