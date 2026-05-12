"""
Mute monitor tool — also handles unmute via `unmute=true`.
"""

import json
import logging

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent

from ..utils.datadog_client import mute_monitor, DD_SITE

logger = logging.getLogger(__name__)


def get_tool_definition() -> Tool:
    """Get the tool definition for mute_monitor."""
    return Tool(
        name="mute_monitor",
        description=(
            "Mute (silence) or unmute a Datadog monitor. By default mutes globally; pass `scope` to mute "
            "only a specific tag scope (e.g. 'env:prod'). Pass `end` (unix timestamp) for a time-bounded mute. "
            "Set `unmute=true` to lift the mute instead."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "monitor_id": {
                    "type": "integer",
                    "description": "The numeric id of the monitor to mute/unmute.",
                },
                "scope": {
                    "type": "string",
                    "description": "Optional tag scope to mute (e.g. 'env:prod'). Ignored on unmute.",
                    "default": "",
                },
                "end": {
                    "type": "integer",
                    "description": "Optional unix timestamp at which the mute should expire. Ignored on unmute.",
                },
                "unmute": {
                    "type": "boolean",
                    "description": "If true, unmutes instead of muting.",
                    "default": False,
                },
            },
            "additionalProperties": False,
            "required": ["monitor_id"],
        },
    )


async def handle_call(request: CallToolRequest) -> CallToolResult:
    """Handle the mute_monitor tool call."""
    try:
        args = request.arguments or {}
        monitor_id = args.get("monitor_id")
        scope = args.get("scope") or None
        end = args.get("end")
        unmute = bool(args.get("unmute", False))

        if monitor_id is None:
            return CallToolResult(
                content=[TextContent(type="text", text="Error: `monitor_id` is required")],
                isError=True,
            )

        result = await mute_monitor(
            monitor_id=int(monitor_id),
            scope=scope,
            end=end,
            unmute=unmute,
        )

        action = "unmuted" if unmute else "muted"
        full_url = f"https://app.{DD_SITE}/monitors/{monitor_id}"
        content = (
            f"Monitor {action} successfully.\n"
            f"  id:  {monitor_id}\n"
            f"  url: {full_url}\n\n"
            f"{json.dumps(result, indent=2)}"
        )

        return CallToolResult(
            content=[TextContent(type="text", text=content)],
            isError=False,
        )

    except Exception as e:
        logger.error(f"Error in mute_monitor: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )
