# Local Streamable HTTP Server

Milestone 5 adds a second entry point:

```text
server_http.py
```

The existing Cursor STDIO entry point remains:

```text
server_stdio.py
```

## Run Locally

```powershell
python server_http.py
```

Defaults:

- Host: `0.0.0.0`
- Port: `8000`
- MCP endpoint: `/mcp`
- Health endpoint: `/health`

Environment variables:

- `PORT`: HTTP port.
- `HOST`: HTTP bind host, default `0.0.0.0`.
- `MCP_HTTP_PATH`: MCP endpoint path, default `/mcp`.
- `LOG_LEVEL`: `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`.

Example:

```powershell
$env:PORT = "9001"
python server_http.py
```

Then test:

```text
http://localhost:9001/health
```

## Health Response

Healthy:

```json
{
  "status": "healthy",
  "database": "reachable",
  "version": "0.1.0"
}
```

Database unavailable:

```json
{
  "status": "degraded",
  "database": "unreachable",
  "version": "0.1.0"
}
```

The health endpoint does not expose passwords, connection strings, local paths,
SQL text, or database exception details.

## MCP Tools

The HTTP server uses the same shared MCP registration as STDIO. It exposes the
legacy tools plus the Copilot-facing visual payload tool:

- `sqlserver_get_schema`
- `sqlserver_query`
- `sqlserver_memory_read`
- `sqlserver_memory_suggest`
- `sqlserver_visual_query`
- `sqlserver_copilot_visual_query`

`sqlserver_copilot_visual_query` returns:

```json
{
  "business_result": {},
  "adaptive_card": {},
  "fallback_text": "..."
}
```

SQL is still excluded from public payloads.
