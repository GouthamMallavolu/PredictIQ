#!/bin/bash
# Azure Container Apps Deployment Script for Consumer Service
# This script builds and deploys the Kafka consumer service to Azure Container Apps

set -e

# Configuration
RESOURCE_GROUP="finsightai-resourcegroup"
CONTAINER_APP_NAME="finsightai-consumer"
ACR_NAME="finsightairegistry"
ENVIRONMENT_NAME="finsightai-containerenv"
IMAGE_NAME="finsightai-consumer"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Azure Consumer Deployment Script${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo -e "${RED}Azure CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if logged in to Azure
echo -e "${YELLOW}Checking Azure login status...${NC}"
if ! az account show &> /dev/null; then
    echo -e "${YELLOW}Not logged in to Azure. Please run 'az login'${NC}"
    exit 1
fi

# Get current git SHA for image tag
GIT_SHA=$(git rev-parse --short HEAD)
if [ -z "$GIT_SHA" ]; then
    GIT_SHA="latest"
fi

echo -e "${GREEN}Using image tag: ${GIT_SHA}${NC}"

# Build Docker image
echo -e "${YELLOW}Building Docker image...${NC}"
docker build -f Dockerfile.consumer -t ${IMAGE_NAME}:${GIT_SHA} .
docker tag ${IMAGE_NAME}:${GIT_SHA} ${IMAGE_NAME}:latest
echo -e "${GREEN}✓ Docker image built${NC}"

# Login to ACR
echo -e "${YELLOW}Logging in to Azure Container Registry...${NC}"
az acr login --name ${ACR_NAME}

# Tag and push to ACR
echo -e "${YELLOW}Pushing image to ACR...${NC}"
docker tag ${IMAGE_NAME}:${GIT_SHA} ${ACR_NAME}.azurecr.io/${IMAGE_NAME}:${GIT_SHA}
docker tag ${IMAGE_NAME}:${GIT_SHA} ${ACR_NAME}.azurecr.io/${IMAGE_NAME}:latest
docker push ${ACR_NAME}.azurecr.io/${IMAGE_NAME}:${GIT_SHA}
docker push ${ACR_NAME}.azurecr.io/${IMAGE_NAME}:latest
echo -e "${GREEN}✓ Image pushed to ACR${NC}"

# Check if container app exists
echo -e "${YELLOW}Checking if container app exists...${NC}"
if az containerapp show --name ${CONTAINER_APP_NAME} --resource-group ${RESOURCE_GROUP} &> /dev/null; then
    echo -e "${GREEN}Container app exists. Updating...${NC}"
    az containerapp update \
        --name ${CONTAINER_APP_NAME} \
        --resource-group ${RESOURCE_GROUP} \
        --image ${ACR_NAME}.azurecr.io/${IMAGE_NAME}:${GIT_SHA}
    echo -e "${GREEN}✓ Container app updated${NC}"
else
    echo -e "${YELLOW}Container app does not exist. Creating...${NC}"
    
    # Prompt for environment variables
    echo -e "${YELLOW}Please provide the following environment variables:${NC}"
    read -p "KAFKA_BROKER: " KAFKA_BROKER
    read -p "KAFKA_USERNAME: " KAFKA_USERNAME
    read -sp "KAFKA_PASSWORD: " KAFKA_PASSWORD
    echo ""
    read -p "STORAGE_CONNECTION: " STORAGE_CONNECTION
    read -p "STORAGE_CONTAINER (default: snapshots): " STORAGE_CONTAINER
    STORAGE_CONTAINER=${STORAGE_CONTAINER:-snapshots}
    
    az containerapp create \
        --name ${CONTAINER_APP_NAME} \
        --resource-group ${RESOURCE_GROUP} \
        --image ${ACR_NAME}.azurecr.io/${IMAGE_NAME}:${GIT_SHA} \
        --environment ${ENVIRONMENT_NAME} \
        --registry-server ${ACR_NAME}.azurecr.io \
        --cpu 1.0 \
        --memory 2.0Gi \
        --min-replicas 1 \
        --max-replicas 1 \
        --env-vars \
            KAFKA_BROKER="${KAFKA_BROKER}" \
            KAFKA_USERNAME="${KAFKA_USERNAME}" \
            KAFKA_PASSWORD="${KAFKA_PASSWORD}" \
            STORAGE_CONNECTION="${STORAGE_CONNECTION}" \
            STORAGE_CONTAINER="${STORAGE_CONTAINER}" \
            CONSUMER_GROUP="finsight-consumer-group"
    
    echo -e "${GREEN}✓ Container app created${NC}"
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Container App: ${CONTAINER_APP_NAME}"
echo "Resource Group: ${RESOURCE_GROUP}"
echo "Image: ${ACR_NAME}.azurecr.io/${IMAGE_NAME}:${GIT_SHA}"
echo ""
echo "To view logs:"
echo "  az containerapp logs show --name ${CONTAINER_APP_NAME} --resource-group ${RESOURCE_GROUP} --follow"

