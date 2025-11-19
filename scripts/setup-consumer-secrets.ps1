# Setup Consumer Secrets for Azure Container Apps
# This script helps configure the consumer container app with required secrets

param(
    [string]$ResourceGroup = "finsightai-resourcegroup",
    [string]$ContainerAppName = "finsightai-consumer"
)

Write-Host "========================================" -ForegroundColor Green
Write-Host "Consumer Secrets Setup" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

Write-Host ""
Write-Host "This script will help you set up secrets for the consumer container app." -ForegroundColor Yellow
Write-Host "You'll need to provide:" -ForegroundColor Yellow
Write-Host "  1. KAFKA_PASSWORD (from Event Hub connection string)" -ForegroundColor Yellow
Write-Host "  2. STORAGE_CONNECTION (Azure Storage connection string)" -ForegroundColor Yellow
Write-Host ""

# Get Kafka password
$kafkaPassword = Read-Host "Enter KAFKA_PASSWORD (Event Hub connection string)" -AsSecureString
$kafkaPasswordPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($kafkaPassword))

# Get Storage connection
$storageConnection = Read-Host "Enter STORAGE_CONNECTION (Azure Storage connection string)" -AsSecureString
$storageConnectionPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($storageConnection))

Write-Host ""
Write-Host "Updating container app environment variables..." -ForegroundColor Yellow

# Update container app with environment variables
az containerapp update `
    --name $ContainerAppName `
    --resource-group $ResourceGroup `
    --set-env-vars `
        "KAFKA_BROKER=finsightai-eventhub.servicebus.windows.net:9093" `
        "KAFKA_USERNAME=`$ConnectionString" `
        "KAFKA_PASSWORD=$kafkaPasswordPlain" `
        "STORAGE_CONNECTION=$storageConnectionPlain" `
        "STORAGE_CONTAINER=snapshots" `
        "CONSUMER_GROUP=finsight-consumer-group" `
        "SYMBOLS=AAPL,MSFT,NVDA,META,TSLA,AMZN"

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✓ Consumer container app updated successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "The consumer should now be able to connect to Kafka." -ForegroundColor Green
    Write-Host "Check logs with:" -ForegroundColor Yellow
    Write-Host "  az containerapp logs show --name $ContainerAppName --resource-group $ResourceGroup --follow" -ForegroundColor Cyan
} else {
    Write-Host ""
    Write-Host "✗ Failed to update container app" -ForegroundColor Red
    Write-Host "Please check the error message above and try again." -ForegroundColor Yellow
}

