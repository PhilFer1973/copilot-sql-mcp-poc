# Copilot SQL MCP POC

Proof of concept for answering business questions over local SQL Server
WideWorldImporters data through MCP.

## Current Milestone

Milestone 4: Adaptive Card renderer.

Status:

- [x] Legacy Cursor implementation preserved in `legacy/`.
- [x] Shared app package created.
- [x] STDIO entry point added as `server_stdio.py`.
- [x] Existing MCP tool names preserved.
- [x] Existing Cursor MCP App resource URI preserved.
- [x] Data dictionary copied from the legacy implementation.
- [x] Cursor renderer copied from the legacy implementation.
- [x] Unit tests added for SQL validation and result handling.
- [x] Shared `VisualResponse` model added.
- [x] Cursor visual results now pass through the neutral model.
- [x] Cursor renderer can normalize `visual_response` payloads.
- [x] SQL remains excluded from public visual response payloads.
- [x] Adaptive Card renderer added for KPI, bar, horizontal bar, line, pie,
  doughnut, table, and fallback outputs.
- [x] Copilot-facing output helper added with business result, Adaptive Card,
  and fallback text.
- [ ] Manual Cursor acceptance questions verified against live SQL Server.

## Local STDIO Server

Run the refactored Cursor-compatible MCP server with:

```powershell
python server_stdio.py
```

The original working implementation remains available at:

```text
legacy/sqlserver_mcp_wwi_cursor_apps_business.py
```

## Configuration

The refactored server keeps the legacy local defaults:

- `SQLSERVER_HOST`, default `050027346-3`
- `SQLSERVER_DB`, default `WideWorldImporters`
- `SQLSERVER_USER`, optional
- `SQLSERVER_PASS`, optional legacy password variable
- `SQLSERVER_PASSWORD`, optional preferred password variable
- `SQLSERVER_DRIVER`, default `ODBC Driver 17 for SQL Server`

If no SQL user/password is provided, the connection uses Windows trusted
authentication, matching the legacy Cursor setup.

Local state files default to the `legacy/` directory for compatibility:

- `mcp_memory.txt`
- `mcp_pending_suggestions.txt`
- `mcp_queries.log`

Override that directory with `MCP_STATE_DIR` if needed.

## Tests

The current tests use the Python standard library and do not require a live SQL
Server:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

Manual Cursor and SQL Server acceptance checks are listed in
`docs/acceptance_tests.md`.

The shared visual contract is summarized in `docs/visual_contract.md`.
Adaptive Card rendering notes are in `docs/adaptive_card_examples.md`.
