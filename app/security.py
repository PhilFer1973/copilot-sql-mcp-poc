"""Read-only SQL validation."""

from __future__ import annotations

import re
from typing import Optional

from .config import DEFAULT_APPROVED_SCHEMAS


FORBIDDEN_KEYWORDS = {
    "alter",
    "bulk",
    "create",
    "delete",
    "drop",
    "exec",
    "execute",
    "insert",
    "into",
    "merge",
    "truncate",
    "update",
}

SYSTEM_SCHEMAS = {"sys", "information_schema"}
SYSTEM_OBJECTS = {
    "syscolumns",
    "sysdatabases",
    "sysindexes",
    "sysobjects",
    "sysprocesses",
    "sysusers",
}


def validate_read_only_sql(
    sql: str,
    approved_schemas: tuple[str, ...] | None = DEFAULT_APPROVED_SCHEMAS,
) -> tuple[bool, Optional[str]]:
    """Validate that SQL is one read-only SELECT or CTE statement."""
    cleaned = sql.strip()
    if not cleaned:
        return False, "The SQL statement is empty."

    without_trailing = cleaned[:-1].rstrip() if cleaned.endswith(";") else cleaned
    if ";" in without_trailing:
        return False, "Only one SQL statement is permitted."

    lowered = without_trailing.lower()
    if not (lowered.startswith("select") or lowered.startswith("with")):
        return False, "The query must begin with SELECT or WITH."

    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{re.escape(keyword)}\b", lowered):
            return False, f"'{keyword.upper()}' is not permitted."

    if "--" in without_trailing or "/*" in without_trailing or "*/" in without_trailing:
        return False, "SQL comments are not permitted."

    cross_database_reference = re.search(
        r"(?<![\w\]])(?:\[?[A-Za-z_][\w $-]*\]?\s*\.\s*){2,}\[?[A-Za-z_][\w $-]*\]?",
        without_trailing,
        flags=re.IGNORECASE,
    )
    if cross_database_reference:
        return False, "Cross-database references are not permitted."

    if re.search(r"\b(?:sys|information_schema)\s*\.", lowered, re.IGNORECASE):
        return False, "System schemas are not permitted."

    for object_name in SYSTEM_OBJECTS:
        if re.search(rf"\b{re.escape(object_name)}\b", lowered):
            return False, "System tables are not permitted."

    configured_schemas = (
        approved_schemas if approved_schemas is not None else DEFAULT_APPROVED_SCHEMAS
    )
    schema_error = _validate_approved_schema_references(without_trailing, configured_schemas)
    if schema_error:
        return False, schema_error

    return True, None


def _validate_approved_schema_references(
    sql: str,
    approved_schemas: tuple[str, ...],
) -> Optional[str]:
    if not approved_schemas:
        return "No approved schemas are configured."

    approved = {schema.lower() for schema in approved_schemas}
    cte_names = _extract_cte_names(sql)

    for match in re.finditer(
        r"\b(?:from|join|apply)\s+([A-Za-z_#@][\w$#@]*|\[[^\]]+\])"
        r"(?:\s*\.\s*([A-Za-z_][\w$]*|\[[^\]]+\]))?",
        sql,
        flags=re.IGNORECASE,
    ):
        first_part = _normalize_identifier(match.group(1))
        second_part = _normalize_identifier(match.group(2)) if match.group(2) else None

        if first_part.startswith("@") or first_part.startswith("#"):
            continue

        if second_part is None:
            if first_part.lower() in cte_names:
                continue
            return (
                "Table references must use approved two-part schema names "
                "or a declared CTE name."
            )

        if first_part.lower() in SYSTEM_SCHEMAS:
            return "System schemas are not permitted."

        if first_part.lower() not in approved:
            return f"Schema '{first_part}' is not approved for querying."

    return None


def _extract_cte_names(sql: str) -> set[str]:
    names: set[str] = set()
    if not re.match(r"^\s*with\b", sql, flags=re.IGNORECASE):
        return names

    for match in re.finditer(
        r"(?:with|,)\s*([A-Za-z_][\w$]*|\[[^\]]+\])\s+as\s*\(",
        sql,
        flags=re.IGNORECASE,
    ):
        names.add(_normalize_identifier(match.group(1)).lower())
    return names


def _normalize_identifier(identifier: str | None) -> str:
    if not identifier:
        return ""
    stripped = identifier.strip()
    if stripped.startswith("[") and stripped.endswith("]"):
        return stripped[1:-1]
    return stripped
