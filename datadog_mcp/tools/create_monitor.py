"""
Create monitor tool
"""

import json
import logging

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent

from ..utils.datadog_client import create_monitor, DD_SITE

logger = logging.getLogger(__name__)


def get_tool_definition() -> Tool:
    """Get the tool definition for create_monitor."""
    return Tool(
        name="create_monitor",
        description=(
            "Create a new Datadog monitor. Pass the full monitor JSON payload as defined by the "
            "Datadog v1 Monitors API (https://docs.datadoghq.com/api/latest/monitors/#create-a-monitor). "
            "Required: `type` (e.g. 'metric alert', 'log alert', 'query alert'), `query`, and `name`. "
            "`message` and `tags` strongly recommended for routing alerts."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "payload": {
                    "type": "object",
                    "description": (
                        "Full monitor JSON payload. Must include `type`, `query`, and `name`. "
                        "See Datadog docs for `options` (thresholds, evaluation_delay, notify_no_data, etc.)."
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
            "required": ["payload"],
        },
    )


async def handle_call(request: CallToolRequest) -> CallToolResult:
    """Handle the create_monitor tool call."""
    try:
        args = request.arguments or {}
        payload = args.get("payload")
        format_type = args.get("format", "summary")

        if not isinstance(payload, dict):
            return CallToolResult(
                content=[TextContent(type="text", text="Error: `payload` must be a JSON object")],
                isError=True,
            )

        for required in ("type", "query", "name"):
            if required not in payload:
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=f"Error: monitor payload is missing required field `{required}`",
                        )
                    ],
                    isError=True,
                )

        result = await create_monitor(payload)
        monitor_id = result.get("id", "<unknown>")
        full_url = f"https://app.{DD_SITE}/monitors/{monitor_id}"

        if format_type == "json":
            content = json.dumps(result, indent=2)
        else:
            content = (
                f"Monitor created successfully.\n"
                f"  id:    {monitor_id}\n"
                f"  name:  {result.get('name', payload.get('name'))}\n"
                f"  type:  {result.get('type', payload.get('type'))}\n"
                f"  url:   {full_url}"
            )

        return CallToolResult(
            content=[TextContent(type="text", text=content)],
            isError=False,
        )

    except Exception as e:
        logger.error(f"Error in create_monitor: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )
