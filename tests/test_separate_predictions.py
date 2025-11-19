"""
Test script to verify separate model predictions are being sent
"""
import sys
import os
import json
import logging
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kafka import KafkaConsumer
from kafka_pipeline.config import *

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_separate_predictions():
    """Check if separate predictions for each model are in the response topic"""
    logger.info("=" * 60)
    logger.info("CHECKING FOR SEPARATE MODEL PREDICTIONS")
    logger.info("=" * 60)
    
    try:
        consumer = KafkaConsumer(
            TOPIC_RECO_RESPONSES,
            bootstrap_servers=KAFKA_BROKER,
            group_id=CONSUMER_GROUP + "_prediction_check",
            sasl_mechanism='PLAIN',
            security_protocol='SASL_SSL',
            sasl_plain_username=SASL_USERNAME,
            sasl_plain_password=SASL_PASSWORD,
            auto_offset_reset='earliest',
            value_deserializer=lambda v: json.loads(v.decode('utf-8')),
            consumer_timeout_ms=10000
        )
        
        logger.info(f"Reading from {TOPIC_RECO_RESPONSES}...")
        
        predictions_by_model = {}
        predictions_by_symbol = {}
        
        for message in consumer:
            pred = message.value
            model = pred.get('model_version', 'unknown')
            symbol = pred.get('symbol', 'unknown')
            
            if model not in predictions_by_model:
                predictions_by_model[model] = []
            predictions_by_model[model].append(pred)
            
            if symbol not in predictions_by_symbol:
                predictions_by_symbol[symbol] = {}
            if model not in predictions_by_symbol[symbol]:
                predictions_by_symbol[symbol][model] = []
            predictions_by_symbol[symbol][model].append(pred)
            
            logger.info(f"Found: {symbol} | {model} | ${pred.get('predicted_close'):.2f} | target: {pred.get('target_timestamp')}")
            
            # Check first 15 messages
            total = sum(len(preds) for preds in predictions_by_model.values())
            if total >= 15:
                break
        
        consumer.close()
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("PREDICTION SUMMARY BY MODEL")
        logger.info("=" * 60)
        for model, preds in predictions_by_model.items():
            logger.info(f"{model}: {len(preds)} prediction(s)")
            if preds:
                logger.info(f"  Sample: {preds[0].get('symbol')} -> ${preds[0].get('predicted_close'):.2f}")
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("PREDICTION SUMMARY BY SYMBOL")
        logger.info("=" * 60)
        for symbol, models in predictions_by_symbol.items():
            logger.info(f"{symbol}:")
            for model, preds in models.items():
                logger.info(f"  {model}: {len(preds)} prediction(s)")
        
        # Verify we have separate predictions
        expected_models = ['LSTM', 'RandomForest', 'MovingAverage']
        found_models = set(predictions_by_model.keys())
        
        logger.info("")
        logger.info("=" * 60)
        if all(model in found_models for model in expected_models):
            logger.info("✓ SUCCESS: Separate predictions found for all models!")
            logger.info(f"  Found models: {sorted(found_models)}")
            return True
        else:
            logger.warning("⚠ Some models missing:")
            logger.warning(f"  Expected: {expected_models}")
            logger.warning(f"  Found: {sorted(found_models)}")
            return False
            
    except Exception as e:
        logger.error(f"Error checking predictions: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = check_separate_predictions()
    sys.exit(0 if success else 1)

