"""Health and diagnostics helpers for HTTP hosting."""

from __future__ import annotations

import logging
import re
from typing import Any

from . import __version__
from .database import DatabaseClient


logger = logging.getLogger(__name__)
_SECRET_PATTERNS = (
    re.compile(r"(?i)(PWD|Password|SQLSERVER_PASSWORD)\s*=\s*([^;\s]+)"),
)


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
    except Exception as error:
        logger.warning(
            "Health database check failed: %s",
            _safe_exception_summary(error),
        )
        return (
            {
                "status": "degraded",
                "database": "unreachable",
                "version": __version__,
            },
            503,
        )


def _safe_exception_summary(error: Exception) -> str:
    """Return a bounded, redacted exception summary for server logs only."""
    message = f"{type(error).__name__}: {error}"
    for pattern in _SECRET_PATTERNS:
        message = pattern.sub(r"\1=<redacted>", message)
    return message[:1000]
