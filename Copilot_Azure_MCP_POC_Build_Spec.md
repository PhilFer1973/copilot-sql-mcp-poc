# Copilot + Azure + SQL Server MCP Proof of Concept

## 1. Objective

Build a working end-to-end proof of concept in which a non-technical business user can ask an ordinary finance or commercial question in Microsoft Copilot, the system can query a local SQL Server Express instance running WideWorldImporters, and the answer is returned as a business-friendly interactive Adaptive Card.

The target user experience is:

> What are the top five outstanding customer balances?

The user should receive:

- an appropriate chart or KPI chosen automatically;
- a concise business summary;
- access to underlying data where appropriate;
- optional follow-up actions such as “Show top 10” or “Overdue only”;
- no SQL, schema details, table names, JSON, MCP tool names, or technical workflow unless explicitly requested.

The existing Cursor MCP implementation must continue to work.

---

## 2. Existing Working Baseline

The current working implementation is a Python MCP server that:

- connects to local SQL Server Express;
- uses the WideWorldImporters database;
- runs over STDIO for Cursor;
- supports live schema inspection;
- contains a curated business data dictionary;
- supports read-only NL-to-SQL workflows;
- logs generated SQL;
- returns interactive MCP App charts in Cursor;
- lets the LLM choose KPI, table, bar, horizontal bar, line, scatter, pie, or doughnut;
- hides SQL and technical detail from business users by default.

The working source file to preserve is:

```text
sqlserver_mcp_wwi_cursor_apps_business.py
```

Do not replace or remove this working capability until the refactored version has passed equivalent tests.

---

## 3. Target Architecture

```text
Microsoft 365 Copilot or Teams
            ↓
Copilot Studio agent
            ↓
MCP over Streamable HTTP
            ↓
Python MCP server hosted in Azure App Service
            ↓
Azure App Service Hybrid Connection
            ↓
Hybrid Connection Manager on the laptop
            ↓
SQL Server Express / WideWorldImporters
```

The project must support two front ends from one analytical core:

```text
Shared analytics engine
    ├── Cursor adapter → MCP App / Chart.js
    └── Copilot adapter → Adaptive Card JSON
```

---

## 4. Core Architectural Principle

Separate the solution into:

1. database connectivity;
2. security and SQL validation;
3. business data dictionary;
4. schema discovery;
5. analytics orchestration;
6. neutral visual response model;
7. Cursor rendering;
8. Adaptive Card rendering;
9. STDIO MCP transport;
10. Streamable HTTP MCP transport;
11. health and diagnostics;
12. deployment configuration.

The LLM should choose the analysis and chart type. The renderer should only convert a validated neutral visual specification into the format required by the front end.

---

## 5. Recommended Repository Structure

```text
copilot-sql-mcp-poc/
│
├── legacy/
│   └── sqlserver_mcp_wwi_cursor_apps_business.py
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── database.py
│   ├── data_dictionary.py
│   ├── schema_service.py
│   ├── security.py
│   ├── query_service.py
│   ├── memory_service.py
│   ├── response_models.py
│   ├── visual_selection.py
│   ├── analytics_service.py
│   ├── mcp_tools.py
│   ├── cursor_renderer.py
│   ├── adaptive_card_renderer.py
│   └── health.py
│
├── tests/
│   ├── test_security.py
│   ├── test_response_models.py
│   ├── test_visual_validation.py
│   ├── test_adaptive_cards.py
│   ├── test_query_service.py
│   └── fixtures/
│       └── sample_visual_responses.json
│
├── server_stdio.py
├── server_http.py
├── requirements.txt
├── requirements-dev.txt
├── Dockerfile
├── .dockerignore
├── .gitignore
├── .env.example
├── README.md
├── AZURE_DEPLOYMENT.md
├── COPILOT_STUDIO_SETUP.md
├── TROUBLESHOOTING.md
└── docs/
    ├── architecture.md
    ├── acceptance_tests.md
    └── adaptive_card_examples.md
```

A smaller structure is acceptable if the same separation of concerns is preserved.

---

## 6. Shared Neutral Visual Contract

Create strongly typed Pydantic models for the analytical result.

Suggested model:

