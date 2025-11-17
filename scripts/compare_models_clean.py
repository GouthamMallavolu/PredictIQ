"""
Model Comparison Script - Clean Version
Compares LSTM, Random Forest, and Moving Average models using real merged dataset
Generates comparison table for PDF report
"""
import pandas as pd
import numpy as np
import joblib
import time
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from tensorflow.keras.models import load_model
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.baseline_ma import MovingAveragePredictor

def load_merged_data():
    """Load the merged dataset"""
    if os.path.exists("Merged_dataset.csv"):
        print(f"Loading data from: Merged_dataset.csv")
        df = pd.read_csv("Merged_dataset.csv")
        print(f"Loaded {len(df)} records")
        return df
    else:
        raise FileNotFoundError("Merged_dataset.csv not found! Please ensure the file exists.")

def prepare_features(df):
    """Prepare features for model training using merged dataset"""
    print("Preparing features from merged dataset...")
    
    # The merged dataset already has technical indicators, so we'll use those
    # Use close_next as target (next hour price)
    df['target'] = df['close_next']
    
    # Select features for training
    feature_columns = [
        'open', 'high', 'low', 'close', 'volume', 
        'sentiment_mean', 'news_count', 'return', 'log_return',
        'ema_10', 'ema_50', 'rsi', 'macd', 'bb_high', 'bb_low', 'atr'
    ]
    
    # Remove rows with NaN values
    df = df.dropna(subset=feature_columns + ['target'])
    
    print(f"Features prepared: {len(df)} records with {len(feature_columns)} features")
    return df

def train_test_split_by_time(df, train_ratio=0.8):
    """Split data by time (first 80% train, last 20% test)"""
    print(f"Splitting data: {train_ratio*100:.0f}% train, {(1-train_ratio)*100:.0f}% test")
    
    # Sort by time
    df = df.sort_values('time')
    
    # Calculate split point
    split_idx = int(len(df) * train_ratio)
    
    train_df = df.iloc[:split_idx].copy()
    test_df = df.iloc[split_idx:].copy()
    
    print(f"   Training: {len(train_df)} records")
    print(f"   Testing: {len(test_df)} records")
    
    return train_df, test_df

def calculate_hit_rate_at_k(predictions, actuals, k=10):
    """Calculate Hit Rate @ K (percentage within $k of actual)"""
    errors = np.abs(predictions - actuals)
    hit_rate = np.mean(errors <= k)
    return hit_rate

def calculate_ndcg_at_k(predictions, actuals, k=5):
    """Calculate NDCG @ K"""
    # Rank predictions and actuals
    pred_ranks = np.argsort(predictions)[::-1]
    actual_ranks = np.argsort(actuals)[::-1]
    
    def dcg_at_k(ranks, k=k):
        return np.sum(1 / np.log2(ranks[:k] + 2))
    
    dcg = dcg_at_k(pred_ranks)
    idcg = dcg_at_k(actual_ranks)
    
    return dcg / idcg if idcg > 0 else 0

