"""
Kafka Consumer Service

Runs the Kafka consumer continuously to process incoming stock data.
This service should run as a background process or container.
"""
import os
import sys
import logging
import signal
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kafka_pipeline.consumer import PredictionConsumer
from kafka_pipeline.config import KAFKA_BROKER, SASL_USERNAME, SASL_PASSWORD, CONSUMER_GROUP, TOPIC_WATCH

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/consumer_service.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global consumer instance for graceful shutdown
consumer_instance = None


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully"""
    logger.info("Received shutdown signal. Closing consumer gracefully...")
    if consumer_instance:
        try:
            consumer_instance.consumer.close()
            logger.info("Consumer closed successfully")
        except Exception as e:
            logger.error(f"Error closing consumer: {e}")
    sys.exit(0)


def main():
    """Main function to run consumer service"""
    global consumer_instance
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Ensure logs directory exists
    os.makedirs('logs', exist_ok=True)
    
    logger.info("="*60)
    logger.info("Starting Kafka Consumer Service")
    logger.info("="*60)
    logger.info(f"Kafka Broker: {KAFKA_BROKER}")
    logger.info(f"Topic: {TOPIC_WATCH}")
    logger.info(f"Consumer Group: {CONSUMER_GROUP}")
    logger.info("="*60)
    
    try:
        # Create consumer instance
        consumer_instance = PredictionConsumer(
            bootstrap_servers=KAFKA_BROKER,
            sasl_username=SASL_USERNAME,
            sasl_password=SASL_PASSWORD,
            group_id=CONSUMER_GROUP,
            topics=[TOPIC_WATCH],
            load_historical=True
        )
        
        logger.info("Consumer initialized successfully")
        logger.info("Starting to consume messages...")
        logger.info("Press Ctrl+C to stop")
        
        # Start consuming (this blocks until interrupted)
        # consume_and_validate() runs in a loop: for message in self.consumer:
        consumer_instance.consume_and_validate(max_messages=None)
        
    except KeyboardInterrupt:
        logger.info("Consumer interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error in consumer service: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if consumer_instance:
            try:
                consumer_instance.consumer.close()
                logger.info("Consumer service stopped")
            except:
                pass


if __name__ == '__main__':
    main()