```python
from typing import Any, Literal
from pydantic import BaseModel, Field

VisualType = Literal[
    "table",
    "kpi",
    "bar",
    "horizontal_bar",
    "line",
    "scatter",
    "pie",
    "doughnut",
]

ValueFormat = Literal[
    "number",
    "integer",
    "currency",
    "percent",
    "date",
    "datetime",
    "text",
]

class SeriesDefinition(BaseModel):
    name: str
    field: str
    value_format: ValueFormat = "number"
    currency_code: str | None = None

class SuggestedAction(BaseModel):
    label: str
    action: str
    parameters: dict[str, Any] = Field(default_factory=dict)

class VisualResponse(BaseModel):
    title: str
    summary: str
    visual_type: VisualType
    category_field: str | None = None
    series: list[SeriesDefinition] = Field(default_factory=list)
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    suggested_actions: list[SuggestedAction] = Field(default_factory=list)
    reasoning_note: str | None = None
```

Requirements:

- `reasoning_note` is internal and must not be shown to the business user.
- SQL must not be included in the public response model.
- SQL may be retained in internal logs.
- Renderers must consume `VisualResponse`.
- Both Cursor and Adaptive Card outputs must be generated from the same response model.
- Validate field names against actual returned rows.
- Fall back safely to table output if a requested visual cannot be rendered.

---

## 7. LLM Visual Selection Rules

The MCP server instructions must tell the model to:

- accept ordinary business questions;
- perform schema discovery, memory lookup, SQL generation, execution, and result inspection silently;
- choose the best final presentation automatically;
- not require the user to ask for a chart;
- not reveal SQL by default;
- not reveal schemas, tables, columns, joins, JSON, tool names, or internal workflow;
- return one or two concise business observations.

Use:

- KPI for one principal numeric result;
- line for an ordered time series;
- horizontal bar for rankings, top/bottom N, or long labels;
- vertical bar for small independent category comparisons;
- scatter for a relationship between two numeric measures;
- pie/doughnut only for a small, meaningful whole with no negative values;
- table for detailed records or unsuitable chart shapes.

---

## 8. Existing Cursor Path

Maintain a working STDIO entry point:

```python
if __name__ == "__main__":
    mcp.run(transport="stdio")
```

Requirements:

- existing Cursor MCP tools remain available;
- existing chart behaviour remains available;
- the Cursor MCP App consumes `VisualResponse`;
- Visual and Data tabs remain available;
- SQL remains hidden from business users;
- existing logging and read-only controls remain available.

Acceptance question:

> What are the top five outstanding customer balances?

Expected:

- horizontal bar;
- concise summary;
- no SQL;
- underlying data available.

Acceptance question:

> How have monthly invoiced sales changed over time?

Expected:

- line chart;
- concise trend summary;
- no SQL.

---

## 9. Streamable HTTP MCP Server

Add a second entry point for Azure and Copilot Studio.

Requirements:

- use Streamable HTTP;
- bind to `0.0.0.0`;
- read port from `PORT`, defaulting to a sensible local value;
- expose the MCP endpoint at a documented path;
- preserve the same tools and business instructions;
- do not duplicate analytical logic;
- add structured logging;
- fail clearly if required environment variables are missing.

Create a basic health endpoint:

```text
GET /health
```

Example response:

```json
{
  "status": "healthy",
  "database": "reachable",
  "version": "0.1.0"
}
```

Do not expose passwords, full connection strings, internal paths, SQL text, or access tokens.

---

## 10. Database Configuration

Support both local development and Azure-hosted operation through environment variables.

Suggested variables:

```text
SQLSERVER_HOST
SQLSERVER_PORT
SQLSERVER_DB
SQLSERVER_USER
SQLSERVER_PASSWORD
SQLSERVER_DRIVER
SQLSERVER_ENCRYPT
SQLSERVER_TRUST_CERT
SQLSERVER_AUTH_MODE
QUERY_TIMEOUT_SECONDS
MAX_QUERY_ROWS
LOG_LEVEL
PORT
```

Authentication modes:

1. `windows` for the existing local Cursor setup;
2. `sql` for Azure-to-laptop proof of concept.

Requirements:

