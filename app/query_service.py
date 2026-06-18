"""Query execution and result formatting."""

from __future__ import annotations

import json
from typing import Any

import pyodbc

from .database import DatabaseClient
from .security import validate_read_only_sql


def to_markdown_table(rows: list[dict[str, Any]]) -> str:
    """Convert a list of dictionaries to a markdown table."""
    if not rows:
        return "_No rows returned._"

    headers = list(rows[0].keys())
    separator = " | ".join(["---"] * len(headers))
    header = " | ".join(headers)
    body = "\n".join(
        " | ".join(str(row.get(header_name, "")) for header_name in headers)
        for row in rows
    )
    return f"{header}\n{separator}\n{body}"


class QueryService:
    """Validate, execute, and format SQL query results."""

    def __init__(
        self,
        database_client: DatabaseClient,
        max_query_rows: int | None = None,
    ) -> None:
        self.database_client = database_client
        self.max_query_rows = max_query_rows or getattr(
            database_client,
            "max_query_rows",
            500,
        )
        self.approved_schemas = getattr(database_client, "approved_schemas", None)

    def run_rows(self, sql: str, max_rows: int = 500) -> list[dict[str, Any]]:
        effective_max_rows = min(max_rows, self.max_query_rows)
        return self.database_client.run_query(sql, max_rows=effective_max_rows)

    def execute_text(self, sql: str, max_rows: int = 100, output_format: str = "markdown") -> str:
        valid, validation_error = validate_read_only_sql(
            sql,
            approved_schemas=self.approved_schemas,
        )
        if not valid:
            return f"Rejected: {validation_error}"

        try:
            effective_max_rows = min(max_rows, self.max_query_rows)
            rows = self.run_rows(sql, max_rows=effective_max_rows)
            row_count = f"_{len(rows)} row(s) returned"
            row_count += (
                " (limit reached - refine your query to see more)"
                if len(rows) == effective_max_rows
                else "._"
            )

            if output_format == "json":
                return row_count + "\n\n" + json.dumps(rows, indent=2, default=str)

            return row_count + "\n\n" + to_markdown_table(rows)

        except pyodbc.Error as error:
            return (
                f"SQL Error: {error}\n\n"
                "Suggestions:\n"
                "- Run sqlserver_get_schema to verify table and column names\n"
                "- Check the DATA DICTIONARY for correct join columns\n"
                "- Confirm status filter values against the system values section"
            )
        except Exception as error:
            return f"Unexpected error: {error}"
