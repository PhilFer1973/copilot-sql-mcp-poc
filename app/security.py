"""Read-only SQL validation."""

from __future__ import annotations

import re
from typing import Optional


FORBIDDEN_KEYWORDS = {
    "alter",
    "bulk",
    "create",
    "delete",
    "drop",
    "exec",
    "execute",
    "insert",
    "merge",
    "truncate",
    "update",
}


def validate_read_only_sql(sql: str) -> tuple[bool, Optional[str]]:
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

    return True, None
