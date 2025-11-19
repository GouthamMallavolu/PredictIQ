"""
Pydantic schemas for data validation
Required for Task 2: Stream ingestor with schema validation
"""
from pydantic import BaseModel, validator, Field
from datetime import datetime
from typing import Optional

class StockWatchEvent(BaseModel):
    """Schema for team01.watch topic - stock price + news data"""
    symbol: str
    timestamp: str
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: int = Field(ge=0)
    sentiment_mean: float = Field(ge=-1, le=1)
    news_count: int = Field(ge=0)
    
    @validator('symbol')
    def symbol_must_be_valid(cls, v):
        valid = ['AAPL', 'MSFT', 'AMZN', 'NVDA', 'META', 'TSLA', 'TSM']
        if v not in valid:
            raise ValueError(f'Invalid symbol: {v}')
        return v
    
    @validator('timestamp')
    def timestamp_must_be_parseable(cls, v):
        try:
            datetime.fromisoformat(v)
        except:
            raise ValueError(f'Invalid timestamp format: {v}')
        return v

class PriceChangeEvent(BaseModel):
    """Schema for team01.rate topic - price changes and volatility"""
    symbol: str
    timestamp: str
    open: float = Field(gt=0)
    close: float = Field(gt=0)
    price_change: float
    price_change_pct: float
    volatility: float = Field(ge=0)
    volume: int = Field(ge=0)
    signal: str  # 'bullish' or 'bearish'
    
    @validator('signal')
    def signal_must_be_valid(cls, v):
        if v not in ['bullish', 'bearish', 'neutral']:
            raise ValueError(f'Invalid signal: {v}')
        return v

class RecoRequest(BaseModel):
    """Schema for team01.reco_requests topic"""
    request_id: str
    user_id: str
    symbols: list[str]
    top_k: int = Field(default=5, ge=1, le=10)
    timestamp: str
    model_preference: Optional[str] = "lstm"  # 'lstm', 'rf', 'ma', 'ensemble'

class RecoResponse(BaseModel):
    """Schema for team01.reco_responses topic"""
    request_id: str
    recommendations: list[dict]  # [{symbol, score, predicted_price, rank}]
    model_used: str
    latency_ms: float
    timestamp: str
    is_personalized: bool

