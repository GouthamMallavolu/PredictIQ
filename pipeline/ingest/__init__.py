"""
Ingest Module

Data ingestion with rate limiting and backpressure handling.
"""

from .rate_limiter import RateLimiter
from .kafka_consumer import KafkaConsumerWithBackpressure

__all__ = ['RateLimiter', 'KafkaConsumerWithBackpressure']
