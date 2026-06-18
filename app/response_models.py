"""Neutral visual response contract shared by renderers."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


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

ValueFormat = Literal[
    "number",
    "integer",
    "currency",
    "percent",
    "date",
    "datetime",
    "text",
]


class SeriesDefinition(BaseModel):
    """One numeric or display series in a visual response."""

    model_config = ConfigDict(extra="forbid")

    name: str
    field: str
    value_format: ValueFormat = "number"
    currency_code: str | None = None

    @model_validator(mode="after")
    def normalize_currency_code(self) -> "SeriesDefinition":
        if self.currency_code:
            self.currency_code = self.currency_code.upper()
        return self


class SuggestedAction(BaseModel):
    """A user-facing follow-up action with a machine-readable payload."""

    model_config = ConfigDict(extra="forbid")

    label: str
    action: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class VisualResponse(BaseModel):
    """Business-facing analytical result independent of a specific renderer."""

    model_config = ConfigDict(extra="forbid")

    title: str
    summary: str
    visual_type: VisualType
    category_field: str | None = None
    series: list[SeriesDefinition] = Field(default_factory=list)
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    suggested_actions: list[SuggestedAction] = Field(default_factory=list)
    reasoning_note: str | None = None

    @model_validator(mode="before")
    @classmethod
    def infer_columns_from_rows(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        rows = data.get("rows") or []
        columns = data.get("columns") or []
        if not columns and rows:
            data = dict(data)
            data["columns"] = list(rows[0].keys())
        return data

    @model_validator(mode="after")
    def validate_referenced_fields(self) -> "VisualResponse":
        available = set(self.columns)

        for row in self.rows:
            available.update(row.keys())

        if self.rows:
            missing = [
                column
                for column in self.columns
                if any(column not in row for row in self.rows)
            ]
            if missing:
                raise ValueError(
                    "columns must be present in every returned row: "
                    + ", ".join(sorted(set(missing)))
                )

        if self.category_field and self.category_field not in available:
            raise ValueError(
                f"category_field '{self.category_field}' is not present in returned rows"
            )

        missing_series = [
            series.field for series in self.series if series.field not in available
        ]
        if missing_series:
            raise ValueError(
                "series fields are not present in returned rows: "
                + ", ".join(sorted(set(missing_series)))
            )

        return self

    def public_payload(self) -> dict[str, Any]:
        """Return the business-facing payload without internal reasoning notes."""
        return self.model_dump(exclude_none=True, exclude={"reasoning_note"})


def cursor_payload_from_visual_response(response: VisualResponse) -> dict[str, Any]:
    """Convert a neutral response to the legacy Cursor MCP App payload shape."""
    first_series = response.series[0] if response.series else None
    value_format: ValueFormat = first_series.value_format if first_series else "number"
    cursor_value_format = (
        value_format if value_format in {"number", "currency", "percent"} else "number"
    )
    currency_code = first_series.currency_code if first_series else None

    return {
        "title": response.title,
        "summary": response.summary,
        "reason": response.summary,
        "visual_type": response.visual_type,
        "category_field": response.category_field,
        "x_field": response.category_field,
        "series": [series.model_dump(exclude_none=True) for series in response.series],
        "y_fields": [series.field for series in response.series],
        "value_format": cursor_value_format,
        "currency_code": (currency_code or "USD").upper(),
        "columns": response.columns,
        "row_count": len(response.rows),
        "rows": response.rows,
        "suggested_actions": [
            action.model_dump() for action in response.suggested_actions
        ],
    }
