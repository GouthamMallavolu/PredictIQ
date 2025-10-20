"""
Kafka Configuration for StockRecoAI
Using Azure Event Hubs with Kafka protocol
"""

# Kafka Broker (Event Hubs with Kafka endpoint)
KAFKA_BROKER = "finsightai-team05-ns.servicebus.windows.net:9093"
SASL_USERNAME = "$ConnectionString"
SASL_PASSWORD = "Endpoint=sb://finsightai-team05-ns.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=L4U4Hm6TRih6qVQNmu4LKKBye8IR7YR/S+AEhMpiNPQ="

# Topics (team05 = your team name)
TOPIC_WATCH = "team05.watch"              # Real-time stock price + news stream (from Alpha Vantage)
TOPIC_RATE = "team05.rate"                # Price change events (hourly deltas, volatility signals)
TOPIC_PREDICT_REQUESTS = "team05.predict_requests"   # Prediction requests (which stocks to predict)
TOPIC_PREDICT_RESPONSES = "team05.predict_responses" # Prediction results (predicted prices)

# Stock symbols
SYMBOLS = ["AAPL", "MSFT", "AMZN", "NVDA", "META", "TSLA", "TSM"]

# Azure Storage for snapshots
STORAGE_CONNECTION = "DefaultEndpointsProtocol=https;EndpointSuffix=core.windows.net;AccountName=finsightaistorage2025;AccountKey=qzHme6Agnw39GpQcwqX1RJHjI8OYU30ScHmkxSvqAixm3JHxZEs/p9eRCoFoqpvlNguk62NOJNO++AStHUDs5w=="
STORAGE_CONTAINER = "snapshots"

# Consumer group
CONSUMER_GROUP = "stock-ingestor"

