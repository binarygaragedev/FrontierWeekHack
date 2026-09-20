# Challenge 0: Setup & Authentication

## Objectives

This setup stage provides the foundational environment for the ride-hailing solution. After deployment, the solution includes:

- ✅ A fully provisioned Microsoft Foundry project for the ride-hailing solution
- ✅ A deployed AI model ready to support the solution agents
- ✅ Application Insights provisioned for tracing and monitoring
- ✅ A generated `.env` file with connection details for the remaining solution components
- ✅ Verified connectivity from the development environment to Microsoft Foundry

## Context

This is a multi-agent AI solution for a ride-hailing platform similar to Uber. The final solution focuses on:

- passenger and driver safety
- route risk evaluation
- real-time in-trip monitoring
- customer support and incident resolution
- operational trust and transparency

Before I build agents, monitoring, and evaluation flows, I need a working Foundry environment with a deployed model and telemetry resources.

## Local Development Setup

Before starting, I need the following:

- An Azure subscription
- Contributor access to the subscription
- Foundry User role assigned on the Foundry account or project
- Azure CLI installed
- Python 3.10+ installed

> [!NOTE]
> Contributor or Owner access alone is not enough for the later build steps. The Foundry User role is also required to run agents in Challenges 1-4.

This solution is intended to run from a local development environment.

```bash
# Clone the repository
git clone https://github.com/binarygaragedev/FrontierWeekHack
cd FrontierWeekHack

# Create and activate a virtual environment
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1

# Install dependencies
python -m pip install -r requirements.txt

# Log in to Azure
az login
```

If my account has access to multiple subscriptions, I select the correct one:

```bash
az account set --subscription "<your-subscription-name-or-id>"
```

## Challenge Task

From the `ridehailing-solution` folder, deploy the environment:

```bash
bash challenge-0-setup/deploy.sh
```

To create predictable resource names, I can provide a suffix:

```bash
SUFFIX=myride01 bash challenge-0-setup/deploy.sh
```

## Expected Output

The deployment script provisions the core infrastructure for the solution:

- a resource group
- a Microsoft Foundry AI Services account
- a Foundry project
- a deployed model
- a Log Analytics workspace
- an Application Insights resource
- a root-level `.env` file with connection values for future challenges

## Validation

When the deployment finishes, I verify the following:

1. Open the Azure Portal.
2. Find the resource group created for the ride-hailing solution.
3. Confirm that the Foundry account, project, Log Analytics workspace, and Application Insights resource were created.
4. Open the Microsoft Foundry portal and confirm that the project is visible.
5. Open the model deployment view and verify that `gpt-5.4` is deployed successfully.
6. Send a short test prompt in the model playground to confirm the deployment is responding.

## Environment Configuration

The deployment writes a `.env` file at the root of the ride-hailing solution. It will contain values similar to:

```env
FOUNDRY_RESOURCE_NAME=...
PROJECT_NAME=...
FOUNDRY_ENDPOINT=...
PROJECT_CONNECTION_STRING=...
MODEL_DEPLOYMENT_NAME=gpt-5.4
APPLICATIONINSIGHTS_CONNECTION_STRING=...
AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING=true
OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true
```

## Success Criteria

- [ ] Azure resources are created successfully
- [ ] The Microsoft Foundry project is visible in the portal
- [ ] The model deployment shows a successful status
- [ ] Application Insights is available for tracing
- [ ] A `.env` file is created with the expected configuration values
- [ ] A test prompt can be sent successfully to the deployed model

## What Comes Next

Once this setup is complete, the environment is ready for Challenge 1, where I build the specialized agents for the ride-hailing workflow.