def evaluate_lstm_model(test_df):
    """Evaluate LSTM model"""
    print("\nEvaluating LSTM Model...")
    
    try:
        # Load trained model
        model = load_model("multi_stock_model_LSTM.keras")
        scaler = joblib.load("scaler.pkl")
        
        # Prepare test data
        feature_cols = [
            'open', 'high', 'low', 'close', 'volume', 
            'sentiment_mean', 'news_count', 'return', 'log_return',
            'ema_10', 'ema_50', 'rsi', 'macd', 'bb_high', 'bb_low', 'atr'
        ]
        X_test = test_df[feature_cols].values
        y_test = test_df['target'].values
        
        # Scale features
        X_test_scaled = scaler.transform(X_test)
        
        # Make predictions (simplified for demo - in real scenario, you'd need sequence data)
        predictions = model.predict(X_test_scaled.reshape(-1, 1, X_test_scaled.shape[1]))
        predictions = predictions.flatten()
        
        # Load actual training metrics
        training_metrics = joblib.load("lstm_training_metrics.pkl")
        train_mae = training_metrics['train_mae']  # Training MAE
        test_mae = training_metrics['test_mae']  # Test MAE
        rmse = np.sqrt(mean_squared_error(y_test, predictions))
        r2 = r2_score(y_test, predictions)
        hr_10 = calculate_hit_rate_at_k(predictions, y_test, k=10)
        ndcg_5 = calculate_ndcg_at_k(predictions, y_test, k=5)
        
        # Model size
        model_size_mb = os.path.getsize("multi_stock_model_LSTM.keras") / (1024 * 1024)
        
        # Calculate inference time
        start_time = time.time()
        _ = model.predict(X_test_scaled.reshape(-1, 1, X_test_scaled.shape[1]))
        inference_time = (time.time() - start_time) * 1000 / len(X_test_scaled)  # ms per prediction
        
        # Load actual training time
        training_metrics = joblib.load("lstm_training_metrics.pkl")
        training_time_min = training_metrics['training_time_min']
        
        return {
            'train_mae': train_mae,
            'test_mae': test_mae,
            'rmse': rmse,
            'r2': r2,
            'hr_10': hr_10,
            'ndcg_5': ndcg_5,
            'model_size_mb': model_size_mb,
            'training_time_min': training_time_min,
            'inference_ms': inference_time
        }
        
    except Exception as e:
        print(f"LSTM evaluation failed: {e}")
        raise e

def evaluate_random_forest_model(test_df):
    """Evaluate Random Forest model"""
    print("\nEvaluating Random Forest Model...")
    
    try:
        # Load trained model
        rf_model = joblib.load("random_forest_model.pkl")
        
        # Prepare features
        feature_cols = [
            'open', 'high', 'low', 'close', 'volume', 
            'sentiment_mean', 'news_count', 'return', 'log_return',
            'ema_10', 'ema_50', 'rsi', 'macd', 'bb_high', 'bb_low', 'atr'
        ]
        X_test = test_df[feature_cols].values
        y_test = test_df['target'].values
        
        # Make predictions
        predictions = rf_model.predict(X_test)
        
        # Load actual training metrics
        training_metrics = joblib.load("rf_training_metrics.pkl")
        train_mae = training_metrics['train_mae']  # Training MAE
        test_mae = training_metrics['test_mae']  # Test MAE
        rmse = np.sqrt(mean_squared_error(y_test, predictions))
        r2 = r2_score(y_test, predictions)
        hr_10 = calculate_hit_rate_at_k(predictions, y_test, k=10)
        ndcg_5 = calculate_ndcg_at_k(predictions, y_test, k=5)
        
        # Model size
        model_size_mb = os.path.getsize("random_forest_model.pkl") / (1024 * 1024)
        
        # Calculate inference time
        start_time = time.time()
        _ = rf_model.predict(X_test)
        inference_time = (time.time() - start_time) * 1000 / len(X_test)  # ms per prediction
        
        # Load actual training time
        training_metrics = joblib.load("rf_training_metrics.pkl")
        training_time_min = training_metrics['training_time_min']
        
        return {
            'train_mae': train_mae,
            'test_mae': test_mae,
            'rmse': rmse,
            'r2': r2,
            'hr_10': hr_10,
            'ndcg_5': ndcg_5,
            'model_size_mb': model_size_mb,
            'training_time_min': training_time_min,
            'inference_ms': inference_time
        }
        
    except Exception as e:
        print(f"Random Forest evaluation failed: {e}")
        raise e

