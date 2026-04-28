"""
Get RUM events tool
"""

import json
import logging
from typing import Any, Dict

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent

logger = logging.getLogger(__name__)

from ..utils.datadog_client import fetch_rum_events
from ..utils.formatters import (
    extract_rum_event_info,
    format_rum_events_as_table,
    format_rum_events_as_text,
)


def get_tool_definition() -> Tool:
    """Get the tool definition for get_rum_events."""
    return Tool(
        name="get_rum_events",
        description="Search and retrieve Real User Monitoring (RUM) events from Datadog. Use this to query RUM actions, views, errors, and other browser events.",
        inputSchema={
            "type": "object",
            "properties": {
                "time_range": {
                    "type": "string",
                    "description": "Time range to look back",
                    "enum": ["1h", "4h", "8h", "1d", "7d", "14d", "30d"],
                    "default": "1h",
                },
                "filters": {
                    "type": "object",
                    "description": "Filters to apply (prefixed with @ automatically). Examples: {'type': 'action', 'action.name': 'project_load', 'context.outcome': 'success'}",
                    "additionalProperties": {"type": "string"},
                    "default": {},
                },
                "query": {
                    "type": "string",
                    "description": "Free-text search query using Datadog RUM query syntax (e.g., '@type:action @action.name:project_load', '@type:error', '@view.name:/edit/*')",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of RUM events (default: 50)",
                    "default": 50,
                    "minimum": 1,
                    "maximum": 1000,
                },
                "cursor": {
                    "type": "string",
                    "description": "Pagination cursor from previous response (for getting next page)",
                    "default": "",
                },
                "format": {
                    "type": "string",
                    "description": "Output format",
                    "enum": ["table", "text", "json"],
                    "default": "table",
                },
            },
            "additionalProperties": False,
            "required": [],
        },
    )


async def handle_call(request: CallToolRequest) -> CallToolResult:
    """Handle the get_rum_events tool call."""
    try:
        args = request.arguments or {}

        time_range = args.get("time_range", "1h")
        filters = args.get("filters", {})
        query = args.get("query")
        limit = args.get("limit", 50)
        cursor = args.get("cursor", "")
        format_type = args.get("format", "table")

        response = await fetch_rum_events(
            time_range=time_range,
            filters=filters,
            query=query,
            limit=limit,
            cursor=cursor if cursor else None,
        )

        rum_events = response.get("data", [])

        # Extract event info
        events = extract_rum_event_info(rum_events)

        # Get pagination info
        meta = response.get("meta", {})
        page = meta.get("page", {})
        next_cursor = page.get("after")

        if len(events) == 0:
            suggestion_msg = "No RUM events found"
            if query:
                suggestion_msg += f" with query: '{query}'"
            if filters:
                filter_strs = [f"{k}={v}" for k, v in filters.items()]
                suggestion_msg += f" with filters: {', '.join(filter_strs)}"
            suggestion_msg += f"\n\nCommon RUM queries:\n"
            suggestion_msg += "  @type:action — custom actions (e.g., trackAction)\n"
            suggestion_msg += "  @type:view — page views\n"
            suggestion_msg += "  @type:error — JS errors\n"
            suggestion_msg += "  @action.name:project_load — specific action name\n"

            return CallToolResult(
                content=[TextContent(type="text", text=suggestion_msg)],
                isError=False,
            )

        # Format output
        if format_type == "json":
            output = {
                "events": events,
                "pagination": {
                    "next_cursor": next_cursor,
                    "has_more": bool(next_cursor),
                },
            }
            content = json.dumps(output, indent=2)
        elif format_type == "text":
            content = format_rum_events_as_text(events)
            if next_cursor:
                content += f"\n\nNext cursor: {next_cursor}"
        else:  # table
            content = format_rum_events_as_table(events)
            if next_cursor:
                content += f"\n\nNext cursor: {next_cursor}"

        # Add summary header (not for JSON)
        if format_type != "json":
            summary = f"Time Range: {time_range} | Found: {len(events)} RUM events"
            if cursor:
                summary += " (cursor pagination)"
            if filters:
                filter_strs = [f"{k}={v}" for k, v in filters.items()]
                summary += f" | Filters: {', '.join(filter_strs)}"
            if query:
                summary += f" | Query: {query}"

            final_content = f"{summary}\n{'=' * len(summary)}\n\n{content}"
        else:
            final_content = content

        return CallToolResult(
            content=[TextContent(type="text", text=final_content)],
            isError=False,
        )

    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )
