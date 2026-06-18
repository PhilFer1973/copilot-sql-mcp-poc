"""Configuration helpers for local Cursor-compatible SQL Server access."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LEGACY_DIR = PROJECT_ROOT / "legacy"


@dataclass(frozen=True)
class DatabaseConfig:
    host: str
    database: str
    user: str = ""
    password: str = ""
    driver: str = "ODBC Driver 17 for SQL Server"
    trust_server_certificate: bool = True
    timeout_seconds: int = 15


@dataclass(frozen=True)
class AppPaths:
    memory_file: Path
    pending_file: Path
    log_file: Path


@dataclass(frozen=True)
class HttpServerConfig:
    host: str = "0.0.0.0"
    port: int = 8000
    mcp_path: str = "/mcp"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"


def get_database_config() -> DatabaseConfig:
    """Read the legacy-compatible database configuration from the environment."""
    return DatabaseConfig(
        host=os.environ.get("SQLSERVER_HOST", "050027346-3"),
        database=os.environ.get("SQLSERVER_DB", "WideWorldImporters"),
        user=os.environ.get("SQLSERVER_USER", ""),
        password=os.environ.get(
            "SQLSERVER_PASSWORD",
            os.environ.get("SQLSERVER_PASS", ""),
        ),
        driver=os.environ.get("SQLSERVER_DRIVER", "ODBC Driver 17 for SQL Server"),
        timeout_seconds=int(os.environ.get("QUERY_TIMEOUT_SECONDS", "15")),
    )


def get_http_server_config() -> HttpServerConfig:
    """Read local Streamable HTTP server settings from the environment."""
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    if log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        log_level = "INFO"

    mcp_path = os.environ.get("MCP_HTTP_PATH", "/mcp")
    if not mcp_path.startswith("/"):
        mcp_path = "/" + mcp_path

    return HttpServerConfig(
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8000")),
        mcp_path=mcp_path,
        log_level=log_level,  # type: ignore[arg-type]
    )


def get_app_paths() -> AppPaths:
    """Return state file paths, defaulting to the legacy script directory."""
    state_dir = Path(os.environ.get("MCP_STATE_DIR", str(LEGACY_DIR)))
    return AppPaths(
        memory_file=state_dir / "mcp_memory.txt",
        pending_file=state_dir / "mcp_pending_suggestions.txt",
        log_file=state_dir / "mcp_queries.log",
    )


def build_connection_string(config: DatabaseConfig) -> str:
    """Build the same ODBC connection string shape used by the legacy server."""
    trust = "yes" if config.trust_server_certificate else "no"
    base = (
        f"DRIVER={{{config.driver}}};"
        f"SERVER={config.host};"
        f"DATABASE={config.database};"
    )

    if config.user and config.password:
        return (
            base
            + f"UID={config.user};"
            + f"PWD={config.password};"
            + f"TrustServerCertificate={trust};"
        )

    return base + "Trusted_Connection=yes;" + f"TrustServerCertificate={trust};"