def evaluate_moving_average_model(test_df):
    """Evaluate Moving Average baseline"""
    print("\nEvaluating Moving Average Model...")
    
    try:
        # Create model
        ma_model = MovingAveragePredictor(window=20)
        
        # Test on each symbol
        all_predictions = []
        all_actuals = []
        
        for symbol in test_df['symbol'].unique():
            symbol_data = test_df[test_df['symbol'] == symbol].sort_values('time')
            
            if len(symbol_data) >= 20:
                # Use last 20 points for prediction
                history = symbol_data.tail(20)
                prediction = ma_model.predict(history)
                actual = symbol_data['target'].iloc[-1]
                
                all_predictions.append(prediction)
                all_actuals.append(actual)
        
        all_predictions = np.array(all_predictions)
        all_actuals = np.array(all_actuals)
        
        # Load actual training metrics
        training_metrics = joblib.load("ma_training_metrics.pkl")
        train_mae = training_metrics['sample_mae']  # Sample MAE (no separate train/test for MA)
        test_mae = training_metrics['sample_mae']  # Same as sample for MA
        rmse = np.sqrt(mean_squared_error(all_actuals, all_predictions))
        r2 = r2_score(all_actuals, all_predictions)
        hr_10 = calculate_hit_rate_at_k(all_predictions, all_actuals, k=10)
        ndcg_5 = calculate_ndcg_at_k(all_predictions, all_actuals, k=5)
        
        # Calculate inference time for Moving Average
        start_time = time.time()
        test_predictions = []
        for symbol in test_df['symbol'].unique():
            symbol_data = test_df[test_df['symbol'] == symbol].sort_values('time')
            if len(symbol_data) >= 20:
                history = symbol_data.tail(20)
                prediction = ma_model.predict(history)
                test_predictions.append(prediction)
        inference_time = (time.time() - start_time) * 1000 / len(test_predictions)
        
        # Load actual training time
        training_metrics = joblib.load("ma_training_metrics.pkl")
        training_time_min = training_metrics['training_time_min']
        
        return {
            'train_mae': train_mae,
            'test_mae': test_mae,
            'rmse': rmse,
            'r2': r2,
            'hr_10': hr_10,
            'ndcg_5': ndcg_5,
            'model_size_mb': 0.001,  # Very small
            'training_time_min': training_time_min,
            'inference_ms': inference_time
        }
        
    except Exception as e:
        print(f"Moving Average evaluation failed: {e}")
        raise e

def generate_comparison_table(results):
    """Generate comparison table"""
    print("\n" + "="*80)
    print("MODEL COMPARISON RESULTS")
    print("="*80)
    
    # Create comparison table
    comparison_data = []
    
    for model_name, metrics in results.items():
        comparison_data.append({
            'Model': model_name.upper(),
            'Train MAE': f"{metrics['train_mae']:.2f}",
            'Test MAE': f"{metrics['test_mae']:.2f}",
            'HR@10': f"{metrics['hr_10']:.2f}",
            'NDCG@5': f"{metrics['ndcg_5']:.2f}",
            'Train Time (min)': f"{metrics['training_time_min']:.1f}",
            'Inference (ms)': f"{metrics['inference_ms']:.1f}",
            'Model Size (MB)': f"{metrics['model_size_mb']:.1f}"
        })
    
    # Create DataFrame
    comparison_df = pd.DataFrame(comparison_data)
    
    # Print table
    print(comparison_df.to_string(index=False))
    
    # Save to CSV
    comparison_df.to_csv('model_comparison.csv', index=False)
    print(f"\nComparison table saved to: model_comparison.csv")
    
    return comparison_df

def main():
    """Main comparison function"""
    print("Starting Model Comparison")
    print("="*50)
    
    # Load data
    df = load_merged_data()
    
    # Prepare features
    df = prepare_features(df)
    
    # Split data (80% train, 20% test)
    train_df, test_df = train_test_split_by_time(df, train_ratio=0.8)
    
    # Evaluate all models
    results = {}
    
    # LSTM
    results['lstm'] = evaluate_lstm_model(test_df)
    
    # Random Forest
    results['rf'] = evaluate_random_forest_model(test_df)
    
    # Moving Average
    results['ma'] = evaluate_moving_average_model(test_df)
    
    # Generate comparison table
    comparison_df = generate_comparison_table(results)
    
    print("\nModel comparison complete!")
    print("Files created:")
    print("   - model_comparison.csv")
    
    return results

if __name__ == "__main__":
    results = main()
