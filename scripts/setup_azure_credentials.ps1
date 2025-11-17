# Setup Azure Credentials for GitHub Actions
# This script creates an Azure Service Principal and outputs the credentials in the correct format

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Azure Credentials Setup for GitHub Actions" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Azure CLI is installed
try {
    $azVersion = az version --output json | ConvertFrom-Json
    Write-Host "[OK] Azure CLI found (version: $($azVersion.'azure-cli'))" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Azure CLI not found. Please install it first:" -ForegroundColor Red
    Write-Host "  https://aka.ms/installazurecliwindows" -ForegroundColor Yellow
    exit 1
}

# Check if logged in
try {
    $account = az account show --output json | ConvertFrom-Json
    Write-Host "[OK] Logged in as: $($account.user.name)" -ForegroundColor Green
    Write-Host "     Subscription: $($account.name) ($($account.id))" -ForegroundColor Gray
} catch {
    Write-Host "[ERROR] Not logged in to Azure. Please run: az login" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Creating Azure Service Principal..." -ForegroundColor Cyan
Write-Host ""

# Get subscription ID
$subscriptionId = $account.id
$spName = "github-actions-finsightai-$(Get-Date -Format 'yyyyMMddHHmmss')"

Write-Host "Service Principal Name: $spName" -ForegroundColor Yellow
Write-Host "Subscription ID: $subscriptionId" -ForegroundColor Yellow
Write-Host ""

# Create service principal
Write-Host "Creating service principal (this may take a moment)..." -ForegroundColor Cyan
try {
    $spOutput = az ad sp create-for-rbac `
        --name $spName `
        --role contributor `
        --scopes "/subscriptions/$subscriptionId" `
        --sdk-auth `
        --output json | ConvertFrom-Json
    
    Write-Host "[OK] Service Principal created successfully!" -ForegroundColor Green
    Write-Host ""
    
    # Format output for GitHub Secret
    $githubSecret = @{
        clientId = $spOutput.clientId
        clientSecret = $spOutput.clientSecret
        subscriptionId = $spOutput.subscriptionId
        tenantId = $spOutput.tenantId
        activeDirectoryEndpointUrl = $spOutput.activeDirectoryEndpointUrl
        resourceManagerEndpointUrl = $spOutput.resourceManagerEndpointUrl
        activeDirectoryGraphResourceId = $spOutput.activeDirectoryGraphResourceId
        sqlManagementEndpointUrl = $spOutput.sqlManagementEndpointUrl
        galleryEndpointUrl = $spOutput.galleryEndpointUrl
        managementEndpointUrl = $spOutput.managementEndpointUrl
    }
    
    $jsonOutput = $githubSecret | ConvertTo-Json -Compress
    
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "AZURE_CREDENTIALS Secret Value:" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host $jsonOutput -ForegroundColor White
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    
    # Save to file
    $outputFile = "azure_credentials.json"
    $jsonOutput | Out-File -FilePath $outputFile -Encoding UTF8
    Write-Host "[OK] Credentials saved to: $outputFile" -ForegroundColor Green
    Write-Host ""
    
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Next Steps:" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "1. Copy the JSON output above (or from $outputFile)" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "2. Go to GitHub repository:" -ForegroundColor Yellow
    Write-Host "   Settings -> Secrets and variables -> Actions" -ForegroundColor White
    Write-Host ""
    Write-Host "3. Click 'New repository secret'" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "4. Name: AZURE_CREDENTIALS" -ForegroundColor Yellow
    Write-Host "   Value: Paste the JSON output" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "5. Click 'Add secret'" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "[WARN] Keep these credentials secure!" -ForegroundColor Red
    Write-Host "       The clientSecret will not be shown again." -ForegroundColor Red
    Write-Host "       Delete $outputFile after adding to GitHub." -ForegroundColor Red
    Write-Host ""
    
} catch {
    Write-Host "[ERROR] Failed to create service principal: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Common issues:" -ForegroundColor Yellow
    Write-Host "  - Insufficient permissions (need Application Administrator role)" -ForegroundColor White
    Write-Host "  - Service principal name already exists (try again)" -ForegroundColor White
    Write-Host ""
    exit 1
}

