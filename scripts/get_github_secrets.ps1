# Helper script to get values for GitHub Secrets
# Run this script to see what values you need to add to GitHub

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "GitHub Secrets Values Helper" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# API URL
Write-Host "1. API_URL:" -ForegroundColor Yellow
$apiUrl = "https://finsightai-api.orangegrass-19668bba.eastus.azurecontainerapps.io"
Write-Host "   Value: $apiUrl" -ForegroundColor Green
Write-Host "   (Copy this value)" -ForegroundColor Gray
Write-Host ""

# KAFKA_BROKER
Write-Host "2. KAFKA_BROKER:" -ForegroundColor Yellow
$kafkaBroker = "finsightai-eventhub.servicebus.windows.net:9093"
Write-Host "   Value: $kafkaBroker" -ForegroundColor Green
Write-Host "   (Copy this value)" -ForegroundColor Gray
Write-Host ""

# KAFKA_USERNAME
Write-Host "3. KAFKA_USERNAME:" -ForegroundColor Yellow
$kafkaUsername = '$ConnectionString'
Write-Host "   Value: $kafkaUsername" -ForegroundColor Green
Write-Host "   (Copy this value)" -ForegroundColor Gray
Write-Host ""

# KAFKA_PASSWORD
Write-Host "4. KAFKA_PASSWORD:" -ForegroundColor Yellow
Write-Host "   This is your Azure Event Hub connection string" -ForegroundColor White
Write-Host "   Format: Endpoint=sb://...;SharedAccessKeyName=...;SharedAccessKey=..." -ForegroundColor White
Write-Host ""
Write-Host "   How to get it:" -ForegroundColor Cyan
Write-Host "   1. Go to Azure Portal" -ForegroundColor White
Write-Host "   2. Navigate to: Event Hubs namespaces → finsightai-eventhub" -ForegroundColor White
Write-Host "   3. Go to: Shared access policies → RootManageSharedAccessKey" -ForegroundColor White
Write-Host "   4. Copy: Connection string-primary key" -ForegroundColor White
Write-Host ""

# Check if KAFKA_PASSWORD is set locally
if ($env:KAFKA_PASSWORD) {
    Write-Host "   Found in environment: $($env:KAFKA_PASSWORD.Substring(0, [Math]::Min(50, $env:KAFKA_PASSWORD.Length)))..." -ForegroundColor Green
    Write-Host "   (You can use this value)" -ForegroundColor Gray
} else {
    Write-Host "   Not found in environment - get from Azure Portal" -ForegroundColor Yellow
}
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan
Write-Host "1. Go to GitHub: https://github.com/YOUR_USERNAME/YOUR_REPO" -ForegroundColor White
Write-Host "2. Click: Settings → Secrets and variables → Actions" -ForegroundColor White
Write-Host "3. Click: New repository secret" -ForegroundColor White
Write-Host "4. Add each secret with the values above" -ForegroundColor White
Write-Host "5. Push workflow to GitHub: git push" -ForegroundColor White
Write-Host "6. Test: Actions → Automated API Probes → Run workflow" -ForegroundColor White
Write-Host ""

