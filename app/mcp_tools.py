"""FastMCP tool registration for the shared SQL Server analytics services."""

from __future__ import annotations

import json
from typing import Any, Optional

import pyodbc
from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, TextContent
from pydantic import BaseModel, ConfigDict, Field

from .config import AppPaths, get_app_paths
from .cursor_renderer import CHART_VIEW_HTML, CHART_VIEW_URI
from .data_dictionary import DATA_DICTIONARY
from .database import DatabaseClient
from .memory_service import MemoryService
from .query_service import QueryService
from .schema_service import SchemaService
from .security import validate_read_only_sql
from .response_models import cursor_payload_from_visual_response
from .adaptive_card_renderer import render_copilot_tool_output
from .visual_selection import ValueFormat, VisualType, build_visual_response


def build_instructions(data_dictionary: str = DATA_DICTIONARY) -> str:
    """Build the business-user instructions preserved from the legacy server."""
    return (
        "You are a conversational business analytics assistant connected to the "
        "WideWorldImporters SQL Server database.\n"
        "The user is not assumed to have technical knowledge of SQL, databases, "
        "schemas, MCP, or software development. Translate ordinary business "
        "questions into internal SQL and return only the useful business answer.\n\n"
        "INTERNAL WORKFLOW\n"
        "Perform this workflow automatically and silently. Do not require the "
        "user to describe these steps.\n"
        "1. Call sqlserver_get_schema for the relevant part of the database.\n"
        "2. Call sqlserver_memory_read.\n"
        "3. Use the DATA DICTIONARY to choose the correct tables, joins and "
        "business interpretation.\n"
        "4. Generate and execute one read-only SQL query.\n"
        "5. Inspect the actual returned columns, values and row count.\n"
        "6. Decide whether the result is best communicated as an interactive "
        "visual, KPI, or detailed table.\n"
        "7. For visual or KPI results, call sqlserver_visual_query automatically "
        "using the same SQL and exact returned column names.\n\n"
        "DEFAULT PRESENTATION BEHAVIOUR\n"
        "Automatically use sqlserver_visual_query when the result represents:\n"
        "- a KPI or one principal numeric value;\n"
        "- a ranking or top/bottom N comparison;\n"
        "- a comparison across categories;\n"
        "- a trend or change over time;\n"
        "- a relationship between numeric measures;\n"
        "- a small part-to-whole composition.\n\n"
        "Use a table when:\n"
        "- the user asks for detailed records, transactions, invoices, orders, "
        "customers, suppliers, or another row-level list;\n"
        "- there are many descriptive columns;\n"
        "- exact values matter more than visual comparison;\n"
        "- no valid chart pattern exists;\n"
        "- the user explicitly requests text, JSON, or table-only output.\n\n"
        "VISUAL SELECTION\n"
        "- KPI: one principal numeric result.\n"
        "- Line: ordered date or period with one or more numeric measures.\n"
        "- Horizontal bar: rankings, top/bottom N, or long category labels.\n"
        "- Bar: comparisons across a small number of independent categories.\n"
        "- Scatter: relationship between two numeric measures.\n"
        "- Pie or doughnut: no more than six categories forming a meaningful "
        "whole, with no negative values.\n"
        "- Table: detailed records or an unsuitable result shape.\n\n"
        "USER-FACING RESPONSE RULES\n"
        "- Do not show SQL unless the user explicitly asks to see it.\n"
        "- Do not expose schema names, table names, column names, joins, JSON "
        "payloads, tool names, or internal workflow unless explicitly requested.\n"
        "- Do not narrate schema inspection, query generation, or tool execution.\n"
        "- Lead with the answer, not the method.\n"
        "- Present results in plain business language.\n"
        "- For analytical questions, return the interactive visual or KPI plus "
        "one or two concise business observations.\n"
        "- For detailed-record questions, return the interactive table plus a "
        "brief business summary.\n"
        "- Keep SQL only in the server query log for audit and troubleshooting.\n"
        "- If the user explicitly asks for SQL, provide it separately after the "
        "business answer.\n"
        "- Do not ask which chart type to use unless two materially different "
        "interpretations are equally valid. Choose the best visual yourself.\n"
        "- Do not require the user to request an interactive chart explicitly.\n"
        "- Keep the underlying result table available inside every interactive "
        "visual.\n\n"
        "SAFETY\n"
        "Only one read-only SELECT or CTE statement is permitted. Never modify "
        "data.\n\n"
        + data_dictionary
    )


class GetSchemaInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    table_filter: Optional[str] = Field(
        default=None,
        description=(
            "Optional partial table name to narrow results. "
            "E.g. 'sales' returns all tables whose name contains 'sales'. "
            "Leave blank to return the full schema."
        ),
    )


class QueryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sql: str = Field(
        ...,
        description="A valid SELECT statement. Write operations are not permitted.",
        min_length=10,
    )
    max_rows: int = Field(
        default=100,
        description="Maximum number of rows to return (1-500)",
        ge=1,
        le=500,
    )
    format: str = Field(
        default="markdown",
        description="Output format: 'markdown' for a readable table, 'json' for structured data",
    )


class MemorySuggestInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: str = Field(
        ...,
        description=(
            "Category of the suggestion. Must be one of: "
            "'join' (a join path discovered or inferred), "
            "'pattern' (a column value pattern observed from results), "
            "'rule' (a business rule inferred from the data), "
            "'correction' (a correction to an existing data dictionary entry)."
        ),
    )
    observation: str = Field(
        ...,
        description=(
            "What was observed. Be specific - include table names, column names, "
            "and values where relevant."
        ),
        min_length=20,
    )
    confidence: str = Field(
        ...,
        description=(
            "How confident you are in this observation. Must be one of: "
            "'high' (observed directly in query results), "
            "'medium' (inferred from naming patterns and partial evidence), "
            "'low' (a guess based on limited evidence - flag clearly)."
        ),
    )
    source_query: Optional[str] = Field(
        default=None,
        description="The SQL query that led to this observation, if applicable.",
    )


class VisualQueryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sql: str = Field(
        ...,
        min_length=10,
        description=(
            "The same single read-only SELECT or CTE statement already tested "
            "with sqlserver_query(format='json')."
        ),
    )
    visual_type: VisualType = Field(
        ...,
        description=(
            "Choose after inspecting the real query result: table, kpi, bar, "
            "horizontal_bar, line, scatter, pie, or doughnut."
        ),
    )
    title: str = Field(
        ...,
        min_length=3,
        max_length=140,
        description="Concise human-readable visual title.",
    )
    reason: str = Field(
        ...,
        min_length=10,
        max_length=400,
        description=(
            "Briefly explain why this visual suits the user's question and "
            "the returned data shape."
        ),
    )
    summary: Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=500,
        description=(
            "Concise business-facing summary. If omitted, the visual reason is "
            "used as the summary for backwards compatibility."
        ),
    )
    x_field: Optional[str] = Field(
        default=None,
        description=(
            "Exact returned column to use for categories, dates, periods or "
            "the scatter x-axis. Not required for table or KPI."
        ),
    )
    y_fields: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="Exact returned numeric columns to plot.",
    )
    value_format: ValueFormat = Field(
        default="number",
        description="Display format for plotted numeric values.",
    )
    currency_code: str = Field(
        default="USD",
        min_length=3,
        max_length=3,
        description="ISO currency code used when value_format is currency.",
    )
    max_rows: int = Field(default=200, ge=1, le=500)


def create_mcp(
    database_client: DatabaseClient | None = None,
    paths: AppPaths | None = None,
    fastmcp_kwargs: dict[str, Any] | None = None,
) -> FastMCP:
    """Create a FastMCP server with the preserved SQL Server tools."""
    resolved_paths = paths or get_app_paths()
    resolved_database = database_client or DatabaseClient()
    query_service = QueryService(resolved_database)
    schema_service = SchemaService(resolved_database.run_query)
    memory_service = MemoryService(
        resolved_paths.memory_file,
        resolved_paths.pending_file,
    )

    mcp = FastMCP(
        "sqlserver_mcp",
        instructions=build_instructions(),
        **(fastmcp_kwargs or {}),
    )

    @mcp.tool(
        name="sqlserver_get_schema",
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def sqlserver_get_schema(params: GetSchemaInput) -> str:
        """Read the live database schema from SQL Server system views."""
        return schema_service.get_schema(params.table_filter)

    @mcp.tool(
        name="sqlserver_query",
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def sqlserver_query(params: QueryInput) -> str:
        """Execute a read-only SELECT query against SQL Server."""
        return query_service.execute_text(
            params.sql,
            max_rows=params.max_rows,
            output_format=params.format,
        )

    @mcp.tool(
        name="sqlserver_memory_read",
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def sqlserver_memory_read() -> str:
        """Load accumulated reviewed schema knowledge from previous sessions."""
        return memory_service.read()

    @mcp.tool(
        name="sqlserver_memory_suggest",
        annotations={
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": False,
        },
    )
    async def sqlserver_memory_suggest(params: MemorySuggestInput) -> str:
        """Write a schema discovery to the pending suggestions file for review."""
        return memory_service.suggest(
            params.category,
            params.observation,
            params.confidence,
            params.source_query,
        )

    @mcp.tool(
        name="sqlserver_visual_query",
        meta={
            "ui": {"resourceUri": CHART_VIEW_URI},
            "ui/resourceUri": CHART_VIEW_URI,
        },
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def sqlserver_visual_query(params: VisualQueryInput) -> CallToolResult:
        """Render the final business answer as an interactive analytical result."""
        valid, validation_error = validate_read_only_sql(
            params.sql,
            approved_schemas=query_service.approved_schemas,
        )
        if not valid:
            payload = {"error": validation_error}
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(payload))],
                structuredContent=payload,
                isError=True,
            )

        try:
            rows = query_service.run_rows(params.sql, max_rows=params.max_rows)
            response = build_visual_response(
                title=params.title,
                summary=params.summary or params.reason,
                reasoning_note=params.reason,
                visual_type=params.visual_type,
                rows=rows,
                category_field=params.x_field,
                series_fields=params.y_fields,
                value_format=params.value_format,
                currency_code=params.currency_code,
            )
            payload = cursor_payload_from_visual_response(response)
            payload["visual_response"] = response.public_payload()

            summary = (
                f"{payload['title']}: {payload['row_count']} row(s), "
                f"rendered as {payload['visual_type']}."
            )

            return CallToolResult(
                content=[
                    TextContent(type="text", text=summary),
                    TextContent(type="text", text=json.dumps(payload, default=str)),
                ],
                structuredContent=payload,
            )

        except pyodbc.Error as error:
            payload = {"error": f"SQL Error: {error}"}
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(payload))],
                structuredContent=payload,
                isError=True,
            )
        except Exception as error:
            payload = {"error": f"Unexpected error: {error}"}
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(payload))],
                structuredContent=payload,
                isError=True,
            )

    @mcp.tool(
        name="sqlserver_copilot_visual_query",
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def sqlserver_copilot_visual_query(params: VisualQueryInput) -> CallToolResult:
        """Return a neutral result, Adaptive Card JSON, and plain-text fallback."""
        valid, validation_error = validate_read_only_sql(
            params.sql,
            approved_schemas=query_service.approved_schemas,
        )
        if not valid:
            payload = {
                "business_result": {
                    "title": "Query rejected",
                    "summary": validation_error,
                    "visual_type": "table",
                    "columns": [],
                    "rows": [],
                    "suggested_actions": [],
                },
                "adaptive_card": {},
                "fallback_text": f"Query rejected: {validation_error}",
            }
            return CallToolResult(
                content=[TextContent(type="text", text=payload["fallback_text"])],
                structuredContent=payload,
                isError=True,
            )

        rows = query_service.run_rows(params.sql, max_rows=params.max_rows)
        response = build_visual_response(
            title=params.title,
            summary=params.summary or params.reason,
            reasoning_note=params.reason,
            visual_type=params.visual_type,
            rows=rows,
            category_field=params.x_field,
            series_fields=params.y_fields,
            value_format=params.value_format,
            currency_code=params.currency_code,
        )
        payload = render_copilot_tool_output(response)
        return CallToolResult(
            content=[TextContent(type="text", text=payload["fallback_text"])],
            structuredContent=payload,
        )

    @mcp.resource(
        CHART_VIEW_URI,
        mime_type="text/html;profile=mcp-app",
        meta={
            "ui": {
                "csp": {
                    "resourceDomains": [
                        "https://unpkg.com",
                        "https://cdn.jsdelivr.net",
                    ]
                }
            }
        },
    )
    def sqlserver_chart_view() -> str:
        """Return the interactive HTML used by sqlserver_visual_query."""
        return CHART_VIEW_HTML

    return mcp


mcp = create_mcp()
