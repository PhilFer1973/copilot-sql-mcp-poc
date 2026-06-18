# Azure Deployment Guide

This guide covers the Azure path for the proof of concept without requiring
local Docker.

Target architecture:

```text
GitHub
  -> GitHub Actions build
  -> Azure Container Registry
  -> Azure App Service for Containers
  -> App Service Hybrid Connection
  -> Hybrid Connection Manager on laptop
  -> SQL Server Express / WideWorldImporters
```

Do not commit passwords, SQL connection strings, publishing profiles, Azure
credentials, Relay connection strings, or access keys.

## Reference Links

- Azure custom container tutorial:
  <https://learn.microsoft.com/en-us/azure/app-service/tutorial-custom-container>
- Azure custom container CI/CD:
  <https://learn.microsoft.com/en-us/azure/app-service/deploy-ci-cd-custom-container>
- App Service app settings:
  <https://learn.microsoft.com/en-us/azure/app-service/configure-common>
- App Service Hybrid Connections:
  <https://learn.microsoft.com/en-us/azure/app-service/app-service-hybrid-connections>

## Recommended Names

Adjust these before creating anything:

```text
Azure region:         UK South
Resource group:       rg-copilot-sql-mcp-poc
Container registry:   acrcopilotsqlmcppoc<unique>
App Service plan:     asp-copilot-sql-mcp-poc
Web app:              app-copilot-sql-mcp-poc-<unique>
Hybrid connection:    hc-local-sqlexpress-wwi
SQL fixed port:       14330
SQL read-only login:  mcp_readonly
```

The App Service plan must use a SKU that supports Hybrid Connections. Basic,
Standard, Premium, and Isolated support Hybrid Connections; Free and Shared do
not.

## Phase 1: Create Azure Resources

Use the Azure Portal unless we later decide to use Azure CLI.

### 1. Create Resource Group

1. Open <https://portal.azure.com>.
2. Search for `Resource groups`.
3. Select `Create`.
4. Choose your subscription.
5. Enter resource group name, for example `rg-copilot-sql-mcp-poc`.
6. Select region, for example `UK South`.
7. Review and create.

### 2. Create Azure Container Registry

1. Search for `Container registries`.
2. Select `Create`.
3. Use the same resource group.
4. Enter a globally unique registry name.
5. Region: same as the resource group.
6. SKU: `Basic` is enough for this POC.
7. Review and create.

Recommended security path:

- Prefer managed identity / deployment integration over long-lived admin
  credentials where possible.
- If Azure Deployment Center creates secrets for GitHub, leave them in GitHub
  secrets only.

### 3. Create App Service Plan

1. Search for `App Service plans`.
2. Select `Create`.
3. Use the same resource group.
4. Operating system: `Linux`.
5. Region: same as the resource group.
6. Pricing tier: `Basic B1` or higher for Hybrid Connections.
7. Review and create.

### 4. Create Web App For Container

1. Search for `App Services`.
2. Select `Create` -> `Web App`.
3. Basics:
   - Publish: `Container`
   - Operating System: `Linux`
   - Region: same as the plan
   - App Service Plan: select the plan created above
4. Container:
   - Choose Azure Container Registry once an image exists, or configure this
     after Deployment Center creates the first image.
5. Review and create.

## Phase 2: Configure GitHub Deployment

Recommended no-local-Docker path:

1. Open the Web App in Azure Portal.
2. Go to `Deployment` -> `Deployment Center`.
3. Source: `GitHub`.
4. Sign in/authorize GitHub if prompted.
5. Select repository:
   - Owner: `PhilFer1973`
   - Repository: `copilot-sql-mcp-poc`
   - Branch: `master`
6. Build provider: `GitHub Actions`.
7. Container registry: select the Azure Container Registry created above.
8. Save.

Expected result:

- Azure adds GitHub secrets for registry/app deployment.
- Azure adds or updates a GitHub Actions workflow.
- The workflow builds the Docker image, pushes it to ACR, and updates App
  Service.

Review any generated workflow before merging future changes. It must build from
the repository root so it finds `Dockerfile`.

## Phase 3: Configure App Settings

In the Web App:

1. Go to `Settings` -> `Environment variables`.
2. Add App settings.
3. Save and restart the app after changes.

Required app settings for the first Azure proof:

```text
PORT=8000
HOST=0.0.0.0
MCP_HTTP_PATH=/mcp
LOG_LEVEL=INFO

SQLSERVER_HOST=<laptop-hostname-used-by-hybrid-connection>
SQLSERVER_PORT=14330
SQLSERVER_DB=WideWorldImporters
SQLSERVER_AUTH_MODE=sql
SQLSERVER_USER=mcp_readonly
SQLSERVER_PASSWORD=<set in Azure only>
SQLSERVER_DRIVER=ODBC Driver 18 for SQL Server
SQLSERVER_ENCRYPT=yes
SQLSERVER_TRUST_CERT=yes
QUERY_TIMEOUT_SECONDS=15
MAX_QUERY_ROWS=500
SQLSERVER_APPROVED_SCHEMAS=Application,Sales,Purchasing,Warehouse
```

Notes:

- Do not use `localhost` for `SQLSERVER_HOST` in App Service.
- Use the same hostname and port configured in the Hybrid Connection.
- Keep `SQLSERVER_PASSWORD` only in Azure App Settings or Key Vault later.

