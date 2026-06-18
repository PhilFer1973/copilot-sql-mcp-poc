# Copilot Studio Integration Guide

This guide covers the Copilot Studio setup for the proof of concept. It assumes
the Azure App Service deployment from `AZURE_DEPLOYMENT.md` is already working.

Target architecture:

```text
Microsoft 365 Copilot or Teams
  -> Copilot Studio agent
  -> Remote MCP server over Streamable HTTP
  -> Azure App Service
  -> Hybrid Connection
  -> SQL Server Express / WideWorldImporters
  -> Adaptive Card or plain-text fallback
```

Do not paste SQL passwords, Azure publishing profiles, GitHub secrets, Relay
connection strings, API keys, OAuth client secrets, or downloaded diagnostic
snapshots into this repository or chat.

## Reference Links

- Copilot Studio MCP overview:
  <https://learn.microsoft.com/en-us/microsoft-copilot-studio/agent-extend-action-mcp>
- Connect an existing MCP server:
  <https://learn.microsoft.com/en-us/microsoft-copilot-studio/mcp-add-existing-server-to-agent>
- Add MCP tools and resources:
  <https://learn.microsoft.com/en-us/microsoft-copilot-studio/mcp-add-components-to-agent>
- Generative orchestration:
  <https://learn.microsoft.com/en-us/microsoft-copilot-studio/advanced-generative-actions>
- Test an agent:
  <https://learn.microsoft.com/en-us/microsoft-copilot-studio/authoring-test-bot>
- Publish and deploy concepts:
  <https://learn.microsoft.com/en-us/microsoft-copilot-studio/publication-fundamentals-publish-channels>
- Teams and Microsoft 365 Copilot channel:
  <https://learn.microsoft.com/en-us/microsoft-copilot-studio/publication-add-bot-to-microsoft-teams>
- MCP troubleshooting:
  <https://learn.microsoft.com/en-us/microsoft-copilot-studio/mcp-troubleshooting>

## Before You Start

Stop here until these are true:

- The Azure web app has deployed the container from this repository.
- `https://<web-app-name>.azurewebsites.net/health` returns `healthy`.
- The Hybrid Connection status is `Connected`.
- SQL Server Express is listening on the fixed port documented in
  `AZURE_DEPLOYMENT.md`.
- You can sign in to Copilot Studio with an account allowed to create agents.
- You know which Copilot Studio environment should hold the POC.

The MCP server URL for Copilot Studio is:

```text
https://<web-app-name>.azurewebsites.net/mcp
```

Use `/health` only for browser health checks. Use `/mcp` for the MCP server.

## Authentication Decision For This POC

Current repository state:

- `server_http.py` exposes Streamable HTTP MCP at `/mcp`.
- It does not yet enforce API-key or OAuth authentication at the MCP endpoint.
- SQL access is still read-only and protected by query validation, schema
  allow-listing, row limits, and a SQL read-only login.

Recommended first POC setting in Copilot Studio:

```text
Authentication type: None
```

Use this only for a controlled proof of concept. Do not share or broadly
publish the agent until endpoint authentication is added.

Do not choose API key in the MCP wizard yet. Copilot Studio can send an API key,
but the current server would not validate it, which would create a false sense
of security.

Future hardening path:

- Add a server-side API-key check or Entra ID OAuth validation.
- Store the secret in Azure App Settings or Key Vault, never in the repo.
- Revisit the Copilot Studio MCP connection and choose API key or OAuth 2.0.

## Phase 1: Create The Agent

Manual steps:

1. Open <https://copilotstudio.microsoft.com>.
2. Sign in with the intended work account.
3. Confirm the correct environment is selected.
4. Create a new agent.
5. Name it:

```text
WideWorldImporters Analytics
```

6. Use this description:

```text
Answers read-only business questions about WideWorldImporters sales, invoices,
customers, suppliers, purchasing, and warehouse operations. It returns concise
business summaries and visual results without exposing SQL or database details.
```

7. Skip optional knowledge sources for the first POC. The database MCP server is
   the source of truth.
8. Save the agent.

## Phase 2: Enable Generative Orchestration

MCP tools require generative orchestration.

Manual steps:

1. Open the agent in Copilot Studio.
2. Go to `Settings`.
3. Find `Generative AI`.
4. Under orchestration, set generative orchestration to `Yes`.
5. Save.

If your environment does not allow generative orchestration, stop. The MCP path
will not work in that environment until an admin enables it or a suitable
environment is selected.

## Phase 3: Add The Remote MCP Server

Manual steps:

1. Open the agent.
2. Go to `Tools`.
3. Select `Add a tool`.
4. Select `New tool`.
5. Select `Model Context Protocol`.
6. Fill in:

```text
Server name: WideWorldImporters SQL Analytics MCP
Server URL:  https://<web-app-name>.azurewebsites.net/mcp
```

7. Use this server description:

```text
Provides read-only WideWorldImporters business analytics. Use it for questions
about sales, invoices, customer balances, purchasing, suppliers, stock,
warehouse activity, payments, and operational trends. It returns concise
business summaries, structured business results, Adaptive Card JSON, and
plain-text fallback output. It must not be used for write operations.
```

8. Authentication type: `None`.
9. Create the MCP server connection.
10. Create a new connection if prompted.
11. Select `Add to agent`.

## Phase 4: Discover And Limit Tools

After the MCP server is added, inspect its tools.

Manual steps:

1. Go to the agent `Tools` tab.
2. Open `WideWorldImporters SQL Analytics MCP`.
3. Review the discovered MCP tools.
4. If Copilot Studio provides an `Allow all` toggle, turn it off.
5. Enable only these tools for the first Copilot POC:

```text
sqlserver_get_schema
sqlserver_query
sqlserver_memory_read
sqlserver_copilot_visual_query
```

6. Disable these tools for Copilot:

```text
sqlserver_visual_query
sqlserver_memory_suggest
```

Reasoning:

- `sqlserver_visual_query` is the Cursor MCP App renderer path.
- `sqlserver_copilot_visual_query` is the Copilot-facing Adaptive Card path.
- `sqlserver_memory_suggest` writes pending local memory suggestions and is not
  needed for end-user Copilot testing.

## Phase 5: Agent Instructions

Paste these instructions into the Copilot Studio agent instructions. They are
written for business users and the current MCP tool contract.

```text
You are a business analytics assistant for WideWorldImporters.

Use the WideWorldImporters SQL Analytics MCP toolset for questions about sales,
invoices, customer balances, purchasing, suppliers, stock, warehouse activity,
payments, and operational trends.

Answer in plain business language. Lead with the answer and one or two concise
observations.

Do not show SQL, schema names, table names, joins, column names, raw JSON, MCP
tool names, or internal workflow unless the user explicitly asks for technical
details.

Only answer from read-only data returned by the MCP tools. Never suggest or
perform data changes.

For analytical questions, inspect the schema, run a read-only query, then use
the Copilot visual result tool to return the final business result. Prefer KPI,
trend, ranking, comparison, part-to-whole, or table output based on the returned
data shape. Choose the visual yourself.

Use sqlserver_copilot_visual_query for the final user-facing result whenever the
answer can be represented as a KPI, chart-like summary, or table.

When the tool returns business_result, adaptive_card, and fallback_text, present
the business_result summary and display the adaptive_card if the channel supports
it. If the card cannot be displayed, use fallback_text and do not expose raw JSON.

If a suggested action is returned, treat it as a user-friendly follow-up option.
Do not show the action JSON.

If the user asks for SQL, provide the business answer first, then explain that
SQL is normally hidden for safety and auditability.
```

## Phase 6: Structured Response Mapping

The Copilot-facing MCP tool is:

```text
sqlserver_copilot_visual_query
```

It returns structured content with this shape:

```json
{
  "business_result": {},
  "adaptive_card": {},
  "fallback_text": "..."
}
```

Expected handling:

- `business_result`: use for the concise business answer and underlying rows.
- `adaptive_card`: display as an Adaptive Card when the host supports it.
- `fallback_text`: use when the channel cannot display the card.

Important compatibility note:

Copilot Studio can discover and call MCP tools over Streamable HTTP. The exact
card rendering behavior must be verified in the target channel. If the test
panel or Teams displays only a text answer, confirm that it uses `fallback_text`
and record the Adaptive Card display gap before Milestone 10.

## Phase 7: Adaptive Cards And Actions

The server renders Adaptive Card schema version `1.2`. The card body is
conservative and uses text, facts, column sets, and tables rather than custom
chart extensions.

Supported output patterns:

- KPI
- horizontal bar ranking
- vertical bar comparison
- line trend as ordered points
- pie or doughnut as contribution rows
- table
- fallback table for unsupported shapes

Suggested actions are included as `Action.Submit` buttons with this shape:

```json
{
  "action": "show_top_10",
  "parameters": {}
}
```

For the first POC:

