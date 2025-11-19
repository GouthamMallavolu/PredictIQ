"""
Online Evaluation for Stock Prediction API
Computes KPIs from Kafka logs (team05.reco_responses)
"""
import json
import pandas as pd
from datetime import datetime, timedelta
from kafka import KafkaConsumer
from kafka_pipeline.config import *
import os
from dotenv import load_dotenv

load_dotenv()

def create_kafka_consumer():
    """Create Kafka consumer for reco_responses topic"""
    consumer = KafkaConsumer(
        TOPIC_RECO_RESPONSES,
        bootstrap_servers=[KAFKA_BROKER],
        security_protocol='SASL_SSL',
        sasl_mechanism='PLAIN',
        sasl_plain_username=SASL_USERNAME,
        sasl_plain_password=SASL_PASSWORD,
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        consumer_timeout_ms=10000,  # 10 second timeout
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        group_id='online_eval_consumer'
    )
    return consumer

def fetch_recent_responses(hours=24, use_historical=False, historical_date_range=None):
    """
    Fetch recent responses from Kafka
    
    Args:
        hours: Number of hours to look back (ignored if use_historical=True)
        use_historical: If True, fetch historical data from Nov 1-7, 2024
        historical_date_range: Tuple of (start_date, end_date) for historical data
    
    Returns:
        List of response records
    """
    consumer = create_kafka_consumer()
    responses = []
    
    if use_historical:
        # Use historical date range (Nov 1-7, 2024)
        if historical_date_range:
            start_date, end_date = historical_date_range
        else:
            start_date = datetime(2024, 11, 1)
            end_date = datetime(2024, 11, 7, 23, 59, 59)
        
        print(f"Fetching historical responses from {start_date.date()} to {end_date.date()}...")
        cutoff_time = start_date
        end_time = end_date
    else:
        cutoff_time = datetime.now() - timedelta(hours=hours)
        end_time = datetime.now()
        print(f"Fetching responses from last {hours} hours...")
    
    try:
        for message in consumer:
            record = message.value
            record['kafka_timestamp'] = datetime.fromtimestamp(message.timestamp / 1000)
            
            # Filter by timestamp if available
            if 'timestamp' in record:
                try:
                    record_time = pd.to_datetime(record['timestamp'])
                    if use_historical:
                        # For historical data, check if timestamp is in range
                        if cutoff_time <= record_time <= end_time:
                            responses.append(record)
                    else:
                        # For recent data, check if timestamp is after cutoff
                        if record_time >= cutoff_time:
                            responses.append(record)
                except:
                    # Include if timestamp parsing fails (for backward compatibility)
                    if not use_historical:
                        responses.append(record)
            else:
                # No timestamp - include only if not using historical filter
                if not use_historical:
                    responses.append(record)
            
            if len(responses) >= 1000:  # Limit to prevent memory issues
                break
    except Exception as e:
        print(f"Error consuming messages: {e}")
    finally:
        consumer.close()
    
    print(f"Fetched {len(responses)} responses")
    return responses

def define_proxy_success(response_record, latency_threshold_ms=500):
    """
    Define proxy success metrics for online evaluation
    
    Proxy success definitions:
    1. Low latency: Response time < threshold
    2. Valid predictions: Has predictions for requested symbols
    3. No errors: Status is 'success'
    4. Reasonable predictions: Predictions are within reasonable range
    
    Args:
        response_record: Single response record from Kafka
        latency_threshold_ms: Maximum acceptable latency in ms
    
    Returns:
        dict with success flags and metrics
    """
    success_metrics = {
        'low_latency': False,
        'valid_predictions': False,
        'no_errors': False,
        'reasonable_predictions': False,
        'overall_success': False
    }
    
    # Check latency
    latency = response_record.get('latency_ms', float('inf'))
    success_metrics['low_latency'] = latency < latency_threshold_ms
    
    # Check status
    status = response_record.get('status', 'error')
    success_metrics['no_errors'] = status == 'success'
    
    # Check if predictions exist
    response_data = response_record.get('response', {})
    results = response_data.get('results', {})
    success_metrics['valid_predictions'] = len(results) > 0
    
    # Check if predictions are reasonable (not null, not extreme)
    if success_metrics['valid_predictions']:
        all_reasonable = True
        for symbol, pred_data in results.items():
            if 'error' in pred_data:
                all_reasonable = False
                break
            predictions = pred_data.get('predictions', {})
            current_price = pred_data.get('current_price', 0)
            
            if current_price <= 0:
                all_reasonable = False
                break
            
            for model_name, pred_price in predictions.items():
                # Check if prediction is within reasonable range (0.1x to 10x current price)
                if pred_price <= 0 or pred_price > current_price * 10 or pred_price < current_price * 0.1:
                    all_reasonable = False
                    break
        
        success_metrics['reasonable_predictions'] = all_reasonable
    
    # Overall success: all conditions met
    success_metrics['overall_success'] = (
        success_metrics['low_latency'] and
        success_metrics['valid_predictions'] and
        success_metrics['no_errors'] and
        success_metrics['reasonable_predictions']
    )
    
    return success_metrics

def compute_online_kpis(responses):
    """
    Compute online KPIs from response records
    
    Args:
        responses: List of response records
    
    Returns:
        dict with KPI metrics
    """
    if len(responses) == 0:
        return {
            'total_requests': 0,
            'success_rate': 0.0,
            'avg_latency_ms': 0.0,
            'p95_latency_ms': 0.0,
            'p99_latency_ms': 0.0,
            'error_rate': 0.0,
            'low_latency_rate': 0.0,
            'valid_predictions_rate': 0.0,
            'reasonable_predictions_rate': 0.0
        }
    
    df = pd.DataFrame(responses)
    
    # Basic metrics
    total_requests = len(df)
    success_count = df[df['status'] == 'success'].shape[0]
    success_rate = success_count / total_requests if total_requests > 0 else 0.0
    error_rate = 1.0 - success_rate
    
    # Latency metrics
    latencies = df['latency_ms'].dropna()
    avg_latency = latencies.mean() if len(latencies) > 0 else 0.0
    p95_latency = latencies.quantile(0.95) if len(latencies) > 0 else 0.0
    p99_latency = latencies.quantile(0.99) if len(latencies) > 0 else 0.0
    
    # Proxy success metrics
    proxy_successes = []
    for _, row in df.iterrows():
        proxy = define_proxy_success(row.to_dict())
        proxy_successes.append(proxy)
    
    proxy_df = pd.DataFrame(proxy_successes)
    low_latency_rate = proxy_df['low_latency'].mean() if len(proxy_df) > 0 else 0.0
    valid_predictions_rate = proxy_df['valid_predictions'].mean() if len(proxy_df) > 0 else 0.0
    reasonable_predictions_rate = proxy_df['reasonable_predictions'].mean() if len(proxy_df) > 0 else 0.0
    
    kpis = {
        'total_requests': total_requests,
        'success_rate': success_rate,
        'error_rate': error_rate,
        'avg_latency_ms': avg_latency,
        'p95_latency_ms': p95_latency,
        'p99_latency_ms': p99_latency,
        'low_latency_rate': low_latency_rate,
        'valid_predictions_rate': valid_predictions_rate,
        'reasonable_predictions_rate': reasonable_predictions_rate,
        'overall_success_rate': proxy_df['overall_success'].mean() if len(proxy_df) > 0 else 0.0
    }
    
    return kpis

def evaluate_online(hours=24, use_historical=False, historical_date_range=None):
    """
    Complete online evaluation pipeline
    
    Args:
        hours: Number of hours to look back (ignored if use_historical=True)
        use_historical: If True, evaluate historical data from Nov 1-7, 2024
        historical_date_range: Tuple of (start_date, end_date) for historical data
    
    Returns:
        dict with evaluation results
    """
    if use_historical:
        if historical_date_range:
            start_date, end_date = historical_date_range
        else:
            start_date = datetime(2024, 11, 1)
            end_date = datetime(2024, 11, 7, 23, 59, 59)
        print(f"\n{'='*60}")
        print(f"Online Evaluation (Historical: {start_date.date()} to {end_date.date()})")
        print(f"{'='*60}")
    else:
        print(f"\n{'='*60}")
        print(f"Online Evaluation (last {hours} hours)")
        print(f"{'='*60}")
    
    # Fetch responses from Kafka
    responses = fetch_recent_responses(
        hours=hours, 
        use_historical=use_historical,
        historical_date_range=historical_date_range
    )
    
    if len(responses) == 0:
        if use_historical:
            print(f"No responses found for historical date range {start_date.date()} to {end_date.date()}")
            print("Note: Make sure probe script has been run to generate historical data")
        else:
            print(f"No responses found in the last {hours} hours")
            print("Note: Try using use_historical=True to evaluate historical probe data (Nov 1-7, 2024)")
        return {}
    
    # Compute KPIs
    kpis = compute_online_kpis(responses)
    
    print(f"\nOnline KPIs:")
    print(f"  Total Requests: {kpis['total_requests']}")
    print(f"  Success Rate: {kpis['success_rate']:.2%}")
    print(f"  Error Rate: {kpis['error_rate']:.2%}")
    print(f"  Avg Latency: {kpis['avg_latency_ms']:.2f} ms")
    print(f"  P95 Latency: {kpis['p95_latency_ms']:.2f} ms")
    print(f"  P99 Latency: {kpis['p99_latency_ms']:.2f} ms")
    print(f"\nProxy Success Metrics:")
    print(f"  Low Latency Rate: {kpis['low_latency_rate']:.2%}")
    print(f"  Valid Predictions Rate: {kpis['valid_predictions_rate']:.2%}")
    print(f"  Reasonable Predictions Rate: {kpis['reasonable_predictions_rate']:.2%}")
    print(f"  Overall Success Rate: {kpis['overall_success_rate']:.2%}")
    
    return kpis

if __name__ == "__main__":
    # Run online evaluation
    # Since we don't have data for today, use historical data from Nov 1-7, 2024
    print("Note: Using historical data mode (Nov 1-7, 2024)")
    print("This matches the probe script's historical data generation")
    print()
    
    results = evaluate_online(use_historical=True)
    
    if not results:
        print("\nNo historical data found. Make sure to:")
        print("1. Run the probe script to generate historical data:")
        print("   python scripts/probe.py")
        print("2. Or wait for the GitHub Actions workflow to run")
        print("3. Then run this evaluation script again")
    
    print(f"\nEvaluation complete!")

