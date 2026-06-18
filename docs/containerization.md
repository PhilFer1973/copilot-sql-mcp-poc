# Containerisation

Milestone 7 adds a production-style Dockerfile for the HTTP MCP server.

The image runs:

```text
python server_http.py
```

It exposes:

- MCP Streamable HTTP endpoint: `/mcp`
- health endpoint: `/health`
- default port: `8000`

## What The Image Contains

- Python 3.12 slim Debian Bookworm base image
- Microsoft ODBC Driver 18 for SQL Server
- unixODBC development headers
- Kerberos/GSSAPI runtime library for Debian slim
- pinned Python requirements
- the refactored `app/` package
- `server_http.py`

It does not contain secrets.

## Build

This step downloads the Python base image and Microsoft/Linux packages, so run
it only when you are ready for Docker to access the network:

```powershell
docker build -t copilot-sql-mcp-poc:local .
```

## Run With Windows Authentication

Windows trusted authentication from a Linux container is not the default local
path. Use `server_stdio.py` on Windows for the existing Cursor setup.

## Run With SQL Authentication

For the later Azure-to-laptop proof of concept, use a dedicated read-only SQL
login and pass settings at runtime. Do not bake secrets into the image.

Example:

```powershell
docker run --rm -p 8000:8000 `
  -e SQLSERVER_HOST=host.docker.internal `
  -e SQLSERVER_PORT=14330 `
  -e SQLSERVER_DB=WideWorldImporters `
  -e SQLSERVER_AUTH_MODE=sql `
  -e SQLSERVER_USER=mcp_readonly `
  -e SQLSERVER_PASSWORD="<set locally, do not commit>" `
  -e SQLSERVER_DRIVER="ODBC Driver 18 for SQL Server" `
  -e SQLSERVER_ENCRYPT=yes `
  -e SQLSERVER_TRUST_CERT=yes `
  copilot-sql-mcp-poc:local
```

Then test:

```text
http://localhost:8000/health
```

## Notes

- The container health check calls `/health`.
- `/health` reports `degraded` if the database is unreachable.
- Runtime state files are written under `/app/legacy` unless `MCP_STATE_DIR` is
  set to a mounted writable directory.
- Use environment variables or a local, uncommitted env file for secrets.

Microsoft's current Linux installation guidance for ODBC Driver 18 documents the
Debian package repository flow used by this Dockerfile.
