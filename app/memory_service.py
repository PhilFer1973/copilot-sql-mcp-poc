"""Reviewed schema memory and pending suggestion storage."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


class MemoryService:
    """Read approved memory and write pending user-review suggestions."""

    def __init__(self, memory_file: Path, pending_file: Path) -> None:
        self.memory_file = memory_file
        self.pending_file = pending_file

    def read(self) -> str:
        if not self.memory_file.exists():
            return (
                "No accumulated memory found. This is normal for a first session. "
                "Use sqlserver_memory_suggest to flag any schema discoveries during "
                "this session for review."
            )

        content = self.memory_file.read_text(encoding="utf-8").strip()
        if not content:
            return "Memory file exists but contains no entries yet."

        return (
            "=== ACCUMULATED SCHEMA KNOWLEDGE (reviewed and approved) ===\n\n"
            + content
            + "\n\n=== END OF ACCUMULATED MEMORY ==="
        )

    def suggest(
        self,
        category: str,
        observation: str,
        confidence: str,
        source_query: str | None = None,
    ) -> str:
        valid_categories = {"join", "pattern", "rule", "correction"}
        valid_confidences = {"high", "medium", "low"}

        if category not in valid_categories:
            return (
                f"Invalid category '{category}'. "
                f"Must be one of: {', '.join(sorted(valid_categories))}."
            )

        if confidence not in valid_confidences:
            return (
                f"Invalid confidence '{confidence}'. "
                f"Must be one of: {', '.join(sorted(valid_confidences))}."
            )

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            f"{'-' * 72}",
            f"DATE:       {timestamp}",
            f"CATEGORY:   {category.upper()}",
            f"CONFIDENCE: {confidence.upper()}",
            "",
            "OBSERVATION:",
            observation,
        ]

        if source_query:
            lines += ["", "SOURCE QUERY:", source_query.strip()]

        lines += [
            "",
            "STATUS: PENDING REVIEW",
            "  -> If correct, copy the OBSERVATION above into mcp_memory.txt",
            "  -> If incorrect, delete this entry",
            f"{'-' * 72}",
            "",
        ]

        entry = "\n".join(lines)
        self.pending_file.parent.mkdir(parents=True, exist_ok=True)
        with self.pending_file.open("a", encoding="utf-8") as handle:
            handle.write(entry)

        return (
            f"Suggestion written to pending review file: {self.pending_file.name}\n"
            f"Category: {category} | Confidence: {confidence}\n\n"
            "This will not affect active memory until you review and approve it."
        )
