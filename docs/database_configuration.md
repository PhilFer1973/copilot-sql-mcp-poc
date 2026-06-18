# Database Configuration

Milestone 6 keeps the current local Cursor behavior while adding the
configuration needed for later Azure-to-laptop testing.

## Environment Variables

Local defaults:

```text
SQLSERVER_HOST=050027346-3
SQLSERVER_DB=WideWorldImporters
SQLSERVER_AUTH_MODE=windows
SQLSERVER_DRIVER=ODBC Driver 17 for SQL Server
SQLSERVER_ENCRYPT=no
SQLSERVER_TRUST_CERT=yes
QUERY_TIMEOUT_SECONDS=15
MAX_QUERY_ROWS=500
SQLSERVER_APPROVED_SCHEMAS=Application,Sales,Purchasing,Warehouse
```

Optional:

```text
SQLSERVER_PORT=
SQLSERVER_USER=
SQLSERVER_PASSWORD=
LOG_LEVEL=INFO
```

`SQLSERVER_PASS` is still accepted as a legacy password variable, but
`SQLSERVER_PASSWORD` is preferred.

## Authentication Modes

`SQLSERVER_AUTH_MODE=windows`

- Uses `Trusted_Connection=yes`.
- Preserves the current local Cursor setup.
- Does not require `SQLSERVER_USER` or `SQLSERVER_PASSWORD`.

`SQLSERVER_AUTH_MODE=sql`

- Uses `UID` and `PWD`.
- Requires `SQLSERVER_USER` and `SQLSERVER_PASSWORD`.
- Intended for the later Azure App Service to Hybrid Connection proof of concept.

Never commit real passwords.

## SQL Safety Controls

The validator allows only one `SELECT` or CTE statement. It rejects:

- multiple statements
- SQL comments
- write keywords, including `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`,
  `CREATE`, `EXEC`, `MERGE`, `TRUNCATE`, `BULK`
- `SELECT INTO`
- cross-database references
- system schemas such as `sys` and `INFORMATION_SCHEMA`
- common system tables such as `sysobjects`
- schema-qualified tables outside the approved schema allow-list
- unqualified table names, except declared CTE names

The default approved schemas are:

```text
Application
Sales
Purchasing
Warehouse
```

Schema discovery still uses SQL Server system views internally. The restrictions
above apply to LLM-generated analytical SQL.

## Row and Timeout Controls

- `QUERY_TIMEOUT_SECONDS` sets the ODBC connection and cursor timeout.
- `MAX_QUERY_ROWS` caps result rows even if a tool requests more.

The database should still use a read-only SQL identity for any remote/Azure
scenario. This code is a guardrail, not the only security boundary.
