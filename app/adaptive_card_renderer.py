"""Adaptive Card renderer for neutral visual responses."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from .response_models import SeriesDefinition, VisualResponse


ADAPTIVE_CARD_SCHEMA = "http://adaptivecards.io/schemas/adaptive-card.json"
ADAPTIVE_CARD_VERSION = "1.2"
MAX_CHART_CATEGORIES = 8
MAX_TABLE_ROWS = 8
MAX_TABLE_COLUMNS = 4
MAX_ACTIONS = 5


def render_adaptive_card(response: VisualResponse) -> dict[str, Any]:
    """Render a VisualResponse as deterministic Adaptive Card JSON."""
    body: list[dict[str, Any]] = [
        _text_block(response.title, weight="Bolder", size="Medium"),
        _text_block(response.summary, wrap=True, isSubtle=True),
    ]

    if not response.rows:
        body.append(_text_block("No rows were returned.", wrap=True))
    elif response.visual_type == "kpi":
        body.extend(_render_kpi(response))
    elif response.visual_type in {"bar", "horizontal_bar"}:
        body.extend(_render_bar_like(response))
    elif response.visual_type == "line":
        body.extend(_render_line(response))
    elif response.visual_type in {"pie", "doughnut"}:
        body.extend(_render_part_to_whole(response))
    elif response.visual_type == "table":
        body.extend(_render_table(response))
    else:
        body.extend(_render_fallback(response))

    body.extend(_render_data_note(response))

    card = {
        "$schema": ADAPTIVE_CARD_SCHEMA,
        "type": "AdaptiveCard",
        "version": ADAPTIVE_CARD_VERSION,
        "fallbackText": fallback_text(response),
        "body": body,
    }

    actions = _render_actions(response)
    if actions:
        card["actions"] = actions

    return card


def render_copilot_tool_output(response: VisualResponse) -> dict[str, Any]:
    """Return the Copilot-facing structured payload for one business result."""
    return {
        "business_result": response.public_payload(),
        "adaptive_card": render_adaptive_card(response),
        "fallback_text": fallback_text(response),
    }


def fallback_text(response: VisualResponse) -> str:
    """Build a concise plain-text fallback with no SQL or internal notes."""
    parts = [response.title, response.summary]
    if response.rows:
        parts.append(f"{len(response.rows)} row(s) returned.")
    else:
        parts.append("No rows were returned.")
    return "\n".join(part for part in parts if part)


def _render_kpi(response: VisualResponse) -> list[dict[str, Any]]:
    series = _primary_series(response)
    if not series:
        return _render_table(response)

    value = response.rows[0].get(series.field) if response.rows else None
    return [
        _text_block(
            _format_value(value, series),
            size="ExtraLarge",
            weight="Bolder",
            spacing="Medium",
            wrap=True,
        ),
        _text_block(series.name, isSubtle=True, wrap=True, spacing="None"),
    ]


def _render_bar_like(response: VisualResponse) -> list[dict[str, Any]]:
    series = _primary_series(response)
    if not series or not response.category_field:
        return _render_table(response)

    rows = _first_rows(response.rows, MAX_CHART_CATEGORIES)
    max_abs = _max_abs_value(rows, series.field)
    items: list[dict[str, Any]] = [
        _text_block(_chart_caption(response), isSubtle=True, wrap=True)
    ]

    for row in rows:
        label = _truncate(str(row.get(response.category_field, "")), 42)
        value = _decimal_or_none(row.get(series.field))
        bar = _bar_text(value, max_abs)
        items.append(
            {
                "type": "ColumnSet",
                "columns": [
                    {
                        "type": "Column",
                        "width": "stretch",
                        "items": [_text_block(label or "-", wrap=True)],
                    },
                    {
                        "type": "Column",
                        "width": "stretch",
                        "items": [
                            _text_block(
                                f"{bar} {_format_value(row.get(series.field), series)}",
                                wrap=True,
                            )
                        ],
                    },
                ],
            }
        )

    items.extend(_truncation_note(response.rows, MAX_CHART_CATEGORIES))
    return items


def _render_line(response: VisualResponse) -> list[dict[str, Any]]:
    series = _primary_series(response)
    if not series or not response.category_field:
        return _render_table(response)

    rows = _first_rows(response.rows, MAX_CHART_CATEGORIES)
    facts = [
        {
            "title": _truncate(str(row.get(response.category_field, "")), 28) + ":",
            "value": _format_value(row.get(series.field), series),
        }
        for row in rows
    ]

    body = [
        _text_block(
            "Line charts are represented as ordered points in this Adaptive Card.",
            isSubtle=True,
            wrap=True,
        ),
        {"type": "FactSet", "facts": facts},
    ]
    body.extend(_truncation_note(response.rows, MAX_CHART_CATEGORIES))
    return body


def _render_part_to_whole(response: VisualResponse) -> list[dict[str, Any]]:
    series = _primary_series(response)
    if not series or not response.category_field:
        return _render_table(response)

    rows = _first_rows(response.rows, MAX_CHART_CATEGORIES)
    total = sum(
        value
        for value in (_decimal_or_none(row.get(series.field)) for row in rows)
        if value is not None and value > 0
    )

    if total <= 0:
        return _render_table(response)

    items = [
        _text_block(
            "Part-to-whole charts are represented as contribution rows.",
            isSubtle=True,
            wrap=True,
        )
    ]

    for row in rows:
        value = _decimal_or_none(row.get(series.field))
        percent = Decimal("0") if value is None else (value / total * 100)
        label = _truncate(str(row.get(response.category_field, "")), 42)
        items.append(
            _text_block(
                f"{label or '-'}: {_format_value(row.get(series.field), series)} "
                f"({_format_decimal(percent, 1)}%)",
                wrap=True,
            )
        )

    items.extend(_truncation_note(response.rows, MAX_CHART_CATEGORIES))
    return items


def _render_table(response: VisualResponse) -> list[dict[str, Any]]:
    if not response.rows:
        return [_text_block("No data to show.", wrap=True)]

    columns = response.columns[:MAX_TABLE_COLUMNS]
    rows = _first_rows(response.rows, MAX_TABLE_ROWS)
    body = [
        _text_block(
            f"Showing {len(rows)} of {len(response.rows)} row(s).",
            isSubtle=True,
            wrap=True,
        ),
        _table_header(columns),
    ]

    for row in rows:
        body.append(_table_row(columns, row, response))

    if len(response.columns) > MAX_TABLE_COLUMNS:
        body.append(
            _text_block(
                f"{len(response.columns) - MAX_TABLE_COLUMNS} additional column(s) omitted.",
                isSubtle=True,
                wrap=True,
            )
        )
    body.extend(_truncation_note(response.rows, MAX_TABLE_ROWS))
    return body


def _render_fallback(response: VisualResponse) -> list[dict[str, Any]]:
    return [
        _text_block(
            f"{response.visual_type.replace('_', ' ').title()} is not rendered "
            "directly in this Adaptive Card yet. Showing the underlying data.",
            wrap=True,
            isSubtle=True,
        ),
        *_render_table(response),
    ]


def _render_data_note(response: VisualResponse) -> list[dict[str, Any]]:
    if not response.rows or response.visual_type == "table":
        return []
    return [
        _text_block(
            "Underlying rows are included in the structured business result.",
            wrap=True,
            isSubtle=True,
            spacing="Small",
        )
    ]


def _render_actions(response: VisualResponse) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for action in response.suggested_actions[:MAX_ACTIONS]:
        actions.append(
            {
                "type": "Action.Submit",
                "title": action.label,
                "data": {
                    "action": action.action,
                    "parameters": action.parameters,
                },
            }
        )
    return actions


def _primary_series(response: VisualResponse) -> SeriesDefinition | None:
    return response.series[0] if response.series else None


def _format_value(value: Any, series: SeriesDefinition | None = None) -> str:
    if value is None:
        return ""

    value_format = series.value_format if series else "text"
    currency_code = series.currency_code if series else None

    if isinstance(value, datetime):
        return value.isoformat(sep=" ", timespec="seconds")
    if isinstance(value, date):
        return value.isoformat()

    if value_format in {"number", "integer", "currency", "percent"}:
        number = _decimal_or_none(value)
        if number is not None:
            if value_format == "integer":
                return f"{number:,.0f}"
            if value_format == "currency":
                return f"{currency_code or 'USD'} {_format_decimal(number, 2)}"
            if value_format == "percent":
                return f"{_format_decimal(number, 1)}%"
            return _format_decimal(number, 2)

    return str(value)


def _format_decimal(value: Decimal, places: int) -> str:
    quantizer = Decimal("1") if places == 0 else Decimal("1." + ("0" * places))
    formatted = value.quantize(quantizer)
    return f"{formatted:,.{places}f}"


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _max_abs_value(rows: list[dict[str, Any]], field: str) -> Decimal:
    values = [
        abs(value)
        for value in (_decimal_or_none(row.get(field)) for row in rows)
        if value is not None
    ]
    return max(values) if values else Decimal("0")


def _bar_text(value: Decimal | None, max_abs: Decimal) -> str:
    if value is None or max_abs <= 0:
        return "[----------]"

    filled = int((abs(value) / max_abs * 10).to_integral_value())
    filled = max(1, min(10, filled))
    return "[" + ("#" * filled) + ("-" * (10 - filled)) + "]"


def _chart_caption(response: VisualResponse) -> str:
    if response.visual_type == "horizontal_bar":
        return "Ranking shown as proportional bars."
    return "Comparison shown as proportional bars."


def _table_header(columns: list[str]) -> dict[str, Any]:
    return {
        "type": "ColumnSet",
        "separator": True,
        "columns": [
            {
                "type": "Column",
                "width": "stretch",
                "items": [_text_block(column, weight="Bolder", wrap=True)],
            }
            for column in columns
        ],
    }


def _table_row(
    columns: list[str],
    row: dict[str, Any],
    response: VisualResponse,
) -> dict[str, Any]:
    series_by_field = {series.field: series for series in response.series}
    return {
        "type": "ColumnSet",
        "columns": [
            {
                "type": "Column",
                "width": "stretch",
                "items": [
                    _text_block(
                        _truncate(
                            _format_value(row.get(column), series_by_field.get(column)),
                            36,
                        ),
                        wrap=True,
                    )
                ],
            }
            for column in columns
        ],
    }


def _text_block(
    text: str,
    *,
    weight: str | None = None,
    size: str | None = None,
    wrap: bool = True,
    isSubtle: bool | None = None,
    spacing: str | None = None,
) -> dict[str, Any]:
    block: dict[str, Any] = {"type": "TextBlock", "text": text, "wrap": wrap}
    if weight:
        block["weight"] = weight
    if size:
        block["size"] = size
    if isSubtle is not None:
        block["isSubtle"] = isSubtle
    if spacing:
        block["spacing"] = spacing
    return block


def _first_rows(rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    return rows[:limit]


def _truncation_note(rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    if len(rows) <= limit:
        return []
    return [
        _text_block(
            f"{len(rows) - limit} additional row(s) omitted from the card.",
            isSubtle=True,
            wrap=True,
            spacing="Small",
        )
    ]


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)] + "..."
