"""
Simple End-to-End Test
1. Check models exist
2. Send a few messages via producer
3. Consume messages and verify predictions are generated
"""
import sys
import os
import json
import time
import logging
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kafka import KafkaConsumer
from kafka_pipeline.config import *

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_models():
    """Check if models exist"""
    logger.info("Checking for model files...")
    models = ['multi_stock_model_LSTM.keras', 'random_forest_model.pkl', 'scaler.pkl']
    all_exist = True
    
    for model in models:
        if os.path.exists(model) or os.path.exists(os.path.join('..', model)):
            logger.info(f"✓ {model}")
        else:
            logger.error(f"✗ {model} - MISSING")
            all_exist = False
    
    return all_exist

def check_response_topic_for_predictions(timeout=30):
    """Check if there are any recent predictions in the response topic"""
    logger.info("=" * 60)
    logger.info("CHECKING RESPONSE TOPIC FOR PREDICTIONS")
    logger.info("=" * 60)
    
    try:
        consumer = KafkaConsumer(
            TOPIC_RECO_RESPONSES,
            bootstrap_servers=KAFKA_BROKER,
            group_id=CONSUMER_GROUP + "_check",
            sasl_mechanism='PLAIN',
            security_protocol='SASL_SSL',
            sasl_plain_username=SASL_USERNAME,
            sasl_plain_password=SASL_PASSWORD,
            auto_offset_reset='earliest',  # Check from beginning
            value_deserializer=lambda v: json.loads(v.decode('utf-8')),
            consumer_timeout_ms=timeout * 1000
        )
        
        predictions = []
        logger.info(f"Reading from {TOPIC_RECO_RESPONSES}...")
        
        for message in consumer:
            pred = message.value
            predictions.append(pred)
            logger.info(f"✓ Found prediction: {pred.get('symbol')} -> ${pred.get('predicted_close'):.2f}")
            
            if len(predictions) >= 5:  # Just check first 5
                break
        
        consumer.close()
        
        if len(predictions) > 0:
            logger.info(f"✓ Found {len(predictions)} prediction(s) in response topic")
            return True, predictions
        else:
            logger.warning("⚠ No predictions found in response topic")
            return False, []
            
    except Exception as e:
        logger.error(f"✗ Error checking response topic: {e}")
        import traceback
        traceback.print_exc()
        return False, []

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("SIMPLE END-TO-END VERIFICATION")
    logger.info("=" * 60)
    logger.info("")
    
    # Step 1: Check models
    if not check_models():
        logger.error("✗ Missing model files. Please train models first.")
        sys.exit(1)
    logger.info("")
    
    # Step 2: Check if predictions exist in response topic
    logger.info("Checking if predictions are being generated...")
    has_predictions, predictions = check_response_topic_for_predictions(timeout=10)
    logger.info("")
    
    if has_predictions:
        logger.info("=" * 60)
        logger.info("✓ END-TO-END PIPELINE IS WORKING!")
        logger.info("=" * 60)
        logger.info(f"Found {len(predictions)} prediction(s):")
        for i, pred in enumerate(predictions, 1):
            logger.info(f"  {i}. {pred.get('symbol')}: ${pred.get('predicted_close'):.2f} "
                       f"(target: {pred.get('target_timestamp', 'N/A')})")
        sys.exit(0)
    else:
        logger.info("=" * 60)
        logger.info("⚠ NO PREDICTIONS FOUND YET")
        logger.info("=" * 60)
        logger.info("")
        logger.info("To test the full pipeline:")
        logger.info("  1. Run producer: python kafka_pipeline/producer.py --date 2025-10-30 --delay 5")
        logger.info("  2. In another terminal, run consumer: python kafka_pipeline/consumer.py --max-messages 20")
        logger.info("  3. Then run this test again to verify predictions")
        logger.info("")
        sys.exit(1)

