"""
Update dashboard tool
"""

import json
import logging

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent

from ..utils.datadog_client import update_dashboard, DD_SITE

logger = logging.getLogger(__name__)


def get_tool_definition() -> Tool:
    """Get the tool definition for update_dashboard."""
    return Tool(
        name="update_dashboard",
        description=(
            "Replace an existing Datadog dashboard's contents with the given JSON payload. "
            "This is a full PUT — fields you omit will be cleared. Fetch the dashboard first via "
            "`get_dashboard` if you only want to tweak parts of it."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "dashboard_id": {
                    "type": "string",
                    "description": "The id of the dashboard to update (e.g. 'abc-123-xyz').",
                },
                "payload": {
                    "type": "object",
                    "description": (
                        "Full dashboard JSON payload. Must include `title`, `layout_type`, and `widgets`."
                    ),
                },
                "format": {
                    "type": "string",
                    "description": "Output format.",
                    "enum": ["summary", "json"],
                    "default": "summary",
                },
            },
            "additionalProperties": False,
            "required": ["dashboard_id", "payload"],
        },
    )


async def handle_call(request: CallToolRequest) -> CallToolResult:
    """Handle the update_dashboard tool call."""
    try:
        args = request.arguments or {}
        dashboard_id = args.get("dashboard_id")
        payload = args.get("payload")
        format_type = args.get("format", "summary")

        if not dashboard_id:
            return CallToolResult(
                content=[TextContent(type="text", text="Error: `dashboard_id` is required")],
                isError=True,
            )
        if not isinstance(payload, dict):
            return CallToolResult(
                content=[TextContent(type="text", text="Error: `payload` must be a JSON object")],
                isError=True,
            )

        for required in ("title", "layout_type", "widgets"):
            if required not in payload:
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=f"Error: dashboard payload is missing required field `{required}`",
                        )
                    ],
                    isError=True,
                )

        result = await update_dashboard(dashboard_id, payload)
        url_path = result.get("url") or f"/dashboard/{dashboard_id}"
        full_url = f"https://app.{DD_SITE}{url_path}"

        if format_type == "json":
            content = json.dumps(result, indent=2)
        else:
            content = (
                f"Dashboard updated successfully.\n"
                f"  id:    {dashboard_id}\n"
                f"  title: {result.get('title', payload.get('title'))}\n"
                f"  url:   {full_url}"
            )

        return CallToolResult(
            content=[TextContent(type="text", text=content)],
            isError=False,
        )

    except Exception as e:
        logger.error(f"Error in update_dashboard: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )
