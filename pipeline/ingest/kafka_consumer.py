"""
Kafka Consumer with Backpressure Handling

Implements queue-based backpressure for Kafka message consumption.
"""

import logging
from queue import Queue, Full
from typing import Dict, Any, Optional, List
from kafka import KafkaConsumer
from kafka.errors import KafkaError

from pipeline.config import get_config

logger = logging.getLogger(__name__)


class KafkaConsumerWithBackpressure:
    """
    Kafka consumer with built-in backpressure handling.
    
    Uses a bounded queue to prevent overwhelming downstream systems.
    """
    
    def __init__(self, topics: List[str], config: Optional[Any] = None):
        """
        Initialize Kafka consumer with backpressure.
        
        Args:
            topics: List of Kafka topics to subscribe to
            config: Pipeline configuration (uses default if None)
        """
        self.config = config or get_config()
        self.topics = topics
        self.consumer: Optional[KafkaConsumer] = None
        self.queue: Optional[Queue] = None
        self._running = False
        
        if self.config.kafka.backpressure_enabled:
            self.queue = Queue(maxsize=self.config.kafka.max_queue_size)
            logger.info(f"Backpressure enabled with queue size: {self.config.kafka.max_queue_size}")
    
    def connect(self):
        """Establish connection to Kafka"""
        try:
            self.consumer = KafkaConsumer(
                *self.topics,
                bootstrap_servers=self.config.kafka.broker,
                security_protocol='SASL_SSL',
                sasl_mechanism='PLAIN',
                sasl_plain_username=self.config.kafka.username,
                sasl_plain_password=self.config.kafka.password,
                group_id=self.config.kafka.consumer_group_id,
                max_poll_records=self.config.kafka.max_poll_records,
                enable_auto_commit=True,
                auto_offset_reset='latest',
                value_deserializer=lambda v: v.decode('utf-8') if v else None
            )
            self._running = True
            logger.info(f"Connected to Kafka: {self.config.kafka.broker}")
            logger.info(f"Subscribed to topics: {self.topics}")
        except KafkaError as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            raise
    
    def poll(self, timeout_ms: int = 1000) -> List[Dict[str, Any]]:
        """
        Poll for messages with backpressure.
        
        Args:
            timeout_ms: Poll timeout in milliseconds
        
        Returns:
            List of messages
        """
        if not self.consumer:
            raise RuntimeError("Consumer not connected. Call connect() first.")
        
        messages = []
        
        try:
            # Poll from Kafka
            records = self.consumer.poll(timeout_ms=timeout_ms)
            
            for topic_partition, msgs in records.items():
                for msg in msgs:
                    message = {
                        'topic': msg.topic,
                        'partition': msg.partition,
                        'offset': msg.offset,
                        'key': msg.key.decode('utf-8') if msg.key else None,
                        'value': msg.value,
                        'timestamp': msg.timestamp
                    }
                    
                    # Apply backpressure if enabled
                    if self.queue:
                        try:
                            # Non-blocking put with timeout
                            self.queue.put(message, block=True, timeout=self.config.kafka.poll_interval)
                            messages.append(message)
                        except Full:
                            logger.warning("Queue full - applying backpressure")
                            # Don't add to messages - will be re-polled next time
                            break
                    else:
                        messages.append(message)
            
            if messages:
                logger.debug(f"Polled {len(messages)} messages")
            
        except KafkaError as e:
            logger.error(f"Error polling messages: {e}")
        
        return messages
    
    def get_from_queue(self, timeout: float = 1.0) -> Optional[Dict[str, Any]]:
        """
        Get a message from the backpressure queue.
        
        Args:
            timeout: Timeout in seconds
        
        Returns:
            Message dict or None if queue empty
        """
        if not self.queue:
            raise RuntimeError("Backpressure not enabled")
        
        try:
            return self.queue.get(timeout=timeout)
        except:
            return None
    
    def queue_size(self) -> int:
        """Get current queue size"""
        return self.queue.qsize() if self.queue else 0
    
    def is_queue_full(self) -> bool:
        """Check if queue is full"""
        if not self.queue:
            return False
        return self.queue.full()
    
    def close(self):
        """Close the consumer"""
        self._running = False
        if self.consumer:
            self.consumer.close()
            logger.info("Kafka consumer closed")
