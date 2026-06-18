"""Streamable HTTP entry point for local and future Azure-hosted MCP use."""

from __future__ import annotations

from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import HttpServerConfig, get_http_server_config
from app.database import DatabaseClient
from app.health import build_health_payload
from app.mcp_tools import create_mcp


def create_http_mcp(
    database_client: DatabaseClient | None = None,
    config: HttpServerConfig | None = None,
):
    """Create the Streamable HTTP MCP server with a public health endpoint."""
    resolved_config = config or get_http_server_config()
    resolved_database = database_client or DatabaseClient()

    mcp = create_mcp(
        database_client=resolved_database,
        fastmcp_kwargs={
            "host": resolved_config.host,
            "port": resolved_config.port,
            "streamable_http_path": resolved_config.mcp_path,
            "log_level": resolved_config.log_level,
        },
    )

    @mcp.custom_route("/health", methods=["GET"], include_in_schema=False)
    async def health_check(request: Request) -> JSONResponse:
        payload, status_code = build_health_payload(resolved_database)
        return JSONResponse(payload, status_code=status_code)

    return mcp


mcp = create_http_mcp()


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
