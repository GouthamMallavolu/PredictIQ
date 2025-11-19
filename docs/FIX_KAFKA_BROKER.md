# Fix Kafka Broker Configuration

## Issue

The `KAFKA_BROKER` GitHub secret is currently pointing to the **Container App** endpoint instead of **Azure Event Hubs**:

```
❌ WRONG: finsightai-api.orangegrass-19668bba.eastus.azurecontainerapps.io:9092
```

This causes probe scripts to fail with:
```
KafkaTimeoutError: Failed to update metadata after 60.0 secs.
```

## Solution

Update the `KAFKA_BROKER` GitHub secret to point to your **Azure Event Hubs** namespace.

### Steps

1. **Find your Event Hubs namespace**
   - Go to Azure Portal
   - Navigate to your Event Hubs Namespace
   - Copy the namespace name (e.g., `team05-kafka`)

2. **Update GitHub Secret**
   - Go to: https://github.com/GouthamMallavolu/PredictIQ/settings/secrets/actions
   - Click **KAFKA_BROKER** secret
   - Click **Update**
   - Set value to:
     ```
     <your-namespace>.servicebus.windows.net:9093
     ```
   - Example:
     ```
     team05-kafka.servicebus.windows.net:9093
     ```
   - Click **Update secret**

3. **Verify other Kafka secrets**
   - `KAFKA_USERNAME`: Should be `$ConnectionString`
   - `KAFKA_PASSWORD`: Should be your full Event Hubs connection string
     ```
     Endpoint=sb://<namespace>.servicebus.windows.net/;SharedAccessKeyName=...;SharedAccessKey=...
     ```

## Test

After updating, the GitHub Actions probe workflow should succeed:
- Go to: https://github.com/GouthamMallavolu/PredictIQ/actions
- Trigger a new run or wait for the scheduled run
- Check logs - should see: `Kafka producer created successfully`

## Expected Behavior

✅ **Success:**
```
Connecting to Kafka broker: team05-kafka.servicebus.windows.net:9093
Using username: $ConnectionString
Password configured: Yes
Kafka producer created successfully
```

❌ **Failure (before fix):**
```
Connecting to Kafka broker: finsightai-api.orangegrass-19668bba...
KafkaTimeoutError: Failed to update metadata after 60.0 secs.
```
