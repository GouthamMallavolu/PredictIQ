# GitHub Secrets Setup for Automated Retraining

The automated retraining workflow requires the following secrets to be configured in your GitHub repository to download training data from Azure Blob Storage.

## Required Secrets

Add these secrets in your GitHub repository:
**Settings → Secrets and variables → Actions → New repository secret**

### 1. `STORAGE_CONNECTION`
- **Description**: Azure Storage Account connection string
- **How to get it**:
  1. Go to Azure Portal → Your Storage Account
  2. Settings → Access keys
  3. Copy the "Connection string" (either key1 or key2)
- **Example**: `DefaultEndpointsProtocol=https;AccountName=...;AccountKey=...;EndpointSuffix=core.windows.net`

### 2. `STORAGE_CONTAINER`
- **Description**: Name of the blob container where `Merged_dataset.csv` is stored
- **Example**: `snapshots` or `data`
- **Note**: This should match the container name you used when uploading the data

### 3. `AZURE_STORAGE_BLOB_NAME` (Optional)
- **Description**: Name of the blob file in the container
- **Default**: `Merged_dataset.csv` (if not set)
- **Example**: `Merged_dataset.csv`

## Verification

After adding the secrets, the next retraining run will:
1. Show debug output indicating which variables are set
2. Attempt to download from Azure Blob Storage
3. Fall back to local files if Azure Blob Storage is not configured

## Troubleshooting

If retraining still fails to download from Azure Blob Storage:

1. **Check the workflow logs** for the "Debug environment variables" step
2. **Verify secrets are set**: Go to Settings → Secrets and variables → Actions
3. **Check secret names**: They must match exactly (case-sensitive)
4. **Verify connection string**: Test it locally or in Azure Portal
5. **Check container name**: Ensure it matches the actual container name in Azure
6. **Verify blob exists**: Ensure `Merged_dataset.csv` exists in the specified container

## Alternative: Using Different Secret Names

The workflow also supports these alternative secret names for compatibility:
- `AZURE_STORAGE_CONNECTION_STRING` (instead of `STORAGE_CONNECTION`)
- `AZURE_STORAGE_CONTAINER` (instead of `STORAGE_CONTAINER`)

You can use either naming convention, but `STORAGE_CONNECTION` and `STORAGE_CONTAINER` are preferred.

