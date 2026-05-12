"""
Delete monitor tool — destructive, gated by `confirm=true`.
"""

import json
import logging

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent

from ..utils.datadog_client import delete_monitor

logger = logging.getLogger(__name__)


def get_tool_definition() -> Tool:
    """Get the tool definition for delete_monitor."""
    return Tool(
        name="delete_monitor",
        description=(
            "Delete a Datadog monitor by id. DESTRUCTIVE: requires `confirm=true` to proceed. "
            "Pass `force=true` to delete even if the monitor is referenced by SLOs."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "monitor_id": {
                    "type": "integer",
                    "description": "The numeric id of the monitor to delete.",
                },
                "confirm": {
                    "type": "boolean",
                    "description": "Must be set to true to actually perform the deletion.",
                    "default": False,
                },
                "force": {
                    "type": "boolean",
                    "description": "Force delete even if referenced by SLOs.",
                    "default": False,
                },
            },
            "additionalProperties": False,
            "required": ["monitor_id"],
        },
    )


async def handle_call(request: CallToolRequest) -> CallToolResult:
    """Handle the delete_monitor tool call."""
    try:
        args = request.arguments or {}
        monitor_id = args.get("monitor_id")
        confirm = bool(args.get("confirm", False))
        force = bool(args.get("force", False))

        if monitor_id is None:
            return CallToolResult(
                content=[TextContent(type="text", text="Error: `monitor_id` is required")],
                isError=True,
            )

        if not confirm:
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=(
                            f"Dry-run: would delete monitor `{monitor_id}`"
                            f"{' (force=true)' if force else ''}. "
                            "Re-call with `confirm=true` to actually delete."
                        ),
                    )
                ],
                isError=False,
            )

        result = await delete_monitor(int(monitor_id), force=force)
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"Monitor `{monitor_id}` deleted.\n{json.dumps(result, indent=2)}",
                )
            ],
            isError=False,
        )

    except Exception as e:
        logger.error(f"Error in delete_monitor: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )
