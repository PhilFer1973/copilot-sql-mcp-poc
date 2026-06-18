# Acceptance Tests

These tests preserve the existing Cursor behavior before any Azure, HTTP, or
Adaptive Card work begins.

## Automated Checks

Run:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

Expected:

- SQL validation accepts one `SELECT` or `WITH` query.
- SQL validation rejects empty SQL, multiple statements, write operations, and
  SQL comments.
- Query result formatting returns markdown and JSON in the legacy shape.
- Memory read handles missing, empty, and populated files.
- Memory suggestions validate category and confidence before writing.
- Schema formatting groups columns by table and includes declared FK references.
- Visual validation preserves the legacy fallback rules.
- Cursor renderer keeps the same `ui://sqlserver-mcp/chart-view.html` resource.

## Manual Cursor Checks

These require the local SQL Server Express and WideWorldImporters setup already
used by the legacy implementation.

### Test A: Ranking

Question:

```text
What are the top five outstanding customer balances?
```

Expected:

- horizontal bar
- concise business summary
- no SQL shown by default
- underlying data available in the Data tab

### Test B: Trend

Question:

```text
How have monthly invoiced sales changed over time?
```

Expected:

- line chart
- chronological x-axis
- concise trend summary
- no SQL shown by default
- underlying data available in the Data tab

### Test C: KPI

Question:

```text
What is total invoiced sales?
```

Expected:

- KPI display
- currency formatting where the model selects currency output
- no SQL shown by default

### Test D: Detailed Records

Question:

```text
Show the 20 most recent invoices.
```

Expected:

- table-focused result
- short business summary
- no chart unless the data shape clearly warrants it
- no SQL shown by default

## Current Compatibility Notes

- The refactored path preserves the legacy SQL validator as-is. Stricter
  controls such as cross-database rejection, system-table blocking, and schema
  allow-lists are planned for the later database configuration/security
  milestone.
- Follow-up actions such as `Show top 10` are part of the later shared visual
  contract and Adaptive Card milestones, not the current legacy Cursor surface.
