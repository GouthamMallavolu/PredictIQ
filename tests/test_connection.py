"""
Test script to verify Kafka Producer and Consumer connectivity
"""
import sys
import os
import json
import time
import logging
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
from config import *

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_producer():
    """Test if producer can connect and send messages"""
    logger.info("=" * 60)
    logger.info("TESTING PRODUCER CONNECTION")
    logger.info("=" * 60)
    
    try:
        producer = KafkaProducer(
            bootstrap_servers=[KAFKA_BROKER],
            security_protocol='SASL_SSL',
            sasl_mechanism='PLAIN',
            sasl_plain_username=SASL_USERNAME,
            sasl_plain_password=SASL_PASSWORD,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            api_version=(0, 10, 1)
        )
        
        logger.info(f"✓ Producer created successfully")
        logger.info(f"  Broker: {KAFKA_BROKER}")
        logger.info(f"  Topic: {TOPIC_WATCH}")
        
        # Send a test message
        test_message = {
            "symbol": "TEST",
            "timestamp": datetime.now().isoformat(),
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.5,
            "volume": 1000,
            "sentiment_mean": 0.0,
            "news_count": 0
        }
        
        logger.info("Sending test message...")
        future = producer.send(TOPIC_WATCH, value=test_message)
        
        # Wait for the message to be sent
        try:
            record_metadata = future.get(timeout=10)
            logger.info(f"✓ Message sent successfully!")
            logger.info(f"  Topic: {record_metadata.topic}")
            logger.info(f"  Partition: {record_metadata.partition}")
            logger.info(f"  Offset: {record_metadata.offset}")
            producer.flush()
            producer.close()
            return True
        except Exception as e:
            logger.error(f"✗ Failed to send message: {e}")
            producer.close()
            return False
            
    except Exception as e:
        logger.error(f"✗ Producer connection failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_consumer():
    """Test if consumer can connect and receive messages"""
    logger.info("=" * 60)
    logger.info("TESTING CONSUMER CONNECTION")
    logger.info("=" * 60)
    
    try:
        consumer = KafkaConsumer(
            TOPIC_WATCH,
            bootstrap_servers=KAFKA_BROKER,
            group_id=CONSUMER_GROUP + "_test",
            sasl_mechanism='PLAIN',
            security_protocol='SASL_SSL',
            sasl_plain_username=SASL_USERNAME,
            sasl_plain_password=SASL_PASSWORD,
            auto_offset_reset='latest',
            value_deserializer=lambda v: json.loads(v.decode('utf-8')),
            consumer_timeout_ms=10000  # 10 second timeout
        )
        
        logger.info(f"✓ Consumer created successfully")
        logger.info(f"  Broker: {KAFKA_BROKER}")
        logger.info(f"  Topic: {TOPIC_WATCH}")
        logger.info(f"  Consumer Group: {CONSUMER_GROUP}_test")
        logger.info("Waiting for messages (10 second timeout)...")
        
        # Try to consume messages
        message_count = 0
        for message in consumer:
            message_count += 1
            logger.info(f"✓ Message received!")
            logger.info(f"  Topic: {message.topic}")
            logger.info(f"  Partition: {message.partition}")
            logger.info(f"  Offset: {message.offset}")
            logger.info(f"  Value: {message.value}")
            
            if message_count >= 1:  # Just test one message
                break
        
        consumer.close()
        
        if message_count > 0:
            logger.info(f"✓ Consumer is working! Received {message_count} message(s)")
            return True
        else:
            logger.warning("⚠ Consumer connected but no messages received (this is OK if topic is empty)")
            return True  # Still consider it working if connection succeeds
            
    except Exception as e:
        logger.error(f"✗ Consumer connection failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    logger.info("Starting Kafka Connection Tests...")
    logger.info("")
    
    # Check environment variables
    logger.info("Checking environment variables...")
    if not SASL_PASSWORD:
        logger.error("✗ KAFKA_PASSWORD environment variable is not set!")
        sys.exit(1)
    if not KAFKA_BROKER:
        logger.error("✗ KAFKA_BROKER environment variable is not set!")
        sys.exit(1)
    logger.info("✓ Environment variables are set")
    logger.info("")
    
    # Test producer
    producer_ok = test_producer()
    logger.info("")
    
    # Wait a bit before testing consumer
    time.sleep(2)
    
    # Test consumer
    consumer_ok = test_consumer()
    logger.info("")
    
    # Summary
    logger.info("=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Producer: {'✓ WORKING' if producer_ok else '✗ FAILED'}")
    logger.info(f"Consumer: {'✓ WORKING' if consumer_ok else '✗ FAILED'}")
    
    if producer_ok and consumer_ok:
        logger.info("")
        logger.info("✓ Both producer and consumer are working!")
        sys.exit(0)
    else:
        logger.info("")
        logger.error("✗ Some components are not working. Check the errors above.")
        sys.exit(1)

