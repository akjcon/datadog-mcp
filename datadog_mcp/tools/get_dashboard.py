"""
Get dashboard tool
"""

import json
import logging

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent

from ..utils.datadog_client import get_dashboard, DD_SITE

logger = logging.getLogger(__name__)


def get_tool_definition() -> Tool:
    """Get the tool definition for get_dashboard."""
    return Tool(
        name="get_dashboard",
        description=(
            "Fetch a single Datadog dashboard's full JSON definition by id. Useful for inspecting an "
            "existing dashboard before mutating it with `update_dashboard`."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "dashboard_id": {
                    "type": "string",
                    "description": "The id of the dashboard to fetch (e.g. 'abc-123-xyz').",
                },
                "format": {
                    "type": "string",
                    "description": (
                        "Output format. `summary` lists widget titles only; `json` returns the full payload."
                    ),
                    "enum": ["summary", "json"],
                    "default": "summary",
                },
            },
            "additionalProperties": False,
            "required": ["dashboard_id"],
        },
    )


def _widget_title(widget: dict) -> str:
    """Best-effort title extraction across widget definition shapes."""
    definition = widget.get("definition") or {}
    return definition.get("title") or definition.get("type") or "(untitled)"


async def handle_call(request: CallToolRequest) -> CallToolResult:
    """Handle the get_dashboard tool call."""
    try:
        args = request.arguments or {}
        dashboard_id = args.get("dashboard_id")
        format_type = args.get("format", "summary")

        if not dashboard_id:
            return CallToolResult(
                content=[TextContent(type="text", text="Error: `dashboard_id` is required")],
                isError=True,
            )

        result = await get_dashboard(dashboard_id)

        if format_type == "json":
            content = json.dumps(result, indent=2)
        else:
            url_path = result.get("url") or f"/dashboard/{dashboard_id}"
            full_url = f"https://app.{DD_SITE}{url_path}"
            widgets = result.get("widgets", [])
            content = (
                f"Dashboard: {result.get('title', '(no title)')}\n"
                f"  id:          {dashboard_id}\n"
                f"  layout_type: {result.get('layout_type', '?')}\n"
                f"  url:         {full_url}\n"
                f"  widgets:     {len(widgets)}\n"
            )
            for i, w in enumerate(widgets, 1):
                content += f"    {i:3d}. {_widget_title(w)}\n"

        return CallToolResult(
            content=[TextContent(type="text", text=content)],
            isError=False,
        )

    except Exception as e:
        logger.error(f"Error in get_dashboard: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )
