# Prompt for Codex

You are working in a new repository for a proof of concept called:

```text
copilot-sql-mcp-poc
```

Read the entire file:

```text
Copilot_Azure_MCP_POC_Build_Spec.md
```

before changing any code.

The existing working Python file will be copied into this repository as:

```text
legacy/sqlserver_mcp_wwi_cursor_apps_business.py
```

Your task is to build the full working end-to-end proof of concept described in the specification.

## Critical instructions

1. Preserve the existing working Cursor MCP behaviour.
2. Do not replace the STDIO Cursor server with the HTTP/Copilot version.
3. Build one shared analytics core with a Cursor MCP App adapter and an Adaptive Card adapter.
4. The LLM must continue selecting the visual type automatically.
5. Business users must not see SQL, schema names, table names, joins, JSON, MCP tool names, or internal workflow unless explicitly requested.
6. SQL must remain available only in secure internal logs.
7. The system must remain read-only.
8. Never commit secrets.
9. Work in milestones and run tests after each milestone.
10. Before any step that requires me to install, configure, create, or sign into something, stop and give me exact step-by-step instructions.

## Required outcome

The finished proof of concept must support:

```text
Cursor
→ STDIO MCP
→ SQL Server Express
→ interactive MCP App chart
```

and:

```text
Microsoft Copilot / Copilot Studio
→ Streamable HTTP MCP
→ Azure App Service
→ Azure Hybrid Connection
→ SQL Server Express on my laptop
→ Adaptive Card
```

## Implementation sequence

Work through these milestones in order.

### Milestone 1 — Inspect and plan

- Inspect the legacy working file.
- Identify database logic, security logic, schema logic, data dictionary, memory logic, MCP tools, Cursor HTML renderer, configuration, and logging.
- Propose the final repository structure.
- List risks and compatibility concerns.
- Do not change code until the plan is shown.

### Milestone 2 — Behaviour-preserving refactor

- Create the modular project structure.
- Move logic into appropriate modules.
- Preserve all existing MCP tools.
- Preserve the full data dictionary.
- Preserve current local Windows authentication.
- Preserve query logging.
- Preserve Cursor chart rendering.
- Add tests for existing safety rules and result handling.
- Confirm that the existing Cursor acceptance questions still work.

### Milestone 3 — Shared neutral visual response model

Create validated Pydantic models for visual type, series definitions, suggested actions, business summary, rows and columns, and value formatting.

Both Cursor and Copilot renderers must consume the same model.

Do not include SQL in the public response model.

### Milestone 4 — Adaptive Card renderer

Implement deterministic, validated Adaptive Card generation for:

- KPI;
- horizontal bar;
- vertical bar;
- line;
- pie;
- doughnut;
- table;
- fallback.

Add tests using sample `VisualResponse` fixtures.

Include suggested actions such as Show top 10, View underlying data, Overdue only, and Compare with prior month.

Where a visual type is not reliably supported, use a safe fallback and document it.

### Milestone 5 — Streamable HTTP server

Add a separate HTTP entry point.

Requirements:

- Streamable HTTP MCP;
- bind to `0.0.0.0`;
- configurable port;
- `/health`;
- structured logging;
- environment-based configuration;
- same MCP tools and instructions;
- no duplicated analytics logic.

Keep `server_stdio.py` working independently.

### Milestone 6 — Database configuration for Azure

Support Windows authentication for local Cursor use and SQL authentication for Azure-to-laptop use.

Use environment variables only.

Add `.env.example`, startup validation, clear error messages, query timeout, row limits, approved-schema allow-list, and no cross-database queries.

### Milestone 7 — Containerisation

Create:

- Dockerfile;
- requirements files with pinned versions;
- ODBC Driver installation;
- `.dockerignore`;
- local Docker instructions;
- health check.

Do not embed secrets.

### Milestone 8 — Azure deployment documentation

Create a detailed guide for:

- Azure Resource Group;
- App Service Plan;
- App Service for Containers;
- application settings;
- deployment;
- logs;
- `/health` testing;
- Hybrid Connection setup;
- Hybrid Connection Manager installation;
- SQL Server Express fixed port;
- SQL read-only login;
- troubleshooting.

When we reach any Azure step, stop and walk me through what I need to create or configure.

### Milestone 9 — Copilot Studio integration

Create a detailed guide for:

- creating the Copilot Studio agent;
- adding the remote MCP server;
- configuring authentication;
- discovering tools;
- agent instructions;
- consuming the structured response;
- displaying Adaptive Cards;
- handling card actions;
- testing;
- publishing to Microsoft 365 Copilot or Teams.

When we reach Copilot Studio setup, stop and guide me through every manual action.

### Milestone 10 — End-to-end proof

Prove these questions:

1. `What are the top five outstanding customer balances?`
   - horizontal bar;
   - concise summary;
   - no SQL;
   - top 10 action.

2. `How have monthly invoiced sales changed over time?`
   - line chart;
   - concise trend summary;
   - no SQL.

3. `What is total invoiced sales?`
   - KPI;
   - currency formatting;
   - no SQL.

4. `Show the 20 most recent invoices.`
   - table;
   - no SQL.

## Working style

- Make small, reviewable changes.
- Run tests after each milestone.
- Explain what changed.
- Show me how to verify each milestone.
- Do not claim a step works unless it has been tested.
- Keep a running checklist in the README.
- Commit after each completed milestone with a clear message.
- Never delete the legacy source file until the refactored version has passed all equivalent tests.
- Remind me about every download, installation, Azure resource, SQL setting, Copilot setting, or account action I need to perform.

Start now with Milestone 1 only:

1. inspect the repository and legacy file;
2. propose the project structure;
3. identify risks;
4. list the exact acceptance checks for the behaviour-preserving refactor;
5. do not edit code yet.
