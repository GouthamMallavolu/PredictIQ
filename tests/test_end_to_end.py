"""
End-to-end test for Producer -> Consumer -> Predictions pipeline
Tests the full flow with Oct 30th data
"""
import sys
import os
import json
import time
import logging
import threading
from datetime import datetime
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import *

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EndToEndTester:
    def __init__(self):
        self.predictions_received = []
        self.messages_sent = 0
        self.messages_consumed = 0
        self.test_complete = False
        
    def monitor_response_topic(self, duration=60):
        """Monitor the response topic for predictions"""
        logger.info("=" * 60)
        logger.info("MONITORING RESPONSE TOPIC FOR PREDICTIONS")
        logger.info("=" * 60)
        
        try:
            consumer = KafkaConsumer(
                TOPIC_RECO_RESPONSES,
                bootstrap_servers=KAFKA_BROKER,
                group_id=CONSUMER_GROUP + "_e2e_test",
                sasl_mechanism='PLAIN',
                security_protocol='SASL_SSL',
                sasl_plain_username=SASL_USERNAME,
                sasl_plain_password=SASL_PASSWORD,
                auto_offset_reset='latest',
                value_deserializer=lambda v: json.loads(v.decode('utf-8')),
                consumer_timeout_ms=duration * 1000
            )
            
            logger.info(f"✓ Monitoring topic: {TOPIC_RECO_RESPONSES}")
            logger.info(f"  Waiting up to {duration} seconds for predictions...")
            
            start_time = time.time()
            for message in consumer:
                elapsed = time.time() - start_time
                if elapsed > duration:
                    break
                    
                prediction = message.value
                self.predictions_received.append(prediction)
                
                logger.info(f"✓ PREDICTION RECEIVED (after {elapsed:.1f}s):")
                logger.info(f"  Symbol: {prediction.get('symbol')}")
                logger.info(f"  Predicted Close: {prediction.get('predicted_close')}")
                logger.info(f"  Prediction Timestamp: {prediction.get('prediction_timestamp')}")
                logger.info(f"  Target Timestamp: {prediction.get('target_timestamp')}")
                logger.info(f"  Model Version: {prediction.get('model_version')}")
                logger.info("")
            
            consumer.close()
            logger.info(f"✓ Finished monitoring. Received {len(self.predictions_received)} predictions")
            
        except Exception as e:
            logger.error(f"✗ Error monitoring response topic: {e}")
            import traceback
            traceback.print_exc()
    
    def monitor_watch_topic(self, duration=30):
        """Monitor the watch topic to see how many messages are being consumed"""
        logger.info("=" * 60)
        logger.info("MONITORING WATCH TOPIC")
        logger.info("=" * 60)
        
        try:
            consumer = KafkaConsumer(
                TOPIC_WATCH,
                bootstrap_servers=KAFKA_BROKER,
                group_id=CONSUMER_GROUP + "_monitor",
                sasl_mechanism='PLAIN',
                security_protocol='SASL_SSL',
                sasl_plain_username=SASL_USERNAME,
                sasl_plain_password=SASL_PASSWORD,
                auto_offset_reset='latest',
                value_deserializer=lambda v: json.loads(v.decode('utf-8')),
                consumer_timeout_ms=duration * 1000
            )
            
            logger.info(f"✓ Monitoring topic: {TOPIC_WATCH}")
            logger.info(f"  Counting messages for {duration} seconds...")
            
            start_time = time.time()
            for message in consumer:
                elapsed = time.time() - start_time
                if elapsed > duration:
                    break
                    
                self.messages_consumed += 1
                if self.messages_consumed % 10 == 0:
                    logger.info(f"  Consumed {self.messages_consumed} messages...")
            
            consumer.close()
            logger.info(f"✓ Finished monitoring. Consumed {self.messages_consumed} messages")
            
        except Exception as e:
            logger.error(f"✗ Error monitoring watch topic: {e}")
            import traceback
            traceback.print_exc()

def check_models_exist():
    """Check if required model files exist"""
    logger.info("=" * 60)
    logger.info("CHECKING REQUIRED MODELS")
    logger.info("=" * 60)
    
    # Check in current directory and parent directory
    base_paths = ['.', '..']
    required_files = [
        'multi_stock_model_LSTM.keras',
        'random_forest_model.pkl',
        'scaler.pkl'
    ]
    
    all_exist = True
    for file in required_files:
        found = False
        for base_path in base_paths:
            file_path = os.path.join(base_path, file)
            if os.path.exists(file_path):
                logger.info(f"✓ Found: {file_path}")
                found = True
                break
        
        if not found:
            logger.error(f"✗ Missing: {file}")
            all_exist = False
    
    return all_exist

