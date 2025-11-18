"""
Probing Script for StockRecoAI API
Periodically tests the API and writes requests/responses to Kafka

This is Task 5: Probing pipeline
Processes historical data from Nov 1-7, 2024
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))    

import requests
import json
from datetime import datetime, timedelta
from kafka import KafkaProducer
from kafka_pipeline.config import *
import time
import logging

# Setup error logging
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
os.makedirs(log_dir, exist_ok=True)

error_log_file = os.path.join(log_dir, f'probe_errors_{datetime.now().strftime("%Y%m%d")}.log')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(error_log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# API URL (update after deployment)
API_URL = os.getenv("API_URL", "http://localhost:8000")

def create_kafka_producer():
    """Create Kafka producer for reco topics"""
    logger.info(f"Connecting to Kafka broker: {KAFKA_BROKER}")
    logger.info(f"Using username: {SASL_USERNAME}")
    logger.info(f"Password configured: {'Yes' if SASL_PASSWORD else 'No'}")
    
    try:
        producer = KafkaProducer(
            bootstrap_servers=[KAFKA_BROKER],
            security_protocol='SASL_SSL',
            sasl_mechanism='PLAIN',
            sasl_plain_username=SASL_USERNAME,
            sasl_plain_password=SASL_PASSWORD,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            api_version=(0, 10, 1),
            request_timeout_ms=60000,  # 60 seconds
            connections_max_idle_ms=120000,  # 120 seconds
            max_block_ms=60000,  # 60 seconds
            metadata_max_age_ms=300000,  # 5 minutes - cache metadata longer
            retry_backoff_ms=1000,  # Retry backoff
            max_in_flight_requests_per_connection=5,
            enable_idempotence=False  # Disable idempotence for better compatibility
        )
        # Pre-fetch metadata for topics to avoid blocking during send
        logger.info("Pre-fetching Kafka topic metadata...")
        try:
            # Get metadata with longer timeout
            metadata = producer.list_topics(timeout=20)
            logger.info(f"Found {len(metadata)} topics")
            # Check if our topics exist
            topics = [topic for topic in metadata]
            if TOPIC_RECO_REQUESTS in topics:
                logger.info(f"Topic {TOPIC_RECO_REQUESTS} exists")
            else:
                logger.warning(f"Topic {TOPIC_RECO_REQUESTS} not found - may need to be created")
            if TOPIC_RECO_RESPONSES in topics:
                logger.info(f"Topic {TOPIC_RECO_RESPONSES} exists")
            else:
                logger.warning(f"Topic {TOPIC_RECO_RESPONSES} not found - may need to be created")
        except Exception as meta_error:
            logger.warning(f"Metadata pre-fetch failed: {meta_error}")
            logger.warning("Will attempt to send anyway - topics may be auto-created")
        logger.info("Kafka producer created successfully")
        return producer
    except Exception as e:
        logger.error(f"Failed to create Kafka producer: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        raise

def probe_api_for_datetime(target_datetime, producer):
    """
    Send probe request to API for a specific datetime and log to Kafka
    Creates probe records with the target timestamp
    """
    # Format timestamp for probe ID
    probe_id = f"probe_{target_datetime.strftime('%Y%m%d_%H%M%S')}"

    # Create probe request
    request_payload = {
        "user_id": probe_id,
        "symbols": ["AAPL", "MSFT", "NVDA"],
        "model": "lstm"
    }

    logger.info(f"Sending probe request: {probe_id} for {target_datetime.strftime('%Y-%m-%d %H:%M:%S UTC')}")

    try:
        # Log request to Kafka (non-blocking, with timeout handling)
        try:
            # Use send with explicit timeout
            future = producer.send(TOPIC_RECO_REQUESTS, request_payload)
            # Don't wait for completion - just queue it
            logger.info("Request queued to Kafka (async)")
        except Exception as kafka_error:
            logger.error(f"Failed to queue request to Kafka: {kafka_error}")
            logger.error(f"Error type: {type(kafka_error).__name__}")
            # If it's a timeout, try to continue anyway - metadata might be cached
            if "Timeout" in str(type(kafka_error).__name__):
                logger.warning("Kafka timeout - continuing with API call, will retry Kafka later")
            else:
                raise  # Fail if Kafka is completely broken

        # Call API (reduced timeout for faster processing)
        start_time = datetime.now()
        logger.info(f"Calling API: {API_URL}/recommend with symbols {request_payload['symbols']}")
        
        try:
            response = requests.post(
                f"{API_URL}/recommend",
                json=request_payload,
                timeout=5  # Reduced from 10 to 5 seconds
            )
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            logger.info(f"API response received: status={response.status_code}, latency={latency_ms:.2f}ms")
        except requests.exceptions.Timeout as timeout_error:
            logger.error(f"API timeout after 5 seconds: {timeout_error}")
            logger.error(f"Request payload: {json.dumps(request_payload, indent=2)}")
            raise
        except requests.exceptions.ConnectionError as conn_error:
            logger.error(f"API connection error: {conn_error}")
            logger.error(f"API URL: {API_URL}")
            raise
        except requests.exceptions.RequestException as req_error:
            logger.error(f"API request error: {req_error}")
            logger.error(f"Error type: {type(req_error).__name__}")
            raise
        
        if response.status_code == 200:
            try:
                result = response.json()
                logger.info("Successfully parsed API response JSON")
            except json.JSONDecodeError as json_error:
                logger.error(f"Failed to parse API response as JSON: {json_error}")
                logger.error(f"Response content: {response.text[:500]}")
                raise

            # Log response to Kafka with historical timestamp
            response_payload = {
                "request_id": probe_id,
                "response": result,
                "latency_ms": latency_ms,
                "timestamp": target_datetime.isoformat(),  # Use historical timestamp
                "num_predictions": len(result.get("results", {})),
                "status": "success"
            }

            try:
                producer.send(TOPIC_RECO_RESPONSES, response_payload)
                logger.info("Response queued to Kafka")
            except Exception as kafka_error:
                logger.error(f"Failed to queue response to Kafka: {kafka_error}")
                raise  # Fail if Kafka is broken

            logger.info(f"Probe successful: latency={latency_ms:.2f}ms, results={len(result.get('results', {}))}, model={result.get('model_used')}")
            print(f"Probe successful:")
            print(f"   Latency: {latency_ms:.2f}ms")
            print(f"   Results: {len(result.get('results', {}))}")
            print(f"   Model used: {result.get('model_used')}")
            
            # Show predicted prices
            results = result.get('results', {})
            for symbol, pred_data in list(results.items())[:3]:
                if 'error' not in pred_data:
                    preds = pred_data.get('predictions', {})
                    current = pred_data.get('current_price', 0)
                    # Show first available prediction
                    if preds:
                        model_name = list(preds.keys())[0]
                        predicted = preds[model_name]
                        change_pct = ((predicted - current) / current * 100) if current > 0 else 0
                        print(f"   {symbol}: ${current:.2f} -> ${predicted:.2f} ({change_pct:+.2f}%) [{model_name}]")
                else:
                    print(f"   {symbol}: Error - {pred_data.get('error')}")
            
            return response_payload
        else:
            logger.error(f"API returned error status: {response.status_code}")
            logger.error(f"Response content: {response.text[:500]}")
            
            # Check for specific error codes
            if response.status_code == 429:
                logger.error("Rate limit exceeded (429) - API is throttling requests")
            elif response.status_code == 503:
                logger.error("Service unavailable (503) - API may be down or overloaded")
            elif response.status_code == 500:
                logger.error("Internal server error (500) - API encountered an error")
            elif response.status_code == 401 or response.status_code == 403:
                logger.error(f"Authentication/Authorization error ({response.status_code})")
            
            print(f"API error: {response.status_code}")
            error_payload = {
                "request_id": probe_id,
                "error": response.text,
                "status_code": response.status_code,
                "timestamp": target_datetime.isoformat(),
                "status": "error"
            }
            try:
                producer.send(TOPIC_RECO_RESPONSES, error_payload)
                logger.info("Error logged to Kafka")
            except Exception as kafka_error:
                logger.error(f"Failed to queue error to Kafka: {kafka_error}")
            return error_payload

    except Exception as e:
        logger.error(f"Probe failed with exception: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Request details: probe_id={probe_id}, target_time={target_datetime}")
        
        print(f"Probe failed: {e}")
        error_payload = {
            "request_id": probe_id,
            "error": str(e),
            "error_type": type(e).__name__,
            "timestamp": target_datetime.isoformat(),
            "status": "error"
        }
        try:
            producer.send(TOPIC_RECO_RESPONSES, error_payload)
            logger.info("Exception logged to Kafka")
        except Exception as kafka_error:
            logger.error(f"Failed to queue error to Kafka: {kafka_error}")
        return error_payload
    finally:
        pass  # Don't flush/close here - will be done after all probes

def get_market_hours_utc(date):
    """
    Get market hours in UTC for a given date
    Market hours: 9:30 AM - 4:00 PM ET
    For Nov 2024, EST is UTC-5, so:
    - 9:30 AM ET = 14:30 UTC
    - 4:00 PM ET = 21:00 UTC
    Reduced to 2 probes per day (market open and close) for faster processing
    """
    # Start: 9:30 AM ET = 14:30 UTC (market open)
    # End: 4:00 PM ET = 21:00 UTC (market close)
    # Only 2 probes: market open and market close
    
    hours = []
    # Market open
    hours.append(date.replace(hour=14, minute=30, second=0, microsecond=0))
    # Market close
    hours.append(date.replace(hour=21, minute=0, second=0, microsecond=0))
    
    return hours

def is_trading_day(date):
    """Check if date is a trading day (Monday-Friday)"""
    return date.weekday() < 5  # 0-4 = Monday-Friday

def probe_nov1_7():
    """
    Process probes for Nov 1-7, 2024
    Only trading days (Nov 1, 4, 5, 6, 7)
    During market hours with 1-hour gaps
    """
    logger.info("="*60)
    logger.info("Starting Probe Processing for Nov 1-7, 2024")
    logger.info(f"Error log file: {error_log_file}")
    logger.info("="*60)
    
    print("Starting Probe Processing for Nov 1-7, 2024")
    print("=" * 60)
    print(f"Error log: {error_log_file}")
    print("=" * 60)

    producer = create_kafka_producer()

    # Define date range: Nov 1-7, 2024
    start_date = datetime(2024, 11, 1)
    end_date = datetime(2024, 11, 7)

    total_probes = 0
    successful_probes = 0

    current_date = start_date
    while current_date <= end_date:
        if is_trading_day(current_date):
            print(f"\n{current_date.strftime('%A, %B %d, %Y')} (Trading Day)")
            market_hours = get_market_hours_utc(current_date)

            for probe_time in market_hours:
                try:
                    probe_api_for_datetime(probe_time, producer)
                    total_probes += 1
                    successful_probes += 1
                    print(f"  [OK] Probe completed")
                except Exception as e:
                    total_probes += 1
                    print(f"  [ERROR] Probe failed: {e}")

                # Small delay between probes (reduced for faster processing)
                time.sleep(0.1)
        else:
            print(f"\n{current_date.strftime('%A, %B %d, %Y')} (Non-Trading Day - Skipped)")

        current_date += timedelta(days=1)

    # Flush producer after all probes
    try:
        producer.flush(timeout=30)
        logger.info("All Kafka messages flushed")
        print("\n[OK] All Kafka messages flushed")
    except Exception as e:
        logger.warning(f"Failed to flush Kafka producer: {e}")
        print(f"\n[WARN] Failed to flush Kafka producer: {e}")
    try:
        producer.close(timeout=10)
        logger.info("Kafka producer closed")
        print("[OK] Kafka producer closed")
    except Exception as e:
        logger.warning(f"Failed to close Kafka producer: {e}")
        print(f"[WARN] Failed to close Kafka producer: {e}")

    logger.info("="*60)
    logger.info("Probe Processing Complete!")
    logger.info(f"Total probes: {total_probes}")
    logger.info(f"Successful: {successful_probes}")
    logger.info(f"Failed: {total_probes - successful_probes}")
    logger.info(f"Error log saved to: {error_log_file}")
    logger.info("="*60)

    print("\n" + "=" * 60)
    print(f"Probe Processing Complete!")
    print(f"   Total probes: {total_probes}")
    print(f"   Successful: {successful_probes}")
    print(f"   Failed: {total_probes - successful_probes}")
    print(f"\nProbe records written to:")
    print(f"   - {TOPIC_RECO_REQUESTS}")
    print(f"   - {TOPIC_RECO_RESPONSES}")
    print(f"\nError log: {error_log_file}")
    print(f"Note: Timestamps are set to Nov 1-7, 2024 for historical data")

def probe_single():
    """
    Run a single probe for current time
    Use this for continuous monitoring (GitHub Actions hourly probes)
    """
    logger.info("="*60)
    logger.info("Running Single Probe (Current Time)")
    logger.info(f"Error log file: {error_log_file}")
    logger.info("="*60)
    
    print("Running Single Probe (Current Time)")
    print("=" * 60)
    print(f"Error log: {error_log_file}")
    print("=" * 60)
    
    producer = create_kafka_producer()
    
    # Use current time for the probe
    current_time = datetime.now()
    
    try:
        probe_api_for_datetime(current_time, producer)
        logger.info("Single probe completed successfully")
        print("\n[OK] Single probe completed successfully")
    except Exception as e:
        logger.error(f"Single probe failed: {e}")
        print(f"\n[ERROR] Single probe failed: {e}")
    finally:
        # Flush producer
        try:
            producer.flush(timeout=10)
            logger.info("Kafka messages flushed")
        except Exception as e:
            logger.warning(f"Failed to flush Kafka producer: {e}")
        try:
            producer.close(timeout=5)
            logger.info("Kafka producer closed")
        except Exception as e:
            logger.warning(f"Failed to close Kafka producer: {e}")
    
    logger.info("="*60)
    logger.info(f"Error log saved to: {error_log_file}")
    logger.info("="*60)
    
    print("\n" + "=" * 60)
    print(f"Error log: {error_log_file}")
    print("=" * 60)

if __name__ == "__main__":
    import sys
    
    # Check if we should run single probe or historical batch
    if len(sys.argv) > 1 and sys.argv[1] == "--single":
        # Single probe mode (for GitHub Actions)
        probe_single()
    elif len(sys.argv) > 1 and sys.argv[1] == "--historical":
        # Historical batch mode (for initial data generation)
        probe_nov1_7()
    else:
        # Default: show usage
        print("Usage:")
        print("  python scripts/probe.py --single       # Run single probe (for continuous monitoring)")
        print("  python scripts/probe.py --historical   # Generate historical data (Nov 1-7)")
        print("\nFor GitHub Actions hourly probes, use --single")
        print("For initial data generation, use --historical")

