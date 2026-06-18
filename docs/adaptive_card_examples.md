# Adaptive Card Renderer

Milestone 4 adds `app/adaptive_card_renderer.py`.

The renderer consumes `VisualResponse` and returns conservative Adaptive Card
JSON using schema version `1.2`.

## Supported Outputs

- KPI: large formatted value plus measure name.
- Horizontal bar: proportional text bars with category labels.
- Bar: proportional text bars with category labels.
- Line: ordered point list using `FactSet`.
- Pie: contribution rows with percentage share.
- Doughnut: contribution rows with percentage share.
- Table: capped row and column grid using `ColumnSet`.
- Scatter: safe fallback to table-style data.

## Limits

- Chart categories are capped to 8 rows.
- Table cards show up to 8 rows and 4 columns.
- Additional rows or columns are noted in the card.
- Suggested actions are rendered as `Action.Submit` buttons.
- Null values render as empty text.
- Long labels are truncated for readability.

## Copilot-Facing Shape

Use `render_copilot_tool_output(response)`:

```json
{
  "business_result": {},
  "adaptive_card": {},
  "fallback_text": "..."
}
```

The business result excludes `reasoning_note`. SQL is not part of the public
payload.

## Notes

This first renderer avoids native chart extensions and generated images so the
cards remain portable across conservative Adaptive Card hosts. Richer visual
cards can be added later once the exact Copilot Studio and Teams host behavior
is verified.
