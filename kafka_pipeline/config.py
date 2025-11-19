"""
Kafka Configuration for StockRecoAI
Using Azure Event Hubs with Kafka protocol
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Kafka Configuration
KAFKA_BROKER = os.getenv('KAFKA_BROKER', 'finsightai-eventhub.servicebus.windows.net:9093')
TOPIC_WATCH = os.getenv('TOPIC_WATCH', 'team05.watch')
TOPIC_NEWS = os.getenv('TOPIC_NEWS', 'team05.news')
TOPIC_RECO_REQUESTS = os.getenv('TOPIC_RECO_REQUESTS', 'team05.reco_requests')
TOPIC_RECO_RESPONSES = os.getenv('TOPIC_RECO_RESPONSES', 'team05.reco_responses')
SASL_USERNAME = os.getenv('KAFKA_USERNAME', '$ConnectionString')
SASL_PASSWORD = os.getenv('KAFKA_PASSWORD')
CONSUMER_GROUP = os.getenv('CONSUMER_GROUP', 'finsight-consumer-group')

# Azure Storage Configuration
# Support both naming conventions for compatibility
AZURE_STORAGE_CONNECTION_STRING = (os.getenv('STORAGE_CONNECTION') or 
                                   os.getenv('AZURE_STORAGE_CONNECTION_STRING') or '')
AZURE_STORAGE_CONTAINER_NAME = (os.getenv('AZURE_STORAGE_CONTAINER') or 
                                os.getenv('AZURE_STORAGE_CONTAINER_NAME') or 'snapshots')

# Alpha Vantage Configuration
ALPHA_VANTAGE_KEY = os.getenv('ALPHA_VANTAGE_KEY')

# Symbols to track
SYMBOLS = os.getenv('SYMBOLS', 'AAPL,MSFT,NVDA,META,TSLA,AMZN').split(',')

