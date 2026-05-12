"""
Update monitor tool
"""

import json
import logging

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent

from ..utils.datadog_client import update_monitor, DD_SITE

logger = logging.getLogger(__name__)


def get_tool_definition() -> Tool:
    """Get the tool definition for update_monitor."""
    return Tool(
        name="update_monitor",
        description=(
            "Edit an existing Datadog monitor by id. Unlike dashboards, the monitor PUT endpoint accepts "
            "a partial payload — fields you omit are left unchanged. Pass only what you want to update."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "monitor_id": {
                    "type": "integer",
                    "description": "The numeric id of the monitor to update.",
                },
                "payload": {
                    "type": "object",
                    "description": (
                        "Partial monitor JSON. Common fields: `name`, `query`, `message`, `options`, `tags`."
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
            "required": ["monitor_id", "payload"],
        },
    )


async def handle_call(request: CallToolRequest) -> CallToolResult:
    """Handle the update_monitor tool call."""
    try:
        args = request.arguments or {}
        monitor_id = args.get("monitor_id")
        payload = args.get("payload")
        format_type = args.get("format", "summary")

        if monitor_id is None:
            return CallToolResult(
                content=[TextContent(type="text", text="Error: `monitor_id` is required")],
                isError=True,
            )
        if not isinstance(payload, dict):
            return CallToolResult(
                content=[TextContent(type="text", text="Error: `payload` must be a JSON object")],
                isError=True,
            )

        result = await update_monitor(int(monitor_id), payload)
        full_url = f"https://app.{DD_SITE}/monitors/{monitor_id}"

        if format_type == "json":
            content = json.dumps(result, indent=2)
        else:
            content = (
                f"Monitor updated successfully.\n"
                f"  id:    {monitor_id}\n"
                f"  name:  {result.get('name', '?')}\n"
                f"  type:  {result.get('type', '?')}\n"
                f"  url:   {full_url}"
            )

        return CallToolResult(
            content=[TextContent(type="text", text=content)],
            isError=False,
        )

    except Exception as e:
        logger.error(f"Error in update_monitor: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )
