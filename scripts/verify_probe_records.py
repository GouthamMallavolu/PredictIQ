"""
Verify Probe Records in Kafka
Check that probe records exist in team05.reco_requests and team05.reco_responses
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from datetime import datetime, timedelta
from kafka import KafkaConsumer
from kafka_pipeline.config import *

def verify_probe_records(hours=24):
    """
    Verify probe records exist in Kafka topics
    
    Args:
        hours: Number of hours to look back
    """
    print("Verifying Probe Records in Kafka")
    print("=" * 60)
    
    # Consumer for requests
    requests_consumer = KafkaConsumer(
        TOPIC_RECO_REQUESTS,
        bootstrap_servers=KAFKA_BROKER,
        security_protocol='SASL_SSL',
        sasl_mechanism='PLAIN',
        sasl_plain_username=SASL_USERNAME,
        sasl_plain_password=SASL_PASSWORD,
        value_deserializer=lambda v: json.loads(v.decode('utf-8')),
        auto_offset_reset='earliest',
        consumer_timeout_ms=10000
    )
    
    # Consumer for responses
    responses_consumer = KafkaConsumer(
        TOPIC_RECO_RESPONSES,
        bootstrap_servers=KAFKA_BROKER,
        security_protocol='SASL_SSL',
        sasl_mechanism='PLAIN',
        sasl_plain_username=SASL_USERNAME,
        sasl_plain_password=SASL_PASSWORD,
        value_deserializer=lambda v: json.loads(v.decode('utf-8')),
        auto_offset_reset='earliest',
        consumer_timeout_ms=10000
    )
    
    cutoff_time = datetime.now() - timedelta(hours=hours)
    
    # Read requests
    print(f"\nReading from {TOPIC_RECO_REQUESTS}...")
    requests = []
    for message in requests_consumer:
        record = message.value
        ts_str = record.get('timestamp', record.get('user_id', ''))
        # Try to parse timestamp from probe_id if timestamp not present
        if 'timestamp' not in record and 'probe_' in ts_str:
            try:
                # Extract datetime from probe_YYYYMMDD_HHMMSS format
                dt_str = ts_str.split('probe_')[1] if 'probe_' in ts_str else ''
                if dt_str:
                    ts = datetime.strptime(dt_str, '%Y%m%d_%H%M%S')
                    if ts >= cutoff_time:
                        requests.append(record)
            except:
                requests.append(record)
        else:
            requests.append(record)
    
    requests_consumer.close()
    
    # Read responses
    print(f"Reading from {TOPIC_RECO_RESPONSES}...")
    responses = []
    for message in responses_consumer:
        record = message.value
        ts_str = record.get('timestamp', '')
        if ts_str:
            try:
                ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                if ts.replace(tzinfo=None) >= cutoff_time:
                    responses.append(record)
            except:
                # If timestamp parsing fails, include it anyway
                responses.append(record)
        else:
            responses.append(record)
    
    responses_consumer.close()
    
    # Analysis
    print("\n" + "=" * 60)
    print("PROBE RECORDS SUMMARY")
    print("=" * 60)
    
    print(f"\nRequests ({TOPIC_RECO_REQUESTS}):")
    print(f"   Total records: {len(requests)}")
    if requests:
        print(f"   Sample request IDs:")
        for req in requests[:5]:
            print(f"     - {req.get('user_id', 'N/A')}")
    
    print(f"\nResponses ({TOPIC_RECO_RESPONSES}):")
    print(f"   Total records: {len(responses)}")
    
    if responses:
        successful = [r for r in responses if r.get('status') == 'success']
        errors = [r for r in responses if r.get('status') == 'error']
        
        print(f"   Successful: {len(successful)}")
        print(f"   Errors: {len(errors)}")
        
        if successful:
            latencies = [r.get('latency_ms', 0) for r in successful if 'latency_ms' in r]
            if latencies:
                print(f"   Avg latency: {sum(latencies)/len(latencies):.2f}ms")
                print(f"   Min latency: {min(latencies):.2f}ms")
                print(f"   Max latency: {max(latencies):.2f}ms")
        
        # Check for simulated records
        simulated = [r for r in responses if r.get('simulated')]
        if simulated:
            print(f"\n   [WARN] Simulated records: {len(simulated)}")
        
        print(f"\n   Sample response IDs:")
        for resp in responses[:5]:
            print(f"     - {resp.get('request_id', 'N/A')} ({resp.get('status', 'N/A')})")
    
    # Date range analysis
    if responses:
        timestamps = []
        for resp in responses:
            ts_str = resp.get('timestamp', '')
            if ts_str:
                try:
                    ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                    timestamps.append(ts.replace(tzinfo=None))
                except:
                    pass
        
        if timestamps:
            print(f"\nDate Range:")
            print(f"   Earliest: {min(timestamps)}")
            print(f"   Latest: {max(timestamps)}")
            print(f"   Span: {(max(timestamps) - min(timestamps)).total_seconds() / 3600:.1f} hours")
    
    print("\n" + "=" * 60)
    
    if len(requests) > 0 and len(responses) > 0:
        print("[OK] Probe records verified successfully!")
        return True
    else:
        print("[WARN] No probe records found. Run probe simulation first.")
        return False

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--hours', type=int, default=168, help='Hours to look back (default: 168 = 7 days)')
    args = parser.parse_args()
    
    verify_probe_records(hours=args.hours)

