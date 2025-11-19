"""
Pipeline Usage Example

Demonstrates the modular pipeline structure:
  ingest → transform → train → serialize → serve → eval
"""

from pipeline.config import get_config
from pipeline.ingest import RateLimiter, KafkaConsumerWithBackpressure
from pipeline.serve import PredictionService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def example_rate_limiting():
    """Example: Rate limiting for API calls"""
    config = get_config()
    
    # Create rate limiter (5 calls per minute)
    rate_limiter = RateLimiter(
        max_calls=config.api.rate_limit,
        time_window=60.0
    )
    
    logger.info("Rate Limiter Example:")
    logger.info(f"Max calls: {config.api.rate_limit} per minute")
    
    # Make controlled API calls
    for i in range(7):
        if rate_limiter.acquire(blocking=True, timeout=5.0):
            logger.info(f"Call {i+1} approved")
            # Make your API call here
        else:
            logger.warning(f"Call {i+1} rate limited")
    
    return rate_limiter


def example_kafka_backpressure():
    """Example: Kafka consumer with backpressure"""
    config = get_config()
    
    # Create consumer with backpressure
    consumer = KafkaConsumerWithBackpressure(
        topics=[config.kafka.topic_requests],
        config=config
    )
    
    logger.info("Kafka Consumer Example:")
    logger.info(f"Backpressure enabled: {config.kafka.backpressure_enabled}")
    logger.info(f"Max queue size: {config.kafka.max_queue_size}")
    
    # Note: Requires valid Kafka credentials to actually connect
    # consumer.connect()
    # messages = consumer.poll(timeout_ms=1000)
    # logger.info(f"Received {len(messages)} messages")
    # logger.info(f"Queue size: {consumer.queue_size()}")
    # consumer.close()
    
    return consumer


def example_prediction_service():
    """Example: Model serving"""
    logger.info("Prediction Service Example:")
    
    # Initialize service (uses config for model paths)
    service = PredictionService()
    
    # Make prediction
    # prediction = service.predict(symbols=["AAPL", "MSFT", "NVDA"], model="lstm")
    # logger.info(f"Prediction: {prediction}")
    
    return service


def example_pipeline_config():
    """Example: Environment-based configuration"""
    config = get_config()
    
    logger.info("Pipeline Configuration:")
    logger.info(f"  API Rate Limit: {config.api.rate_limit} calls/min")
    logger.info(f"  Kafka Broker: {config.kafka.broker}")
    logger.info(f"  Model Path: {config.models.path}")
    logger.info(f"  Cache TTL: {config.serving.cache_ttl}s")
    logger.info(f"  Backpressure: {config.kafka.backpressure_enabled}")
    
    return config


if __name__ == "__main__":
    logger.info("="*60)
    logger.info("MODULAR PIPELINE DEMONSTRATION")
    logger.info("="*60)
    
    # Stage 0: Configuration
    logger.info("\n1. CONFIGURATION (env-based)")
    config = example_pipeline_config()
    
    # Stage 1: Ingest with rate limiting
    logger.info("\n2. INGEST (with backpressure)")
    rate_limiter = example_rate_limiting()
    
    # Stage 2: Transform (placeholder)
    logger.info("\n3. TRANSFORM")
    logger.info("  Feature engineering happens here")
    
    # Stage 3: Train (placeholder)
    logger.info("\n4. TRAIN")
    logger.info("  Model training happens here")
    
    # Stage 4: Serialize (placeholder)
    logger.info("\n5. SERIALIZE")
    logger.info("  Model saving/loading happens here")
    
    # Stage 5: Serve
    logger.info("\n6. SERVE")
    service = example_prediction_service()
    
    # Stage 6: Eval (placeholder)
    logger.info("\n7. EVAL")
    logger.info("  Offline/online evaluation happens here")
    
    logger.info("\n" + "="*60)
    logger.info("Pipeline stages complete!")
    logger.info("="*60)
