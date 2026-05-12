"""
Create dashboard tool
"""

import json
import logging

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent

from ..utils.datadog_client import create_dashboard, DD_SITE

logger = logging.getLogger(__name__)


def get_tool_definition() -> Tool:
    """Get the tool definition for create_dashboard."""
    return Tool(
        name="create_dashboard",
        description=(
            "Create a new Datadog dashboard. Pass the full dashboard JSON payload as defined by the "
            "Datadog v1 Dashboards API (https://docs.datadoghq.com/api/latest/dashboards/#create-a-new-dashboard). "
            "Required top-level fields: `title`, `layout_type` (\"ordered\" or \"free\"), and `widgets` (array). "
            "Returns the created dashboard's id and the URL where it can be viewed."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "payload": {
                    "type": "object",
                    "description": (
                        "Full dashboard JSON payload. Must include `title`, `layout_type`, and `widgets`. "
                        "May also include `description`, `template_variables`, `notify_list`, `tags`, etc."
                    ),
                },
                "format": {
                    "type": "string",
                    "description": "Output format. `summary` returns id+url; `json` returns the full response.",
                    "enum": ["summary", "json"],
                    "default": "summary",
                },
            },
            "additionalProperties": False,
            "required": ["payload"],
        },
    )


async def handle_call(request: CallToolRequest) -> CallToolResult:
    """Handle the create_dashboard tool call."""
    try:
        args = request.arguments or {}
        payload = args.get("payload")
        format_type = args.get("format", "summary")

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

        result = await create_dashboard(payload)
        dashboard_id = result.get("id", "<unknown>")
        url_path = result.get("url") or f"/dashboard/{dashboard_id}"
        full_url = f"https://app.{DD_SITE}{url_path}"

        if format_type == "json":
            content = json.dumps(result, indent=2)
        else:
            content = (
                f"Dashboard created successfully.\n"
                f"  id:    {dashboard_id}\n"
                f"  title: {result.get('title', payload.get('title'))}\n"
                f"  url:   {full_url}"
            )

        return CallToolResult(
            content=[TextContent(type="text", text=content)],
            isError=False,
        )

    except Exception as e:
        logger.error(f"Error in create_dashboard: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )
