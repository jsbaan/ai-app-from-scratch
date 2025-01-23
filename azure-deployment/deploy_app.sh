#!/bin/bash
set -e # Exit script on first error.
# Execute this script from the root of the repository: `bash azure-deployment/deploy_app.sh`

###################################################
# Setting up
###################################################
# Install Azure CLI for macos [optional]
brew update && brew install azure-cli

# Define environment variables used to create Azure resources
source azure-deployment/private_env_vars.sh # load SUBSCRIPTION_ID and EMAIL from a private file
RESOURCE_GROUP="chat-app-rg"
LOCATION="germanywestcentral"
VNET="chat-vnet"
ACA_SUBNET="aca-subnet"
DB_SUBNET="db-subnet"
KEYVAULT="chat-keyvault"
DB_SERVER="chat-postgresql-db"
ACR="acachatjsbaan"
ACA_ENVIRONMENT="chat-app-env"
UI="chat-ui"
DB_API="db-api"
LM_API="lm-api"
CUSTOM_DOMAIN=chat.jorisbaan.nl


echo "Create resource group"
az group create \
  --name $RESOURCE_GROUP \
  --location "$LOCATION"

echo "Create VNET with 256 IP addresses"
az network vnet create \
  --resource-group $RESOURCE_GROUP \
  --name $VNET \
  --address-prefix 10.0.0.0/24 \
  --location $LOCATION


################################################
#PostgreSQL server deployment
################################################

echo "Create subnet for DB with 128 IP addresses"
az network vnet subnet create \
  --resource-group $RESOURCE_GROUP \
  --name $DB_SUBNET \
  --vnet-name $VNET \
  --address-prefix 10.0.0.128/25

echo "Create a key vault to securely store and retrieve secrets, like the db password and session cookie key"
az keyvault create \
  --name $KEYVAULT \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION

echo "Give myself access to the key vault so I can store and retrieve the db password."
az role assignment create \
  --role "Key Vault Secrets Officer" \
  --assignee $EMAIL \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.KeyVault/vaults/$KEYVAULT"

echo "Store random db username and password in the key vault"
echo "It takes a while for the key vault to be ready. If you get 'Caller is not authorized to perform action on resource',"
echo "simply restart the script from here, and don't forget to load the env vars again"
sleep 50
az keyvault secret set \
  --name postgres-username \
  --vault-name $KEYVAULT \
  --value $(openssl rand -base64 12 | tr -dc 'a-zA-Z' | head -c 12)
az keyvault secret set \
  --name postgres-password \
  --vault-name $KEYVAULT \
  --value $(openssl rand -base64 16)
az keyvault secret set \
  --name session-key \
  --vault-name $KEYVAULT \
  --value $(openssl rand -base64 16)

echo "Create PostgreSQL flexible server in our VNET in its own subnet. Creates Private DNS Zone that manages DB hostname."
POSTGRES_USERNAME=$(az keyvault secret show --name postgres-username --vault-name $KEYVAULT --query "value" --output tsv)
POSTGRES_PASSWORD=$(az keyvault secret show --name postgres-password --vault-name $KEYVAULT --query "value" --output tsv)
az postgres flexible-server create \
  --resource-group $RESOURCE_GROUP \
  --name $DB_SERVER \
  --vnet $VNET \
  --subnet $DB_SUBNET \
  --location $LOCATION \
  --admin-user $POSTGRES_USERNAME \
  --admin-password $POSTGRES_PASSWORD \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --storage-size 32 \
  --version 16 \
  --yes


################################################
# Deploy Azure Container Apps Environment
################################################

echo "Create subnet for ACA with 128 IP addresses."
az network vnet subnet create \
  --resource-group $RESOURCE_GROUP \
  --name $ACA_SUBNET \
  --vnet-name $VNET \
  --address-prefix 10.0.0.0/25

echo "Delegate the subnet to ACA"
az network vnet subnet update \
  --resource-group $RESOURCE_GROUP \
  --vnet-name $VNET \
  --name $ACA_SUBNET \
  --delegations Microsoft.App/environments

echo "Obtain the ID of our subnet"
ACA_SUBNET_ID=$(az network vnet subnet show \
  --resource-group $RESOURCE_GROUP \
  --name $ACA_SUBNET \
  --vnet-name $VNET \
  --query id --output tsv)

