"""
Kafka Configuration for StockRecoAI
Using Azure Event Hubs with Kafka protocol
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Kafka Broker (Event Hubs with Kafka endpoint)
KAFKA_BROKER = os.getenv("KAFKA_BROKER")
SASL_USERNAME = os.getenv("KAFKA_USERNAME")
SASL_PASSWORD = os.getenv("KAFKA_PASSWORD")

# Topics
TOPIC_WATCH = os.getenv("TOPIC_WATCH")
TOPIC_RATE = os.getenv("TOPIC_RATE")
TOPIC_PREDICT_REQUESTS = os.getenv("TOPIC_PREDICT_REQUESTS")
TOPIC_PREDICT_RESPONSES = os.getenv("TOPIC_PREDICT_RESPONSES")

# Stock symbols
SYMBOLS = os.getenv("SYMBOLS")

# Azure Storage for snapshots
STORAGE_CONNECTION = os.getenv("STORAGE_CONNECTION")
STORAGE_CONTAINER = os.getenv("STORAGE_CONTAINER")

# Consumer group
CONSUMER_GROUP = os.getenv("CONSUMER_GROUP")