def run_producer_test(date='2025-10-30', delay=5):
    """Run producer to send test data"""
    logger.info("=" * 60)
    logger.info("RUNNING PRODUCER TEST")
    logger.info("=" * 60)
    logger.info(f"Date: {date}, Delay: {delay}s")
    
    try:
        # Import and run producer
        import importlib.util
        spec = importlib.util.spec_from_file_location("producer", "kafka_pipeline/producer.py")
        producer_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(producer_module)
        
        producer = producer_module.StockDataProducer()
        producer.simulate_streaming(date=date, delay_seconds=delay)
        producer.close()
        
        logger.info("✓ Producer completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"✗ Producer failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_consumer_test(max_messages=50):
    """Run consumer to process messages and generate predictions"""
    logger.info("=" * 60)
    logger.info("RUNNING CONSUMER TEST")
    logger.info("=" * 60)
    logger.info(f"Max messages: {max_messages}")
    
    try:
        # Import and run consumer
        import importlib.util
        spec = importlib.util.spec_from_file_location("consumer", "kafka_pipeline/consumer.py")
        consumer_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(consumer_module)
        
        consumer = consumer_module.PredictionConsumer(
            bootstrap_servers=KAFKA_BROKER,
            sasl_username=SASL_USERNAME,
            sasl_password=SASL_PASSWORD,
            group_id=CONSUMER_GROUP + "_e2e",
            topics=[TOPIC_WATCH],
            load_historical=True
        )
        
        logger.info("✓ Consumer initialized")
        logger.info("  Starting to consume messages and generate predictions...")
        
        consumer.consume_and_validate(max_messages=max_messages)
        
        logger.info("✓ Consumer completed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Consumer failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("END-TO-END PIPELINE TEST")
    logger.info("=" * 60)
    logger.info("")
    
    # Step 1: Check models
    if not check_models_exist():
        logger.error("✗ Missing required model files. Cannot proceed.")
        sys.exit(1)
    logger.info("")
    
    # Step 2: Start monitoring response topic in background
    tester = EndToEndTester()
    response_monitor_thread = threading.Thread(
        target=tester.monitor_response_topic,
        args=(120,),  # Monitor for 2 minutes
        daemon=True
    )
    response_monitor_thread.start()
    logger.info("✓ Started response topic monitor thread")
    logger.info("")
    
    # Step 3: Wait a bit for monitor to initialize
    time.sleep(2)
    
    # Step 4: Run producer (this will send messages)
    logger.info("Starting producer to send Oct 30th data...")
    producer_success = run_producer_test(date='2025-10-30', delay=5)
    logger.info("")
    
    if not producer_success:
        logger.error("✗ Producer failed. Cannot continue test.")
        sys.exit(1)
    
    # Step 5: Wait a bit for messages to be available
    logger.info("Waiting 5 seconds for messages to be available...")
    time.sleep(5)
    logger.info("")
    
    # Step 6: Run consumer (this will consume and generate predictions)
    logger.info("Starting consumer to process messages and generate predictions...")
    consumer_success = run_consumer_test(max_messages=30)
    logger.info("")
    
    # Step 7: Wait for monitor to finish
    logger.info("Waiting for response monitor to finish...")
    response_monitor_thread.join(timeout=10)
    logger.info("")
    
    # Step 8: Summary
    logger.info("=" * 60)
    logger.info("END-TO-END TEST SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Producer: {'✓ SUCCESS' if producer_success else '✗ FAILED'}")
    logger.info(f"Consumer: {'✓ SUCCESS' if consumer_success else '✗ FAILED'}")
    logger.info(f"Predictions Generated: {len(tester.predictions_received)}")
    logger.info("")
    
    if len(tester.predictions_received) > 0:
        logger.info("✓ PREDICTIONS RECEIVED:")
        for i, pred in enumerate(tester.predictions_received[:5], 1):  # Show first 5
            logger.info(f"  {i}. {pred.get('symbol')}: ${pred.get('predicted_close'):.2f} "
                       f"(target: {pred.get('target_timestamp')})")
        if len(tester.predictions_received) > 5:
            logger.info(f"  ... and {len(tester.predictions_received) - 5} more")
        logger.info("")
        logger.info("✓ END-TO-END PIPELINE IS WORKING!")
        sys.exit(0)
    else:
        logger.warning("⚠ No predictions were received. This could mean:")
        logger.warning("  - Consumer didn't process enough messages")
        logger.warning("  - Consumer didn't have enough historical data")
        logger.warning("  - Models failed to generate predictions")
        logger.warning("  - Response topic monitoring timed out")
        logger.info("")
        logger.info("⚠ END-TO-END TEST INCONCLUSIVE")
        sys.exit(1)

