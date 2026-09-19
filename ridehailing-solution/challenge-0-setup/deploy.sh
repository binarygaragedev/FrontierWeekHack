#!/bin/bash
set -euo pipefail

# =============================================================================
# Ride-Hailing AI Solution — Infrastructure Deployment Script
# Provisions: AI Foundry (hub + project + model), Log Analytics, App Insights
# Region: swedencentral
# =============================================================================

export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL='*'

az config set extension.use_dynamic_install=yes_without_prompt --only-show-errors >/dev/null 2>&1 || true
az extension add --name application-insights --only-show-errors >/dev/null 2>&1 || true

SUFFIX="${SUFFIX:-$(openssl rand -hex 4)}"
RESOURCE_GROUP="${RESOURCE_GROUP:-ridehailing-hack-rg-$SUFFIX}"
LOCATION="${LOCATION:-swedencentral}"
FOUNDRY_RESOURCE_NAME="${FOUNDRY_RESOURCE_NAME:-ridehailing-foundry-$SUFFIX}"
PROJECT_NAME="${PROJECT_NAME:-ridehailing-project}"
MODEL_DEPLOYMENT_NAME="${MODEL_DEPLOYMENT_NAME:-gpt-5.4}"
MODEL_NAME="${MODEL_NAME:-gpt-5.4}"
MODEL_VERSION="${MODEL_VERSION:-2026-03-05}"
LOG_ANALYTICS_NAME="${LOG_ANALYTICS_NAME:-ridehailing-logs-$SUFFIX}"
APP_INSIGHTS_NAME="${APP_INSIGHTS_NAME:-ridehailing-insights-$SUFFIX}"

