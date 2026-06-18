"""Internal query logging helpers."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .config import get_app_paths


def log_query(sql: str, row_count: int, log_file: Path | None = None) -> None:
    """Append a timestamped query record to the internal query log."""
    target = log_file or get_app_paths().log_file
    target.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] ROWS: {row_count} | SQL: {sql.strip()}\n"
    with target.open("a", encoding="utf-8") as handle:
        handle.write(entry)
