"""Live SQL Server schema discovery."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


RunQuery = Callable[[str, int], list[dict[str, Any]]]


class SchemaService:
    """Read live table, column, and declared FK structure from SQL Server."""

    def __init__(self, run_query: RunQuery) -> None:
        self.run_query = run_query

    def get_schema(self, table_filter: str | None = None) -> str:
        try:
            filter_clause = ""
            if table_filter:
                safe = table_filter.replace("'", "")
                filter_clause = (
                    f"AND (c.TABLE_SCHEMA LIKE '%{safe}%' "
                    f"OR c.TABLE_NAME LIKE '%{safe}%' "
                    f"OR CONCAT(c.TABLE_SCHEMA, '.', c.TABLE_NAME) LIKE '%{safe}%')"
                )

            column_sql = f"""
            SELECT
                c.TABLE_SCHEMA,
                c.TABLE_NAME,
                c.COLUMN_NAME,
                c.DATA_TYPE,
                c.CHARACTER_MAXIMUM_LENGTH  AS max_length,
                c.IS_NULLABLE,
                CASE
                    WHEN kcu.COLUMN_NAME IS NOT NULL THEN 'PK'
                    ELSE ''
                END AS key_type
            FROM INFORMATION_SCHEMA.COLUMNS c
            LEFT JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
                ON  c.TABLE_NAME  = kcu.TABLE_NAME
                AND c.COLUMN_NAME = kcu.COLUMN_NAME
                AND EXISTS (
                    SELECT 1
                    FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
                    WHERE tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
                      AND tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
                )
            WHERE c.TABLE_SCHEMA NOT IN ('sys', 'INFORMATION_SCHEMA')
            {filter_clause}
            ORDER BY c.TABLE_SCHEMA, c.TABLE_NAME, c.ORDINAL_POSITION
        """
            columns = self.run_query(column_sql, 2000)

            fk_sql = """
            SELECT
                sp.name  AS parent_schema,
                tp.name  AS parent_table,
                cp.name  AS parent_column,
                sr.name  AS referenced_schema,
                tr.name  AS referenced_table,
                cr.name  AS referenced_column
            FROM sys.foreign_keys           fk
            JOIN sys.tables              tp ON fk.parent_object_id      = tp.object_id
            JOIN sys.schemas             sp ON tp.schema_id             = sp.schema_id
            JOIN sys.tables              tr ON fk.referenced_object_id  = tr.object_id
            JOIN sys.schemas             sr ON tr.schema_id             = sr.schema_id
            JOIN sys.foreign_key_columns fc ON fk.object_id             = fc.constraint_object_id
            JOIN sys.columns             cp ON fc.parent_object_id      = cp.object_id
                                           AND fc.parent_column_id      = cp.column_id
            JOIN sys.columns             cr ON fc.referenced_object_id  = cr.object_id
                                           AND fc.referenced_column_id  = cr.column_id
            ORDER BY sp.name, tp.name, cp.name
        """
            fk_rows = self.run_query(fk_sql, 500)

            tables: dict[str, list[dict[str, Any]]] = {}
            for row in columns:
                full_table_name = f"{row['TABLE_SCHEMA']}.{row['TABLE_NAME']}"
                tables.setdefault(full_table_name, []).append(row)

            output = ["# Live Schema\n"]
            for table_name, table_columns in tables.items():
                output.append(f"## {table_name}")
                for column in table_columns:
                    length = f"({column['max_length']})" if column["max_length"] else ""
                    pk = " [PK]" if column["key_type"] == "PK" else ""
                    null = " NULL" if column["IS_NULLABLE"] == "YES" else " NOT NULL"
                    output.append(
                        f"  - {column['COLUMN_NAME']}: "
                        f"{column['DATA_TYPE']}{length}{pk}{null}"
                    )
                output.append("")

            if fk_rows:
                output.append("## Declared FK Constraints")
                for fk in fk_rows:
                    output.append(
                        f"  - {fk['parent_schema']}.{fk['parent_table']}."
                        f"{fk['parent_column']} -> {fk['referenced_schema']}."
                        f"{fk['referenced_table']}.{fk['referenced_column']}"
                    )
                output.append("")

            output.append(
                "_Note: joins not listed above are documented in the DATA DICTIONARY._"
            )
            return "\n".join(output)

        except Exception as error:
            return f"Error reading schema: {error}"
