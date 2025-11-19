"""
Pipeline Configuration Module

Environment-based configuration for all pipeline stages.
Supports .env files and environment variables.
"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class APIConfig:
    """API configuration"""
    alpha_vantage_key: str
    rate_limit: int = 5  # requests per minute
    timeout: int = 30
    
    @classmethod
    def from_env(cls):
        return cls(
            alpha_vantage_key=os.getenv('ALPHA_VANTAGE_API_KEY', ''),
            rate_limit=int(os.getenv('API_RATE_LIMIT', '5')),
            timeout=int(os.getenv('API_TIMEOUT', '30'))
        )


@dataclass
class KafkaConfig:
    """Kafka configuration"""
    broker: str
    username: str
    password: str
    topic_requests: str
    topic_responses: str
    consumer_group_id: str = "finsightai-consumer"
    max_poll_records: int = 100
    backpressure_enabled: bool = True
    max_queue_size: int = 1000
    poll_interval: float = 1.0
    
    @classmethod
    def from_env(cls):
        return cls(
            broker=os.getenv('KAFKA_BROKER', ''),
            username=os.getenv('KAFKA_USERNAME', ''),
            password=os.getenv('KAFKA_PASSWORD', ''),
            topic_requests=os.getenv('KAFKA_TOPIC_RECO_REQUESTS', 'team05.reco_requests'),
            topic_responses=os.getenv('KAFKA_TOPIC_RECO_RESPONSES', 'team05.reco_responses'),
            consumer_group_id=os.getenv('KAFKA_CONSUMER_GROUP', 'finsightai-consumer'),
            max_poll_records=int(os.getenv('KAFKA_MAX_POLL_RECORDS', '100')),
            backpressure_enabled=os.getenv('KAFKA_BACKPRESSURE', 'true').lower() == 'true',
            max_queue_size=int(os.getenv('KAFKA_MAX_QUEUE_SIZE', '1000')),
            poll_interval=float(os.getenv('KAFKA_POLL_INTERVAL', '1.0'))
        )


@dataclass
class ModelConfig:
    """Model configuration"""
    path: str
    lstm_file: str
    rf_file: str
    scaler_file: str
    batch_size: int = 32
    epochs: int = 50
    validation_split: float = 0.2
    
    @classmethod
    def from_env(cls):
        return cls(
            path=os.getenv('MODEL_PATH', 'models/'),
            lstm_file=os.getenv('LSTM_MODEL_FILE', 'multi_stock_model_LSTM.keras'),
            rf_file=os.getenv('RF_MODEL_FILE', 'random_forest_model.pkl'),
            scaler_file=os.getenv('SCALER_FILE', 'scaler.pkl'),
            batch_size=int(os.getenv('TRAIN_BATCH_SIZE', '32')),
            epochs=int(os.getenv('TRAIN_EPOCHS', '50')),
            validation_split=float(os.getenv('TRAIN_VAL_SPLIT', '0.2'))
        )


@dataclass
class PathConfig:
    """Path configuration"""
    data: str
    logs: str
    cache: str
    
    @classmethod
    def from_env(cls):
        return cls(
            data=os.getenv('DATA_PATH', 'data/'),
            logs=os.getenv('LOGS_PATH', 'logs/'),
            cache=os.getenv('CACHE_PATH', 'cache/')
        )


@dataclass
class ServingConfig:
    """Serving configuration"""
    cache_ttl: int = 300  # seconds
    max_batch_size: int = 10
    timeout: float = 5.0
    
    @classmethod
    def from_env(cls):
        return cls(
            cache_ttl=int(os.getenv('SERVING_CACHE_TTL', '300')),
            max_batch_size=int(os.getenv('SERVING_MAX_BATCH_SIZE', '10')),
            timeout=float(os.getenv('SERVING_TIMEOUT', '5.0'))
        )


@dataclass
class PipelineConfig:
    """Main pipeline configuration"""
    api: APIConfig
    kafka: KafkaConfig
    models: ModelConfig
    paths: PathConfig
    serving: ServingConfig
    
    @classmethod
    def from_env(cls):
        """Load configuration from environment variables"""
        return cls(
            api=APIConfig.from_env(),
            kafka=KafkaConfig.from_env(),
            models=ModelConfig.from_env(),
            paths=PathConfig.from_env(),
            serving=ServingConfig.from_env()
        )


# Global configuration instance
config = PipelineConfig.from_env()


def get_config() -> PipelineConfig:
    """Get global configuration instance"""
    return config


def reload_config():
    """Reload configuration from environment"""
    global config
    load_dotenv(override=True)
    config = PipelineConfig.from_env()
    return config
