# Azure Container Apps Deployment Script for Consumer Service (PowerShell)
# This script builds and deploys the Kafka consumer service to Azure Container Apps

param(
    [string]$ResourceGroup = "finsightai-resourcegroup",
    [string]$ContainerAppName = "finsightai-consumer",
    [string]$AcrName = "finsightairegistry",
    [string]$EnvironmentName = "finsightai-containerenv",
    [string]$ImageName = "finsightai-consumer"
)

Write-Host "========================================" -ForegroundColor Green
Write-Host "Azure Consumer Deployment Script" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

# Check if Azure CLI is installed
if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Host "Azure CLI is not installed. Please install it first." -ForegroundColor Red
    exit 1
}

# Check if logged in to Azure
Write-Host "Checking Azure login status..." -ForegroundColor Yellow
$account = az account show 2>$null
if (-not $account) {
    Write-Host "Not logged in to Azure. Please run 'az login'" -ForegroundColor Yellow
    exit 1
}

# Get current git SHA for image tag
$gitSha = git rev-parse --short HEAD
if (-not $gitSha) {
    $gitSha = "latest"
}

Write-Host "Using image tag: $gitSha" -ForegroundColor Green

# Build Docker image
Write-Host "Building Docker image..." -ForegroundColor Yellow
docker build -f Dockerfile.consumer -t "${ImageName}:${gitSha}" .
docker tag "${ImageName}:${gitSha}" "${ImageName}:latest"
Write-Host "✓ Docker image built" -ForegroundColor Green

# Login to ACR
Write-Host "Logging in to Azure Container Registry..." -ForegroundColor Yellow
az acr login --name $AcrName

# Tag and push to ACR
Write-Host "Pushing image to ACR..." -ForegroundColor Yellow
docker tag "${ImageName}:${gitSha}" "${AcrName}.azurecr.io/${ImageName}:${gitSha}"
docker tag "${ImageName}:${gitSha}" "${AcrName}.azurecr.io/${ImageName}:latest"
docker push "${AcrName}.azurecr.io/${ImageName}:${gitSha}"
docker push "${AcrName}.azurecr.io/${ImageName}:latest"
Write-Host "✓ Image pushed to ACR" -ForegroundColor Green

# Check if container app exists
Write-Host "Checking if container app exists..." -ForegroundColor Yellow
$appExists = az containerapp show --name $ContainerAppName --resource-group $ResourceGroup 2>$null

if ($appExists) {
    Write-Host "Container app exists. Updating..." -ForegroundColor Green
    az containerapp update `
        --name $ContainerAppName `
        --resource-group $ResourceGroup `
        --image "${AcrName}.azurecr.io/${ImageName}:${gitSha}"
    Write-Host "✓ Container app updated" -ForegroundColor Green
} else {
    Write-Host "Container app does not exist. Creating..." -ForegroundColor Yellow
    
    # Prompt for environment variables
    Write-Host "Please provide the following environment variables:" -ForegroundColor Yellow
    $kafkaBroker = Read-Host "KAFKA_BROKER"
    $kafkaUsername = Read-Host "KAFKA_USERNAME"
    $kafkaPassword = Read-Host "KAFKA_PASSWORD" -AsSecureString
    $kafkaPasswordPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($kafkaPassword))
    $storageConnection = Read-Host "STORAGE_CONNECTION"
    $storageContainer = Read-Host "STORAGE_CONTAINER (default: snapshots)"
    if (-not $storageContainer) {
        $storageContainer = "snapshots"
    }
    
    az containerapp create `
        --name $ContainerAppName `
        --resource-group $ResourceGroup `
        --image "${AcrName}.azurecr.io/${ImageName}:${gitSha}" `
        --environment $EnvironmentName `
        --registry-server "${AcrName}.azurecr.io" `
        --cpu 1.0 `
        --memory 2.0Gi `
        --min-replicas 1 `
        --max-replicas 1 `
        --env-vars `
            "KAFKA_BROKER=$kafkaBroker" `
            "KAFKA_USERNAME=$kafkaUsername" `
            "KAFKA_PASSWORD=$kafkaPasswordPlain" `
            "STORAGE_CONNECTION=$storageConnection" `
            "STORAGE_CONTAINER=$storageContainer" `
            "CONSUMER_GROUP=finsight-consumer-group"
    
    Write-Host "✓ Container app created" -ForegroundColor Green
}

Write-Host "========================================" -ForegroundColor Green
Write-Host "Deployment completed successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Container App: $ContainerAppName"
Write-Host "Resource Group: $ResourceGroup"
Write-Host "Image: ${AcrName}.azurecr.io/${ImageName}:${gitSha}"
Write-Host ""
Write-Host "To view logs:"
Write-Host "  az containerapp logs show --name $ContainerAppName --resource-group $ResourceGroup --follow"

