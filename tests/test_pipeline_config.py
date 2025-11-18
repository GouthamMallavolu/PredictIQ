"""
Unit tests for pipeline configuration module
"""

import pytest
import os
from pipeline.config import (
    APIConfig, KafkaConfig, ModelConfig, PathConfig, ServingConfig,
    PipelineConfig, get_config, reload_config
)


def test_api_config_from_env(monkeypatch):
    """Test API config loading from environment"""
    monkeypatch.setenv('ALPHA_VANTAGE_API_KEY', 'test_key')
    monkeypatch.setenv('API_RATE_LIMIT', '10')
    monkeypatch.setenv('API_TIMEOUT', '60')
    
    config = APIConfig.from_env()
    
    assert config.alpha_vantage_key == 'test_key'
    assert config.rate_limit == 10
    assert config.timeout == 60


def test_kafka_config_from_env(monkeypatch):
    """Test Kafka config loading from environment"""
    monkeypatch.setenv('KAFKA_BROKER', 'localhost:9092')
    monkeypatch.setenv('KAFKA_USERNAME', 'user')
    monkeypatch.setenv('KAFKA_PASSWORD', 'pass')
    monkeypatch.setenv('KAFKA_BACKPRESSURE', 'true')
    monkeypatch.setenv('KAFKA_MAX_QUEUE_SIZE', '500')
    
    config = KafkaConfig.from_env()
    
    assert config.broker == 'localhost:9092'
    assert config.username == 'user'
    assert config.password == 'pass'
    assert config.backpressure_enabled == True
    assert config.max_queue_size == 500


def test_model_config_from_env(monkeypatch):
    """Test model config loading from environment"""
    monkeypatch.setenv('MODEL_PATH', 'custom/models/')
    monkeypatch.setenv('TRAIN_BATCH_SIZE', '64')
    monkeypatch.setenv('TRAIN_EPOCHS', '100')
    
    config = ModelConfig.from_env()
    
    assert config.path == 'custom/models/'
    assert config.batch_size == 64
    assert config.epochs == 100


def test_serving_config_from_env(monkeypatch):
    """Test serving config loading from environment"""
    monkeypatch.setenv('SERVING_CACHE_TTL', '600')
    monkeypatch.setenv('SERVING_MAX_BATCH_SIZE', '20')
    
    config = ServingConfig.from_env()
    
    assert config.cache_ttl == 600
    assert config.max_batch_size == 20


def test_pipeline_config_integration():
    """Test full pipeline config loading"""
    config = PipelineConfig.from_env()
    
    assert isinstance(config.api, APIConfig)
    assert isinstance(config.kafka, KafkaConfig)
    assert isinstance(config.models, ModelConfig)
    assert isinstance(config.paths, PathConfig)
    assert isinstance(config.serving, ServingConfig)


def test_get_config():
    """Test getting global config instance"""
    config = get_config()
    assert isinstance(config, PipelineConfig)


def test_config_defaults():
    """Test default configuration values"""
    config = APIConfig.from_env()
    assert config.rate_limit == 5
    assert config.timeout == 30
    
    config = KafkaConfig.from_env()
    assert config.backpressure_enabled == True
    assert config.max_queue_size == 1000
    
    config = ServingConfig.from_env()
    assert config.cache_ttl == 300
