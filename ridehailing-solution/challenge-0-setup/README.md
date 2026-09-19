# Challenge 0: Setup & Authentication

Time: ~20 minutes

## Objectives

By the end of this challenge, you will have:

- ✅ A Microsoft Foundry project created for the ride-hailing AI solution
- ✅ A deployed model ready for agent development
- ✅ Application Insights configured for tracing and monitoring
- ✅ A local `.env` file with connection details
- ✅ Verified authentication from your machine to the Azure Foundry environment

## Scenario

This solution focuses on a ride-hailing platform similar to Uber, with a strong emphasis on:

- passenger and driver safety,
- route risk evaluation,
- real-time in-trip monitoring,
- customer support and incident resolution,
- operational trust and transparency.

Before building agents, the environment must be provisioned in Azure and connected to Microsoft Foundry.

## Prerequisites

Before starting, make sure you have:

- An Azure subscription
- Contributor access to the subscription
- A Foundry User role assigned in the Microsoft Foundry project or account
- Azure CLI installed
- Python 3.10+ installed

## Step 1: Log in to Azure

```bash
az login
```

If needed, set the correct subscription:

```bash
az account set --subscription "<your-subscription-name-or-id>"
```

## Step 2: Run the deployment script

From the `ridehailing-solution` folder, run:

```bash
bash challenge-0-setup/deploy.sh
```

You can also pass a custom suffix or tag, for example:

```bash
SUFFIX=myride01 bash challenge-0-setup/deploy.sh
```

## What the script deploys

The script creates:

- a resource group,
- Microsoft Foundry AI Services account,
- a Foundry project,
- a deployed model (`gpt-5.4`),
- a Log Analytics workspace,
- an Application Insights resource,
- and the `.env` file with connection values for future challenges.

## Step 3: Verify the setup

After deployment:

1. Open the Azure Portal.
2. Find the resource group created for this solution.
3. Confirm that the Foundry account, project, Log Analytics workspace, and Application Insights resource exist.
4. Open the Microsoft Foundry portal and ensure the project is visible.
5. Navigate to the model deployment and verify that `gpt-5.4` is available and running.

## Environment file

The deployment writes a `.env` file at the root of the solution folder. It contains values such as:

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

## Success criteria

- [ ] Azure resources are created successfully
- [ ] A Foundry project exists
- [ ] A model deployment appears as successful
- [ ] Application Insights is connected or ready for tracing
- [ ] A `.env` file is created and contains the correct configuration

## Next step

Once this step succeeds, the next stage is to build the specialized agents for the ride-hailing workflow.
