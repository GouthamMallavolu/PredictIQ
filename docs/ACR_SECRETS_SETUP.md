# Azure Container Registry Secrets Setup

## Required GitHub Secrets

For CI/CD to push Docker images to Azure Container Registry and deploy to Container Apps, you need these secrets:

### 1. ACR_LOGIN_SERVER
**Value**: `finsightairegistry.azurecr.io`

### 2. ACR_USERNAME
**Value**: Your ACR admin username (usually: `finsightairegistry`)

### 3. ACR_PASSWORD
**Value**: Your ACR admin password

---

## How to Get ACR Credentials

### Option 1: Azure Portal (Easiest)

1. Go to: https://portal.azure.com
2. Navigate to: **Container registries** → **finsightairegistry**
3. In the left menu, click: **Access keys**
4. If "Admin user" is disabled, **enable it**
5. Copy:
   - **Login server**: `finsightairegistry.azurecr.io`
   - **Username**: Usually `finsightairegistry`
   - **Password**: Use either `password` or `password2`

### Option 2: Azure CLI

```bash
# Get login server
az acr show --name finsightairegistry --query loginServer --output tsv
# Output: finsightairegistry.azurecr.io

# Get credentials
az acr credential show --name finsightairegistry
# Output will show username and passwords
```

---

## How to Add Secrets to GitHub

1. Go to: https://github.com/GouthamMallavolu/PredictIQ/settings/secrets/actions

2. Click: **New repository secret**

3. Add each secret:

   **Secret 1:**
   - Name: `ACR_LOGIN_SERVER`
   - Value: `finsightairegistry.azurecr.io`
   - Click: **Add secret**

   **Secret 2:**
   - Name: `ACR_USERNAME`
   - Value: `finsightairegistry` (or the username from Azure Portal)
   - Click: **Add secret**

   **Secret 3:**
   - Name: `ACR_PASSWORD`
   - Value: (paste the password from Azure Portal)
   - Click: **Add secret**

---

## What Happens After Adding Secrets

Once secrets are configured:

1. **On push to `development` branch:**
   - Tests run
   - Docker image builds
   - Image pushes to ACR
   - Deploy skipped (only runs on `main`)

2. **On push to `main` branch:**
   - Tests run
   - Docker image builds
   - Image pushes to ACR
   - **Deploys to Azure Container App automatically**

---

## Why We Need ACR

Your Container App needs to pull Docker images from Azure Container Registry:

```
GitHub Actions → Build → Push to ACR → Container App pulls from ACR
```
