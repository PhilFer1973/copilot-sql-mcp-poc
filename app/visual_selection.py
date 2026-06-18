"""Validation and payload building for Cursor visual results."""

from __future__ import annotations

from typing import Any, Literal


VisualType = Literal[
    "table",
    "kpi",
    "bar",
    "horizontal_bar",
    "line",
    "scatter",
    "pie",
    "doughnut",
]

ValueFormat = Literal["number", "currency", "percent"]


def is_numeric(value: Any) -> bool:
    """Return True when a value can safely be treated as numeric."""
    if value is None or isinstance(value, bool):
        return False
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def validate_visual_choice(
    requested_type: VisualType,
    rows: list[dict[str, Any]],
    x_field: str | None,
    y_fields: list[str],
) -> tuple[VisualType, str | None]:
    """Validate an LLM-selected visual and return a safe fallback if needed."""
    if not rows:
        return "table", "No rows were returned, so a table fallback was used."

    columns = list(rows[0].keys())

    if requested_type == "table":
        return "table", None

    if requested_type == "kpi":
        if len(rows) == 1 and len(y_fields) == 1 and y_fields[0] in columns:
            if is_numeric(rows[0].get(y_fields[0])):
                return "kpi", None
        return "table", "KPI output requires one returned row and one numeric y-field."

    if not x_field or x_field not in columns:
        return "table", "The selected x_field was not present in the result."

    if not y_fields:
        return "table", "At least one y-field is required for this visual."

    missing = [field for field in y_fields if field not in columns]
    if missing:
        return (
            "table",
            "The following y-fields were not present in the result: " + ", ".join(missing),
        )

    if requested_type == "scatter":
        if len(y_fields) != 1:
            return "table", "Scatter charts require one x-field and one y-field."
        if any(
            not is_numeric(row.get(x_field)) or not is_numeric(row.get(y_fields[0]))
            for row in rows
        ):
            return "table", "Scatter x and y values must both be numeric."

    if requested_type in {"bar", "horizontal_bar", "line", "pie", "doughnut"}:
        for field in y_fields:
            if any(not is_numeric(row.get(field)) for row in rows):
                return "table", f"Field '{field}' was not consistently numeric."

    if requested_type in {"pie", "doughnut"}:
        if len(y_fields) != 1:
            return "table", "Pie and doughnut charts require one y-field."
        if len(rows) > 8:
            return (
                "horizontal_bar",
                "More than eight categories were returned; a horizontal bar "
                "chart is more readable.",
            )
        if any(float(row[y_fields[0]]) < 0 for row in rows):
            return (
                "bar",
                "Negative values cannot be represented meaningfully in a "
                "pie or doughnut chart.",
            )

    if requested_type == "bar" and len(rows) >= 10:
        return (
            "horizontal_bar",
            "Ten or more categories were returned; horizontal bars are more readable.",
        )

    return requested_type, None


def build_visual_payload(
    title: str,
    reason: str,
    visual_type: VisualType,
    rows: list[dict[str, Any]],
    x_field: str | None,
    y_fields: list[str],
    value_format: ValueFormat,
    currency_code: str,
) -> dict[str, Any]:
    """Build and validate the JSON payload consumed by the Cursor MCP App."""
    columns = list(rows[0].keys()) if rows else []
    final_type, fallback_reason = validate_visual_choice(
        visual_type,
        rows,
        x_field,
        y_fields,
    )

    final_reason = reason
    if fallback_reason:
        final_reason = f"{reason} Server fallback: {fallback_reason}"

    return {
        "title": title,
        "reason": final_reason,
        "visual_type": final_type,
        "x_field": x_field,
        "y_fields": y_fields,
        "value_format": value_format,
        "currency_code": currency_code.upper(),
        "columns": columns,
        "row_count": len(rows),
        "rows": rows,
    }


_is_numeric = is_numeric
_validate_visual_choice = validate_visual_choice
_build_visual_payload = build_visual_payload
