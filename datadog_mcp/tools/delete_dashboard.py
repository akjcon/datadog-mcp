"""
Delete dashboard tool — destructive, gated by `confirm=true`.
"""

import json
import logging

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent

from ..utils.datadog_client import delete_dashboard

logger = logging.getLogger(__name__)


def get_tool_definition() -> Tool:
    """Get the tool definition for delete_dashboard."""
    return Tool(
        name="delete_dashboard",
        description=(
            "Delete a Datadog dashboard by id. DESTRUCTIVE: requires `confirm=true` to proceed. "
            "Without confirm, the call is a dry-run that reports what would be deleted."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "dashboard_id": {
                    "type": "string",
                    "description": "The id of the dashboard to delete.",
                },
                "confirm": {
                    "type": "boolean",
                    "description": "Must be set to true to actually perform the deletion.",
                    "default": False,
                },
            },
            "additionalProperties": False,
            "required": ["dashboard_id"],
        },
    )


async def handle_call(request: CallToolRequest) -> CallToolResult:
    """Handle the delete_dashboard tool call."""
    try:
        args = request.arguments or {}
        dashboard_id = args.get("dashboard_id")
        confirm = bool(args.get("confirm", False))

        if not dashboard_id:
            return CallToolResult(
                content=[TextContent(type="text", text="Error: `dashboard_id` is required")],
                isError=True,
            )

        if not confirm:
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=(
                            f"Dry-run: would delete dashboard `{dashboard_id}`. "
                            "Re-call with `confirm=true` to actually delete."
                        ),
                    )
                ],
                isError=False,
            )

        result = await delete_dashboard(dashboard_id)
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"Dashboard `{dashboard_id}` deleted.\n{json.dumps(result, indent=2)}",
                )
            ],
            isError=False,
        )

    except Exception as e:
        logger.error(f"Error in delete_dashboard: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )
