"""
Baseline Model 1: Moving Average Predictor
Simple baseline for comparison with ML models
"""
import numpy as np
import pandas as pd
from typing import List, Dict

class MovingAveragePredictor:
    """
    Simple Moving Average baseline model
    Predicts next price as average of last N prices
    """
    def __init__(self, window=20):
        self.window = window
        self.name = f"MovingAverage_{window}"
    
    def predict(self, stock_history: pd.DataFrame) -> float:
        """
        Predict next price based on moving average
        
        Args:
            stock_history: DataFrame with 'close' column
        
        Returns:
            Predicted price
        """
        if len(stock_history) < self.window:
            # Not enough data, use all available
            return stock_history['close'].mean()
        
        # Use last N prices
        recent_prices = stock_history['close'].tail(self.window)
        return recent_prices.mean()
    
    def predict_batch(self, histories: Dict[str, pd.DataFrame]) -> Dict[str, float]:
        """
        Predict for multiple symbols
        
        Args:
            histories: Dict mapping symbol -> DataFrame
        
        Returns:
            Dict mapping symbol -> predicted price
        """
        predictions = {}
        for symbol, history in histories.items():
            predictions[symbol] = self.predict(history)
        return predictions
    
    def get_model_info(self) -> Dict:
        """Return model metadata"""
        return {
            "name": self.name,
            "type": "baseline",
            "window": self.window,
            "parameters": 0,
            "size_bytes": 0
        }

if __name__ == "__main__":
    # Test the model
    import pandas as pd
    
    # Create sample data
    dates = pd.date_range(start='2025-01-01', periods=100, freq='h')
    prices = np.random.randn(100).cumsum() + 100
    
    df = pd.DataFrame({
        'time': dates,
        'close': prices
    })
    
    model = MovingAveragePredictor(window=20)
    prediction = model.predict(df)
    
    print(f"Model: {model.name}")
    print(f"Last 5 prices: {df['close'].tail(5).values}")
    print(f"Predicted next price: ${prediction:.2f}")
    print(f"Actual next (simulated): ${prices[-1] + np.random.randn():.2f}")