TAGS=("environment=ridehailing" "solution=multi-agent-safety")
while [[ $# -gt 0 ]]; do
    case "$1" in
        --tags)
            shift
            while [[ $# -gt 0 && "$1" != --* ]]; do
                TAGS+=("$1")
                shift
            done
            ;;
        *)
            echo "Unknown argument: $1" >&2
            echo "Usage: deploy.sh [--tags 'Key=Value' ...]" >&2
            exit 1
            ;;
    esac
done

echo "=============================================="
echo "  Ride-Hailing AI Solution — Infrastructure Deploy"
echo "=============================================="
echo ""
echo "Suffix:            $SUFFIX"
echo "Resource Group:    $RESOURCE_GROUP"
echo "Location:          $LOCATION"
echo "Foundry Resource:  $FOUNDRY_RESOURCE_NAME"
echo "Project:           $PROJECT_NAME"
echo "Model Deployment:  $MODEL_DEPLOYMENT_NAME"
echo "Model Name:        $MODEL_NAME"
echo "Model Version:     $MODEL_VERSION"
echo "Tags:              ${TAGS[*]}"
echo ""

echo ">>> Creating resource group..."
az group create \
    --name "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --output none \
    --tags "${TAGS[@]}"

echo ">>> Creating Microsoft Foundry Account resource (AIServices)..."
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
az rest \
    --method PUT \
    --url "https://management.azure.com/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.CognitiveServices/accounts/$FOUNDRY_RESOURCE_NAME?api-version=2026-03-01" \
    --body "{\"kind\": \"AIServices\", \"sku\": {\"name\": \"S0\"}, \"location\": \"$LOCATION\", \"identity\": {\"type\": \"SystemAssigned\"}, \"properties\": {\"customSubDomainName\": \"$FOUNDRY_RESOURCE_NAME\", \"publicNetworkAccess\": \"Enabled\", \"allowProjectManagement\": true}}" \
    --output none || true

echo ">>> Waiting for AIServices resource to reach Succeeded state..."
for i in $(seq 1 36); do
    PROV_STATE=$(az cognitiveservices account show \
        --name "$FOUNDRY_RESOURCE_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --query "properties.provisioningState" -o tsv 2>/dev/null || echo "Pending")
    if [ "$PROV_STATE" = "Succeeded" ]; then
        echo "    ✓ Provisioning complete."
        break
    elif [ "$PROV_STATE" = "Failed" ]; then
        echo "❌ AIServices resource provisioning failed. Check the Azure portal for details."
        exit 1
    fi
    echo "    State: $PROV_STATE — retrying in 10s... ($i/36)"
    sleep 10
done

FOUNDRY_RESOURCE_ID=$(az cognitiveservices account show \
    --name "$FOUNDRY_RESOURCE_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query id -o tsv)

az resource update \
    --ids "$FOUNDRY_RESOURCE_ID" \
    --set properties.disableLocalAuth=false \
    --output none || true

az resource update \
    --ids "$FOUNDRY_RESOURCE_ID" \
    --set properties.allowProjectManagement=true \
    --output none

DISABLE_LOCAL_AUTH=$(az cognitiveservices account show \
    --name "$FOUNDRY_RESOURCE_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query properties.disableLocalAuth -o tsv)

if [ "$DISABLE_LOCAL_AUTH" = "true" ]; then
    echo "⚠️  API key authentication is disabled by Azure Policy on this tenant."
    echo "   The deployment will continue — use DefaultAzureCredential (Entra ID) in your code."
fi

echo ">>> Creating Microsoft Foundry project..."
az cognitiveservices account project create \
    --name "$FOUNDRY_RESOURCE_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --project-name "$PROJECT_NAME" \
    --location "$LOCATION" \
    --output none

echo ">>> Deploying model: $MODEL_NAME ($MODEL_VERSION)..."
az cognitiveservices account deployment create \
    --name "$FOUNDRY_RESOURCE_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --deployment-name "$MODEL_DEPLOYMENT_NAME" \
    --model-name "$MODEL_NAME" \
    --model-version "$MODEL_VERSION" \
    --model-format OpenAI \
    --sku-capacity 10 \
    --sku-name GlobalStandard \
    --output none

echo ">>> Creating Log Analytics workspace..."
az monitor log-analytics workspace create \
    --resource-group "$RESOURCE_GROUP" \
    --workspace-name "$LOG_ANALYTICS_NAME" \
    --location "$LOCATION" \
    --output none

LOG_ANALYTICS_ID=$(az monitor log-analytics workspace show \
    --resource-group "$RESOURCE_GROUP" \
    --workspace-name "$LOG_ANALYTICS_NAME" \
    --query id -o tsv)

echo ">>> Creating Application Insights (linked to Log Analytics)..."
az monitor app-insights component create \
    --app "$APP_INSIGHTS_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --workspace "$LOG_ANALYTICS_ID" \
    --output none

APP_INSIGHTS_CONN_STRING=$(az monitor app-insights component show \
    --app "$APP_INSIGHTS_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query connectionString -o tsv)

APP_INSIGHTS_INSTRUMENTATION_KEY=$(az monitor app-insights component show \
    --app "$APP_INSIGHTS_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query instrumentationKey -o tsv)

APP_INSIGHTS_RESOURCE_ID=$(az monitor app-insights component show \
    --app "$APP_INSIGHTS_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query id -o tsv)

echo ">>> Connecting Application Insights to Foundry account..."
if ! az rest \
    --method PUT \
    --url "https://management.azure.com/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.CognitiveServices/accounts/$FOUNDRY_RESOURCE_NAME/connections/appinsights-conn?api-version=2025-06-01" \
    --body "{\"properties\": {\"category\": \"AppInsights\", \"target\": \"$APP_INSIGHTS_RESOURCE_ID\", \"authType\": \"ApiKey\", \"credentials\": {\"key\": \"$APP_INSIGHTS_CONN_STRING\"}, \"isSharedToAll\": true, \"metadata\": {\"ApiType\": \"Azure\", \"ResourceId\": \"$APP_INSIGHTS_RESOURCE_ID\"}}}" \
    --output none; then
    echo "⚠️  Could not link Application Insights to the account automatically."
    echo "   You can connect it manually from the Foundry portal."
fi

echo ">>> Retrieving Foundry endpoint and keys..."
FOUNDRY_ENDPOINT=$(az cognitiveservices account show \
    --name "$FOUNDRY_RESOURCE_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.endpoint" -o tsv)

PROJECT_CONNECTION_STRING=$(az cognitiveservices account project show \
    --name "$FOUNDRY_RESOURCE_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --project-name "$PROJECT_NAME" \
    --query "properties.endpoints.\"AI Foundry API\"" -o tsv)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env"

echo ">>> Writing .env file to: $ENV_FILE"

cat > "$ENV_FILE" << EOF
# =============================================================================
# Ride-Hailing AI Solution — Environment Variables
# Auto-generated by deploy.sh on $(date)
# =============================================================================

AZURE_SUBSCRIPTION_ID=$SUBSCRIPTION_ID
RESOURCE_GROUP=$RESOURCE_GROUP

FOUNDRY_RESOURCE_NAME=$FOUNDRY_RESOURCE_NAME
PROJECT_NAME=$PROJECT_NAME
FOUNDRY_ENDPOINT=$FOUNDRY_ENDPOINT
PROJECT_CONNECTION_STRING=$PROJECT_CONNECTION_STRING
MODEL_DEPLOYMENT_NAME=$MODEL_DEPLOYMENT_NAME

APPLICATIONINSIGHTS_CONNECTION_STRING=$APP_INSIGHTS_CONN_STRING
APPINSIGHTS_INSTRUMENTATION_KEY=$APP_INSIGHTS_INSTRUMENTATION_KEY

AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING=true
OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true
EOF

echo ""
echo "=============================================="
echo "  ✅ DEPLOYMENT COMPLETE"
echo "=============================================="
echo ""
echo "  .env file written to: $ENV_FILE"
echo ""
