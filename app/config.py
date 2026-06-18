"""Configuration helpers for local Cursor-compatible SQL Server access."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LEGACY_DIR = PROJECT_ROOT / "legacy"
DEFAULT_APPROVED_SCHEMAS = ("Application", "Sales", "Purchasing", "Warehouse")


class ConfigError(ValueError):
    """Raised when required runtime configuration is invalid."""


@dataclass(frozen=True)
class DatabaseConfig:
    host: str
    database: str
    port: int | None = None
    user: str = ""
    password: str = ""
    driver: str = "ODBC Driver 17 for SQL Server"
    encrypt: bool = False
    trust_server_certificate: bool = True
    auth_mode: Literal["windows", "sql"] = "windows"
    timeout_seconds: int = 15
    max_query_rows: int = 500
    approved_schemas: tuple[str, ...] = DEFAULT_APPROVED_SCHEMAS


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
    user = os.environ.get("SQLSERVER_USER", "")
    password = os.environ.get(
        "SQLSERVER_PASSWORD",
        os.environ.get("SQLSERVER_PASS", ""),
    )
    auth_mode = os.environ.get("SQLSERVER_AUTH_MODE", "").lower()
    if not auth_mode:
        auth_mode = "sql" if user or password else "windows"

    approved_schemas = tuple(
        schema.strip()
        for schema in os.environ.get(
            "SQLSERVER_APPROVED_SCHEMAS",
            ",".join(DEFAULT_APPROVED_SCHEMAS),
        ).split(",")
        if schema.strip()
    )

    return DatabaseConfig(
        host=os.environ.get("SQLSERVER_HOST", "050027346-3"),
        database=os.environ.get("SQLSERVER_DB", "WideWorldImporters"),
        port=_optional_int(os.environ.get("SQLSERVER_PORT"), "SQLSERVER_PORT"),
        user=user,
        password=password,
        driver=os.environ.get("SQLSERVER_DRIVER", "ODBC Driver 17 for SQL Server"),
        encrypt=_bool_from_env("SQLSERVER_ENCRYPT", default=False),
        trust_server_certificate=_bool_from_env("SQLSERVER_TRUST_CERT", default=True),
        auth_mode=auth_mode,  # type: ignore[arg-type]
        timeout_seconds=_positive_int("QUERY_TIMEOUT_SECONDS", default=15),
        max_query_rows=_positive_int("MAX_QUERY_ROWS", default=500),
        approved_schemas=approved_schemas or DEFAULT_APPROVED_SCHEMAS,
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
    validate_database_config(config)

    server = config.host if config.port is None else f"{config.host},{config.port}"
    encrypt = "yes" if config.encrypt else "no"
    trust = "yes" if config.trust_server_certificate else "no"
    base = (
        f"DRIVER={{{config.driver}}};"
        f"SERVER={server};"
        f"DATABASE={config.database};"
        f"Encrypt={encrypt};"
    )

    if config.auth_mode == "sql":
        return (
            base
            + f"UID={config.user};"
            + f"PWD={config.password};"
            + f"TrustServerCertificate={trust};"
        )

    return base + "Trusted_Connection=yes;" + f"TrustServerCertificate={trust};"


def validate_database_config(config: DatabaseConfig) -> None:
    """Validate database settings before opening a connection."""
    errors: list[str] = []

    if not config.host.strip():
        errors.append("SQLSERVER_HOST is required.")
    if not config.database.strip():
        errors.append("SQLSERVER_DB is required.")
    if config.auth_mode not in {"windows", "sql"}:
        errors.append("SQLSERVER_AUTH_MODE must be 'windows' or 'sql'.")
    if config.auth_mode == "sql":
        if not config.user:
            errors.append("SQLSERVER_USER is required when SQLSERVER_AUTH_MODE=sql.")
        if not config.password:
            errors.append("SQLSERVER_PASSWORD is required when SQLSERVER_AUTH_MODE=sql.")
    if config.timeout_seconds < 1:
        errors.append("QUERY_TIMEOUT_SECONDS must be greater than zero.")
    if config.max_query_rows < 1:
        errors.append("MAX_QUERY_ROWS must be greater than zero.")
    if not config.approved_schemas:
        errors.append("At least one approved schema is required.")

    if errors:
        raise ConfigError(" ".join(errors))


def _positive_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value in {None, ""}:
        return default
    try:
        parsed = int(value)
    except ValueError as error:
        raise ConfigError(f"{name} must be an integer.") from error
    if parsed < 1:
        raise ConfigError(f"{name} must be greater than zero.")
    return parsed


def _optional_int(value: str | None, name: str) -> int | None:
    if value in {None, ""}:
        return None
    try:
        parsed = int(value)
    except ValueError as error:
        raise ConfigError(f"{name} must be an integer.") from error
    if parsed < 1:
        raise ConfigError(f"{name} must be greater than zero.")
    return parsed


def _bool_from_env(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value in {None, ""}:
        return default

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise ConfigError(f"{name} must be a boolean value.")