- Treat action buttons as suggested follow-up prompts.
- If the host submits the action back to the agent, have the agent ask or infer
  the matching follow-up question and call the MCP tools again.
- If the host does not submit the action, users can type the same intent, for
  example `Show top 10` or `View underlying data`.
- Do not display action JSON to business users.

## Phase 8: Test In Copilot Studio

Manual steps:

1. Open `Test your agent`.
2. Start a new test session.
3. Open the activity map so you can see whether the MCP server is selected.
4. Ask:

```text
What is total invoiced sales?
```

Expected:

- The agent calls the MCP server.
- The final result is a KPI-style answer.
- No SQL, schema names, table names, MCP tool names, or JSON are shown.
- The answer uses the business summary or fallback text.

5. Ask:

```text
What are the top five outstanding customer balances?
```

Expected:

- The result is a ranking.
- The card or text fallback includes the top customers and balances.
- Suggested action `Show top 10` may be available.

6. Ask:

```text
How have monthly invoiced sales changed over time?
```

Expected:

- The result is a trend.
- The response is concise and business-facing.

7. Ask:

```text
Show the 20 most recent invoices.
```

Expected:

- The result is a table-style answer.
- No raw SQL or raw JSON is shown.

8. If the agent asks for a connection, open `Manage connections` from the test
   panel and confirm the MCP connection is authorized.
9. If you save diagnostic snapshots, keep them outside this repository because
   they can include sensitive agent content.

## Phase 9: Publish For Personal Testing

Do this only after the Copilot Studio test panel passes.

Manual steps:

1. Select `Publish`.
2. Confirm publishing.
3. Do not make the agent broadly available yet.
4. Use the personal/demo test path first.
5. Start a new session after publishing so the latest instructions are loaded.

## Phase 10: Connect Teams And Microsoft 365 Copilot

Manual steps:

1. Open `Channels`.
2. Select `Teams and Microsoft 365 Copilot`.
3. Add the channel.
4. If you want both hosts, keep `Make agent available in Microsoft 365 Copilot`
   selected.
5. Edit details:
   - short description
   - icon
   - developer name
   - website
   - privacy statement
   - terms of use
6. Save.
7. Select `See agent in Teams`.
8. Add it for yourself.
9. In Microsoft 365 Copilot, mention it with `@WideWorldImporters Analytics`
   and ask one of the test questions.

For wider access:

- Share only with selected users first.
- For organization-wide availability, submit for admin approval.
- Coordinate with the Teams or Microsoft 365 admin before broad publication.

## Troubleshooting

### MCP Server Does Not Appear

1. Confirm the server URL ends with `/mcp`.
2. Confirm the Azure app is reachable from the public internet.
3. Confirm the App Service is running.
4. Check `https://<web-app-name>.azurewebsites.net/health`.
5. Confirm Copilot Studio is using Streamable MCP, not SSE.

### Tool Is Not Selected

1. Confirm generative orchestration is enabled.
2. Improve the MCP server description with business terms such as sales,
   invoices, customer balances, purchasing, and warehouse.
3. Confirm the relevant tools are enabled in the MCP tool settings.
4. Use the activity map to see whether another topic or tool was selected.

### Authentication Error

1. Confirm the MCP connection was created with `None` for this POC.
2. Do not configure API key until the server validates API keys.
3. If OAuth is required by policy, stop. The server needs an OAuth validation
   milestone before this integration can proceed.

### Health Is Degraded

1. Return to `AZURE_DEPLOYMENT.md`.
2. Verify the Hybrid Connection is connected.
3. Verify SQL Server Express TCP/IP and fixed port.
4. Verify the SQL read-only login.
5. Verify Azure App Settings.

### Card Does Not Render

1. Confirm `sqlserver_copilot_visual_query` was used.
2. Confirm the tool output includes `adaptive_card`.
3. Confirm the agent used `fallback_text` instead of exposing raw JSON.
4. Test in Teams or Microsoft 365 Copilot after publishing, because the design
   test panel is not a full substitute for channel behavior.
5. Record the channel behavior before Milestone 10.

## Milestone 9 Acceptance Checklist

- Agent creation steps are documented.
- MCP server onboarding steps are documented.
- Authentication choice and limitation are explicit.
- Tool discovery and tool enablement are documented.
- Agent instructions are copy/paste ready.
- Structured response mapping is documented.
- Adaptive Card display and fallback behavior are documented.
- Suggested action handling is documented.
- Test questions are documented.
- Publish, Teams, and Microsoft 365 Copilot steps are documented.
- No secrets or credentials are committed.
