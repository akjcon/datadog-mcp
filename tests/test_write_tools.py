"""
Tests for the dashboard + monitor write tools added in 0.1.0.

These exercise the tool wrappers (validation, dry-run gating, output formatting)
with the underlying datadog_client functions mocked out — so no real API calls.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from datadog_mcp.tools import (
    create_dashboard,
    update_dashboard,
    get_dashboard,
    delete_dashboard,
    create_monitor,
    update_monitor,
    mute_monitor,
    delete_monitor,
)


def _req(args):
    """Build a minimal mock CallToolRequest."""
    request = MagicMock()
    request.arguments = args
    return request


# -------------------------------------------------------------------------
# Dashboard tools
# -------------------------------------------------------------------------

class TestCreateDashboard:
    @pytest.mark.asyncio
    async def test_returns_id_and_url_on_success(self):
        with patch(
            "datadog_mcp.tools.create_dashboard.create_dashboard",
            new=AsyncMock(return_value={"id": "abc-123", "title": "My Dash", "url": "/dashboard/abc-123"}),
        ):
            result = await create_dashboard.handle_call(_req({
                "payload": {"title": "My Dash", "layout_type": "ordered", "widgets": []},
            }))
        assert result.isError is False
        text = result.content[0].text
        assert "abc-123" in text
        assert "My Dash" in text
        assert "https://app." in text and "/dashboard/abc-123" in text

    @pytest.mark.asyncio
    async def test_payload_must_be_object(self):
        result = await create_dashboard.handle_call(_req({"payload": "not-an-object"}))
        assert result.isError is True
        assert "must be a JSON object" in result.content[0].text

    @pytest.mark.asyncio
    async def test_missing_required_field_errors(self):
        # Missing `widgets`
        result = await create_dashboard.handle_call(_req({
            "payload": {"title": "X", "layout_type": "ordered"},
        }))
        assert result.isError is True
        assert "widgets" in result.content[0].text


class TestUpdateDashboard:
    @pytest.mark.asyncio
    async def test_requires_dashboard_id(self):
        result = await update_dashboard.handle_call(_req({
            "payload": {"title": "X", "layout_type": "ordered", "widgets": []},
        }))
        assert result.isError is True
        assert "dashboard_id" in result.content[0].text

    @pytest.mark.asyncio
    async def test_happy_path(self):
        with patch(
            "datadog_mcp.tools.update_dashboard.update_dashboard",
            new=AsyncMock(return_value={"id": "abc-123", "title": "Updated"}),
        ):
            result = await update_dashboard.handle_call(_req({
                "dashboard_id": "abc-123",
                "payload": {"title": "Updated", "layout_type": "ordered", "widgets": []},
            }))
        assert result.isError is False
        assert "Updated" in result.content[0].text


class TestGetDashboard:
    @pytest.mark.asyncio
    async def test_summary_lists_widget_titles(self):
        fake = {
            "title": "Test",
            "layout_type": "ordered",
            "widgets": [
                {"definition": {"title": "Widget A", "type": "timeseries"}},
                {"definition": {"type": "note"}},  # no title — falls back to type
            ],
        }
        with patch(
            "datadog_mcp.tools.get_dashboard.get_dashboard",
            new=AsyncMock(return_value=fake),
        ):
            result = await get_dashboard.handle_call(_req({"dashboard_id": "abc-123"}))
        text = result.content[0].text
        assert "Widget A" in text
        assert "note" in text
        assert "widgets:     2" in text

    @pytest.mark.asyncio
    async def test_json_format_returns_raw(self):
        with patch(
            "datadog_mcp.tools.get_dashboard.get_dashboard",
            new=AsyncMock(return_value={"id": "abc"}),
        ):
            result = await get_dashboard.handle_call(_req({"dashboard_id": "abc", "format": "json"}))
        parsed = json.loads(result.content[0].text)
        assert parsed == {"id": "abc"}


class TestDeleteDashboard:
    @pytest.mark.asyncio
    async def test_refuses_without_confirm(self):
        with patch(
            "datadog_mcp.tools.delete_dashboard.delete_dashboard",
            new=AsyncMock(side_effect=AssertionError("must not be called")),
        ):
            result = await delete_dashboard.handle_call(_req({"dashboard_id": "abc"}))
        assert result.isError is False
        assert "Dry-run" in result.content[0].text
        assert "confirm=true" in result.content[0].text

    @pytest.mark.asyncio
    async def test_deletes_with_confirm(self):
        mock_delete = AsyncMock(return_value={"deleted_dashboard_id": "abc"})
        with patch("datadog_mcp.tools.delete_dashboard.delete_dashboard", new=mock_delete):
            result = await delete_dashboard.handle_call(_req({
                "dashboard_id": "abc",
                "confirm": True,
            }))
        mock_delete.assert_awaited_once_with("abc")
        assert "deleted" in result.content[0].text


# -------------------------------------------------------------------------
# Monitor tools
# -------------------------------------------------------------------------

class TestCreateMonitor:
    @pytest.mark.asyncio
    async def test_validates_required_fields(self):
        # Missing `query`
        result = await create_monitor.handle_call(_req({
            "payload": {"type": "metric alert", "name": "x"},
        }))
        assert result.isError is True
        assert "query" in result.content[0].text

    @pytest.mark.asyncio
    async def test_happy_path(self):
        with patch(
            "datadog_mcp.tools.create_monitor.create_monitor",
            new=AsyncMock(return_value={"id": 12345, "name": "rollout cap-fire", "type": "log alert"}),
        ):
            result = await create_monitor.handle_call(_req({
                "payload": {"type": "log alert", "query": "logs(\"foo\").index(\"main\")", "name": "rollout cap-fire"},
            }))
        text = result.content[0].text
        assert "12345" in text
        assert "rollout cap-fire" in text


class TestUpdateMonitor:
    @pytest.mark.asyncio
    async def test_requires_monitor_id(self):
        result = await update_monitor.handle_call(_req({"payload": {"name": "new"}}))
        assert result.isError is True
        assert "monitor_id" in result.content[0].text

    @pytest.mark.asyncio
    async def test_partial_payload_allowed(self):
        # Unlike dashboards, monitors allow partial payloads — no required-field check
        mock_update = AsyncMock(return_value={"id": 42, "name": "renamed", "type": "log alert"})
        with patch("datadog_mcp.tools.update_monitor.update_monitor", new=mock_update):
            result = await update_monitor.handle_call(_req({
                "monitor_id": 42,
                "payload": {"name": "renamed"},
            }))
        assert result.isError is False
        mock_update.assert_awaited_once_with(42, {"name": "renamed"})


class TestMuteMonitor:
    @pytest.mark.asyncio
    async def test_mute_passes_scope(self):
        mock_mute = AsyncMock(return_value={})
        with patch("datadog_mcp.tools.mute_monitor.mute_monitor", new=mock_mute):
            await mute_monitor.handle_call(_req({
                "monitor_id": 7,
                "scope": "env:prod",
                "end": 1735689600,
            }))
        mock_mute.assert_awaited_once_with(
            monitor_id=7, scope="env:prod", end=1735689600, unmute=False,
        )

    @pytest.mark.asyncio
    async def test_unmute_flag(self):
        mock_mute = AsyncMock(return_value={})
        with patch("datadog_mcp.tools.mute_monitor.mute_monitor", new=mock_mute):
            await mute_monitor.handle_call(_req({"monitor_id": 7, "unmute": True}))
        mock_mute.assert_awaited_once()
        kwargs = mock_mute.await_args.kwargs
        assert kwargs["unmute"] is True


class TestDeleteMonitor:
    @pytest.mark.asyncio
    async def test_refuses_without_confirm(self):
        mock_delete = AsyncMock(side_effect=AssertionError("must not be called"))
        with patch("datadog_mcp.tools.delete_monitor.delete_monitor", new=mock_delete):
            result = await delete_monitor.handle_call(_req({"monitor_id": 99}))
        assert result.isError is False
        assert "Dry-run" in result.content[0].text

    @pytest.mark.asyncio
    async def test_deletes_with_confirm_and_force(self):
        mock_delete = AsyncMock(return_value={"deleted_monitor_id": 99})
        with patch("datadog_mcp.tools.delete_monitor.delete_monitor", new=mock_delete):
            result = await delete_monitor.handle_call(_req({
                "monitor_id": 99,
                "confirm": True,
                "force": True,
            }))
        mock_delete.assert_awaited_once_with(99, force=True)
        assert "deleted" in result.content[0].text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
