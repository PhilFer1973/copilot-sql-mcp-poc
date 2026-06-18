"""Health and diagnostics helpers for HTTP hosting."""

from __future__ import annotations

from typing import Any

from . import __version__
from .database import DatabaseClient


def build_health_payload(database_client: DatabaseClient) -> tuple[dict[str, Any], int]:
    """Return a safe health payload and HTTP status code."""
    try:
        database_client.run_query("SELECT 1 AS health_check", max_rows=1)
        return (
            {
                "status": "healthy",
                "database": "reachable",
                "version": __version__,
            },
            200,
        )
    except Exception:
        return (
            {
                "status": "degraded",
                "database": "unreachable",
                "version": __version__,
            },
            503,
        )