## Phase 4: Test App Startup

After deployment:

1. Open the Web App.
2. Go to `Monitoring` -> `Log stream`.
3. Wait for the container to start.
4. Test:

```text
https://<web-app-name>.azurewebsites.net/health
```

Before Hybrid Connection and SQL setup are complete, `/health` may return:

```json
{
  "status": "degraded",
  "database": "unreachable",
  "version": "0.1.0"
}
```

That is acceptable until the laptop SQL path is configured. A healthy response
is:

```json
{
  "status": "healthy",
  "database": "reachable",
  "version": "0.1.0"
}
```

## Phase 5: Prepare SQL Server Express On Laptop

Do this only when ready to connect Azure to the laptop.

### Enable TCP/IP And Fixed Port

1. Open `SQL Server Configuration Manager`.
2. Go to `SQL Server Network Configuration`.
3. Select protocols for your SQL Express instance.
4. Enable `TCP/IP`.
5. Open `TCP/IP` properties.
6. On the `IP Addresses` tab, clear dynamic ports for the active IP entries.
7. Set TCP port to `14330`.
8. Restart the SQL Server service.

### Test Locally

In PowerShell:

```powershell
Test-NetConnection <your-laptop-hostname> -Port 14330
```

Expected:

```text
TcpTestSucceeded : True
```

### Create Read-Only Login

Use SQL Server Management Studio or an equivalent tool.

Create a SQL login named `mcp_readonly`, grant it access to
`WideWorldImporters`, and grant read-only permissions.

Do not paste the password into this repository or chat.

Example shape to review before running manually:

```sql
USE [master];
CREATE LOGIN [mcp_readonly] WITH PASSWORD = '<choose-local-secret>';

USE [WideWorldImporters];
CREATE USER [mcp_readonly] FOR LOGIN [mcp_readonly];
ALTER ROLE [db_datareader] ADD MEMBER [mcp_readonly];
```

Test the login locally before using it in Azure App Settings.

## Phase 6: Create Hybrid Connection

In the Web App:

1. Go to `Settings` -> `Networking`.
2. Find `Hybrid connections`.
3. Select `Add hybrid connection`.
4. Select `Create new hybrid connection`.
5. Enter:
   - Name: `hc-local-sqlexpress-wwi`
   - Endpoint host: laptop hostname, not `localhost`
   - Endpoint port: `14330`
   - Service Bus namespace: create/select one in same region
6. Save.

Hybrid Connections are TCP host/port mappings. They do not expose SQL Server to
the public internet.

## Phase 7: Install Hybrid Connection Manager

On the laptop:

1. Download the current Windows Hybrid Connection Manager MSI from the Azure
   Hybrid Connections documentation.
2. Install it.
3. Open `Hybrid Connection Manager GUI`.
4. Select `+ New`.
5. Select `Select with Azure`.
6. Sign in.
7. Choose the subscription.
8. Select the Hybrid Connection created above.
9. Select `Create`.

Expected state:

```text
Connected
```

Network requirements:

- Laptop must reach Azure Relay over outbound TCP 443.
- Laptop must reach SQL Server Express on the configured host and port.
- The endpoint hostname must resolve from the laptop running HCM.

## Phase 8: End-To-End Health Test

After App Settings, SQL Server TCP, read-only login, and Hybrid Connection are
configured:

```text
https://<web-app-name>.azurewebsites.net/health
```

Expected:

```json
{
  "status": "healthy",
  "database": "reachable",
  "version": "0.1.0"
}
```

## Troubleshooting

### Container Does Not Start

1. Open Web App -> `Log stream`.
2. Check image pull errors.
3. Confirm App Service can access the container registry.
4. Confirm `PORT=8000`.
5. Confirm the container image has the latest tag from the workflow.

### `/health` Is Degraded

1. Confirm SQL Server service is running.
2. Confirm TCP/IP is enabled for SQL Express.
3. Confirm fixed port is set to `14330`.
4. Run local PowerShell:

```powershell
Test-NetConnection <your-laptop-hostname> -Port 14330
```

5. Confirm Hybrid Connection status is `Connected`.
6. Confirm App Settings match the Hybrid Connection host and port.
7. Confirm `SQLSERVER_AUTH_MODE=sql`.
8. Confirm the SQL login can read `WideWorldImporters`.

### Hybrid Connection Not Connected

1. Confirm Hybrid Connection Manager is installed and running.
2. Confirm the laptop has outbound TCP 443 access.
3. Restart the Hybrid Connection Manager service.
4. Confirm no proxy/firewall is blocking WebSocket/HTTPS to Azure Relay.
5. Confirm you selected the correct subscription and Hybrid Connection in HCM.

### App Cannot Reach Hybrid Endpoint

1. Use Web App -> `Advanced Tools` -> console.
2. Use `tcpping <hybrid-host> <port>` if available.
3. Check that the endpoint host is not `localhost`.
4. Check that DNS resolves for the endpoint host.

## Cost Reminder

This POC can incur Azure cost for:

- App Service Plan
- Azure Container Registry
- Azure Relay / Hybrid Connection listeners
- Log retention or monitoring if enabled

Stop or delete resources when not testing.
