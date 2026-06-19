"""Database access for SQL Server query execution."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pyodbc

from .config import build_connection_string, get_database_config
from .logging_config import log_query


QueryLogger = Callable[[str, int], None]


class DatabaseClient:
    """Small pyodbc wrapper that preserves the legacy fetch/log behavior."""

    def __init__(
        self,
        connection_string: str | None = None,
        timeout_seconds: int | None = None,
        max_query_rows: int | None = None,
        query_logger: QueryLogger = log_query,
    ) -> None:
        config = get_database_config()
        self.connection_string = connection_string or build_connection_string(config)
        self.timeout_seconds = timeout_seconds or config.timeout_seconds
        self.max_query_rows = max_query_rows or config.max_query_rows
        self.approved_schemas = config.approved_schemas
        self.query_logger = query_logger

    def get_connection(self):
        """Open and return a pyodbc connection."""
        return pyodbc.connect(self.connection_string, timeout=self.timeout_seconds)

    def run_query(self, sql: str, max_rows: int = 500) -> list[dict[str, Any]]:
        """Execute a SELECT query and return rows as a list of dictionaries."""
        effective_max_rows = min(max_rows, self.max_query_rows)
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            if hasattr(cursor, "timeout"):
                cursor.timeout = self.timeout_seconds
            cursor.execute(sql)
            columns = [col[0] for col in cursor.description]
            rows = [
                dict(zip(columns, row))
                for row in cursor.fetchmany(effective_max_rows)
            ]
            self.query_logger(sql, len(rows))
            return rows
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()


def run_query(sql: str, max_rows: int = 500) -> list[dict[str, Any]]:
    """Legacy-style module helper for simple call sites."""
    return DatabaseClient().run_query(sql, max_rows=max_rows)