- never hard-code passwords;
- `.env` must be ignored by Git;
- provide `.env.example`;
- validate configuration at startup;
- use ODBC Driver 18 where available in Azure/container environments;
- keep current local fallback behaviour where needed.

---

## 11. SQL Safety Controls

The LLM is not the security boundary.

Required controls:

- one statement only;
- `SELECT` or CTE only;
- no `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, `EXEC`, `MERGE`, `TRUNCATE`, `BULK`;
- no SQL comments;
- no cross-database references;
- no system tables;
- maximum row limit;
- command timeout;
- server-side read-only SQL identity;
- logging of timestamp, calling tool, duration, row count, success/failure, and SQL text in secure internal logs only.

Prefer an allow-list of approved schemas:

```text
Application
Sales
Purchasing
Warehouse
```

Support a stricter future mode based on approved reporting views.

---

## 12. Adaptive Card Renderer

Create an adapter that converts `VisualResponse` to Adaptive Card JSON.

Initial supported outputs:

- KPI;
- horizontal bar;
- vertical bar;
- line;
- pie;
- doughnut;
- table;
- unsupported/fallback message.

Scatter may initially fall back to a table or generated image if the target host does not support it reliably.

Requirements:

- use supported Adaptive Card schema for the intended Copilot/Teams host;
- do not generate arbitrary unvalidated JSON;
- use deterministic templates or validated builder functions;
- handle empty datasets;
- handle null values;
- handle long labels;
- cap categories to a readable number;
- preserve full underlying data through a detail action or secondary card where practical;
- include business summary;
- include optional suggested actions.

Suggested actions:

- Show top 10;
- Show top 20;
- Overdue only;
- View underlying data;
- Compare with prior month;
- Filter by category;
- Change period.

Each action should submit a machine-readable payload such as:

```json
{
  "action": "change_top_n",
  "parameters": {
    "top_n": 10
  }
}
```

---

## 13. Copilot Tool Output

The Copilot-facing MCP tool should return:

- the neutral visual payload;
- Adaptive Card JSON;
- concise plain-text fallback.

Suggested structured response:

```json
{
  "business_result": {
    "title": "...",
    "summary": "...",
    "visual_type": "...",
    "category_field": "...",
    "series": [],
    "rows": [],
    "suggested_actions": []
  },
  "adaptive_card": {},
  "fallback_text": "..."
}
```

Do not return SQL in this public payload.

---

## 14. Docker and Azure App Service

Create a production-like Dockerfile that installs:

- Python;
- Microsoft ODBC Driver for SQL Server;
- unixODBC dependencies;
- pinned Python packages;
- the application.

Requirements:

- non-root execution where practical;
- no secrets in image;
- clear startup command;
- health check;
- small and maintainable image;
- `.dockerignore`;
- local Docker run instructions.

Azure target:

```text
Azure App Service for Containers
```

Use App Service because the proof of concept will use Azure Hybrid Connections to reach SQL Server Express on the laptop.

---

## 15. Laptop SQL Server Express Preparation

Document the exact manual steps required:

1. enable TCP/IP for the SQL Express instance;
2. assign a fixed port, for example `14330`;
3. restart SQL Server;
4. test locally with `Test-NetConnection`;
5. enable SQL authentication if required;
6. create a dedicated read-only login;
7. grant access to WideWorldImporters;
8. test the login locally;
9. install Hybrid Connection Manager;
10. keep the laptop, SQL Server, and Hybrid Connection Manager running during tests.

Suggested proof-of-concept SQL identity:

```text
mcp_readonly
```

The guide must remind the user not to place the password in source control.

---

## 16. Azure Hybrid Connection

Document:

- creating the App Service;
- creating the Hybrid Connection;
- configuring laptop hostname and fixed SQL port;
- installing and registering Hybrid Connection Manager;
- confirming Connected status;
- configuring App Service environment variables;
- testing `/health`;
- testing database reachability.

The project must not require exposing SQL Server directly to the public internet.

---

## 17. Copilot Studio Setup

Create a step-by-step guide covering:

1. create a Copilot Studio agent;
2. configure business-user instructions;
3. add the Streamable HTTP MCP server;
4. configure authentication;
5. discover and enable tools;
6. map the structured MCP response;
7. display Adaptive Card output;
8. handle action submissions;
9. test in Copilot Studio;
10. publish to Microsoft 365 Copilot or Teams.

For the first POC, support API-key authentication if that is the fastest viable route, but structure the code so Entra ID OAuth can replace it later.

Do not hard-code the API key.

---

## 18. Testing Requirements

### Unit tests

Cover:

- read-only SQL validation;
- forbidden keyword detection;
- multiple statement rejection;
- cross-database rejection;
- visual validation;
- chart fallback;
- empty result handling;
- value formatting;
- Adaptive Card schema shape;
- action payload generation;
- environment validation.

### Integration tests

Use mocked database results for:

- top five outstanding balances;
- monthly invoiced sales trend;
- total invoiced sales KPI;
- recent invoice detail table;
- small part-to-whole analysis;
- invalid chart request;
- empty result;
- SQL execution failure.

### Manual acceptance tests

#### Test A: Ranking

Question:

> What are the top five outstanding customer balances?

Expected:

- horizontal bar;
- business summary;
- no SQL;
- underlying values available;
- Show top 10 action.

#### Test B: Trend

Question:

> How have monthly invoiced sales changed over time?

Expected:

- line chart;
- chronological x-axis;
- short trend observation;
- no SQL.

#### Test C: KPI

Question:

> What is total invoiced sales?

Expected:

- KPI card;
- currency formatting;
- no SQL.

#### Test D: Detailed records

Question:

> Show the 20 most recent invoices.

Expected:

- table;
- short summary;
- no chart unless clearly useful;
- no SQL.

#### Test E: Copilot round trip

Expected path:

```text
Copilot Studio
→ Streamable HTTP MCP
→ Azure App Service
→ Hybrid Connection
→ SQL Server Express
→ Adaptive Card response
```

---

## 19. Delivery Milestones

### Milestone 1 — Behaviour-preserving refactor

- modular structure;
- current Cursor functionality still works;
- no Azure work yet.

### Milestone 2 — Shared visual contract

- `VisualResponse`;
- existing Cursor renderer consumes it;
- tests added.

### Milestone 3 — Adaptive Card renderer

- KPI;
- horizontal bar;
- vertical bar;
- line;
- pie;
- doughnut;
- table;
- fallback.

### Milestone 4 — Local Streamable HTTP

- HTTP MCP server;
- `/health`;
- local test guide.

### Milestone 5 — Containerisation

- Dockerfile;
- ODBC installation;
- local container test.

### Milestone 6 — Azure App Service

- deployment;
- configuration;
- health test.

### Milestone 7 — Hybrid Connection

- Azure to laptop SQL connectivity;
- read-only SQL login;
- end-to-end query.

### Milestone 8 — Copilot Studio

- MCP onboarding;
- Adaptive Card rendering;
- action handling;
- natural-language test.

### Milestone 9 — POC completion

- all acceptance tests pass;
- documentation complete;
- known limitations recorded.

---

## 20. Definition of Done

The proof of concept is complete when:

1. Cursor still works through STDIO.
2. Copilot Studio can call the Azure-hosted MCP server.
3. Azure can query SQL Server Express on the laptop through Hybrid Connection.
4. A user can ask ordinary business questions.
5. The LLM chooses the appropriate visual automatically.
6. Adaptive Cards render KPI, ranking, trend, and table results.
7. SQL and technical workflow are hidden by default.
8. Underlying data is available where appropriate.
9. At least one interactive follow-up action works.
10. Tests, setup guides, and troubleshooting instructions are included.
11. Secrets are not committed to Git.
12. The repository can be rebuilt from documented instructions.

---

## 21. Important Working Rules for Codex

- Preserve the existing working Cursor implementation.
- Do not rewrite everything in one uncontrolled pass.
- Work milestone by milestone.
- Run tests after every milestone.
- Explain any manual setup required from the user.
- Do not assume Azure, SQL Server, Copilot Studio, or Hybrid Connection steps have been completed.
- Stop and provide exact instructions whenever user action is required.
- Never place secrets in code, tests, documentation examples, or Git history.
- Prefer small, reviewable commits.
- Update documentation as the implementation changes.
- Record assumptions and known limitations.
- Do not remove functionality merely to simplify the architecture.