echo "Create Container Apps Environment (this is like a Kubernetes Cluster) in our custom subnet.\
By default, the Env has a Workload profile with Consumption plan."
az containerapp env create \
  --resource-group $RESOURCE_GROUP \
  --name $ACA_ENVIRONMENT \
  --infrastructure-subnet-resource-id $ACA_SUBNET_ID \
  --location $LOCATION

echo "Create container registry (ACR)"
az acr create \
  --resource-group $RESOURCE_GROUP \
  --name $ACR \
  --sku Standard \
  --admin-enabled true

echo "Login to ACR and push local images"
az acr login --name $ACR
docker build --tag $ACR.azurecr.io/$DB_API $DB_API
docker push $ACR.azurecr.io/$DB_API
docker build --tag $ACR.azurecr.io/$LM_API $LM_API
docker push $ACR.azurecr.io/$LM_API
docker build --tag $ACR.azurecr.io/$UI $UI
docker push $ACR.azurecr.io/$UI



#############################################
# Deploy the containers in the Container Apps Environment
#############################################

echo "Deploy DB API on Container Apps with the db credentials from the key vault as env vars. \
More secure is to use a managed identity that allows the container itself to retrieve them from the key vault. \
But for simplicity we simply fetch it ourselves using the CLI."
POSTGRES_USERNAME=$(az keyvault secret show --name postgres-username --vault-name $KEYVAULT --query "value" --output tsv)
POSTGRES_PASSWORD=$(az keyvault secret show --name postgres-password --vault-name $KEYVAULT --query "value" --output tsv)
az containerapp create --name $DB_API \
  --resource-group $RESOURCE_GROUP \
  --environment $ACA_ENVIRONMENT \
  --registry-server $ACR.azurecr.io \
  --image $ACR.azurecr.io/$DB_API \
  --target-port 80 \
  --ingress internal \
  --env-vars "POSTGRES_HOST=$DB_SERVER.postgres.database.azure.com" "POSTGRES_USERNAME=$POSTGRES_USERNAME" "POSTGRES_PASSWORD=$POSTGRES_PASSWORD" \
  --min-replicas 1 \
  --max-replicas 5 \
  --cpu 0.5 \
  --memory 1 \
  --query properties.configuration.ingress.fqdn

echo "Deploy LM API on Container Apps"
az containerapp create --name $LM_API \
  --resource-group $RESOURCE_GROUP \
  --environment $ACA_ENVIRONMENT \
  --registry-server $ACR.azurecr.io \
  --image $ACR.azurecr.io/$LM_API \
  --target-port 80 \
  --ingress internal \
  --min-replicas 1 \
  --max-replicas 5 \
  --cpu 1 \
  --memory 2 \
  --scale-rule-name my-http-rule \
  --scale-rule-http-concurrency 2 \
  --query properties.configuration.ingress.fqdn

echo "Deploy UI on Container Apps, and retrieve the \
 secret random session key the UI uses to encrypt session cookies"
SESSION_KEY=$(az keyvault secret show --name session-key --vault-name $KEYVAULT --query "value" --output tsv)
az containerapp create --name $UI \
  --resource-group $RESOURCE_GROUP \
  --environment $ACA_ENVIRONMENT \
  --registry-server $ACR.azurecr.io \
  --image $ACR.azurecr.io/$UI \
  --target-port 80 \
  --ingress external \
  --env-vars "db_api_url=http://$DB_API" "lm_api_url=http://$LM_API" "session_key=$SESSION_KEY" \
  --min-replicas 1 \
  --max-replicas 5 \
  --cpu 0.5 \
  --memory 1 \
  --query properties.configuration.ingress.fqdn


#############################################
# Add custom DNS name and automatically managed TLS certificate
#############################################

# Obtain public UI URL and verification code
URL=$(az containerapp show -n $UI -g $RESOURCE_GROUP -o tsv --query "properties.configuration.ingress.fqdn")
VERIFICATION_CODE=$(az containerapp show -n $UI -g $RESOURCE_GROUP -o tsv --query "properties.customDomainVerificationId")

# First go to domain registrar to add a CNAME record with this URL and a TXT record with this verification code
# (Do this manually)

# Add custom domain name to UI App
az containerapp hostname add --hostname $CUSTOM_DOMAIN -g $RESOURCE_GROUP -n $UI

# Configure managed certificate for HTTPS
az containerapp hostname bind --hostname $CUSTOM_DOMAIN -g $RESOURCE_GROUP -n $UI --environment $ACA_ENVIRONMENT --validation-method CNAME

