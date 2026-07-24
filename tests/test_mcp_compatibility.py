"""
Automated compatibility tests validating SigNozMCPClient helpers
against the official SigNoz MCP tool manifest schema.
"""
import json
import os
import sys
import pytest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from mcp.client import SigNozMCPClient


# Load official manifest dumped from live signoz-mcp-server
MANIFEST_PATH = os.path.join(os.path.dirname(__file__), "..", "mcp_manifest_raw.json")

@pytest.fixture(scope="module")
def official_manifest():
    assert os.path.exists(MANIFEST_PATH), f"Manifest file missing: {MANIFEST_PATH}"
    with open(MANIFEST_PATH) as f:
        tools = json.load(f)
    return {t["name"]: t for t in tools}


def validate_tool_arguments(tool_name: str, args: dict, manifest_dict: dict):
    """
    Validate that arguments passed to _call_tool match the official MCP tool schema:
    1. Tool name must exist in manifest.
    2. All passed keys must exist in schema properties.
    3. All required fields in schema must be present in args.
    """
    assert tool_name in manifest_dict, f"Tool '{tool_name}' not in official MCP manifest"
    schema = manifest_dict[tool_name].get("inputSchema", {})
    props = schema.get("properties", {})
    required = schema.get("required", [])

    # Check unknown parameters
    for key in args:
        if key == "searchContext":  # Automatically appended by _call_tool
            continue
        assert key in props, (
            f"Parameter '{key}' passed to '{tool_name}' is NOT in official schema properties: {list(props.keys())}"
        )

    # Check required fields
    for req_key in required:
        assert req_key in args, (
            f"Required parameter '{req_key}' for '{tool_name}' is missing in call arguments: {list(args.keys())}"
        )


@pytest.mark.asyncio
async def test_search_traces_compatibility(official_manifest):
    client = SigNozMCPClient()
    captured_calls = []

    async def mock_call(tool_name, args=None):
        captured_calls.append((tool_name, args or {}))
        return AsyncMock(success=True, raw_content=[])

    with patch.object(client, "_call_tool", side_effect=mock_call):
        await client.search_traces(service_name="test-svc", filter_error=True)

    assert len(captured_calls) == 1
    tool_name, args = captured_calls[0]
    assert tool_name == "signoz_search_traces"
    assert args["service"] == "test-svc"
    assert args["error"] is True
    validate_tool_arguments(tool_name, args, official_manifest)


@pytest.mark.asyncio
async def test_get_trace_details_compatibility(official_manifest):
    client = SigNozMCPClient()
    captured_calls = []

    async def mock_call(tool_name, args=None):
        captured_calls.append((tool_name, args or {}))
        return AsyncMock(success=True, raw_content=[])

    with patch.object(client, "_call_tool", side_effect=mock_call):
        await client.get_trace_details(trace_id="abc123trace")

    assert len(captured_calls) == 1
    tool_name, args = captured_calls[0]
    assert tool_name == "signoz_get_trace_details"
    assert "traceId" in args, "Must use 'traceId', not 'traceID'"
    assert "traceID" not in args
    validate_tool_arguments(tool_name, args, official_manifest)


@pytest.mark.asyncio
async def test_search_logs_compatibility(official_manifest):
    client = SigNozMCPClient()
    captured_calls = []

    async def mock_call(tool_name, args=None):
        captured_calls.append((tool_name, args or {}))
        return AsyncMock(success=True, raw_content=[])

    with patch.object(client, "_call_tool", side_effect=mock_call):
        await client.search_logs(service_name="test-svc", severity="ERROR")

    assert len(captured_calls) == 1
    tool_name, args = captured_calls[0]
    assert tool_name == "signoz_search_logs"
    assert args["service"] == "test-svc"
    assert args["severity"] == "ERROR"
    validate_tool_arguments(tool_name, args, official_manifest)


@pytest.mark.asyncio
async def test_get_service_top_operations_compatibility(official_manifest):
    client = SigNozMCPClient()
    captured_calls = []

    async def mock_call(tool_name, args=None):
        captured_calls.append((tool_name, args or {}))
        return AsyncMock(success=True, raw_content=[])

    with patch.object(client, "_call_tool", side_effect=mock_call):
        await client.get_service_top_operations(service_name="test-svc")

    assert len(captured_calls) == 1
    tool_name, args = captured_calls[0]
    assert tool_name == "signoz_get_service_top_operations"
    assert "service" in args, "Must use 'service', not 'serviceName'"
    assert "serviceName" not in args
    validate_tool_arguments(tool_name, args, official_manifest)


@pytest.mark.asyncio
async def test_aggregate_traces_compatibility(official_manifest):
    client = SigNozMCPClient()
    captured_calls = []

    async def mock_call(tool_name, args=None):
        captured_calls.append((tool_name, args or {}))
        return AsyncMock(success=True, raw_content=[])

    with patch.object(client, "_call_tool", side_effect=mock_call):
        await client.aggregate_traces(service_name="test-svc", aggregation="count", group_by="name")

    assert len(captured_calls) == 1
    tool_name, args = captured_calls[0]
    assert tool_name == "signoz_aggregate_traces"
    assert args["aggregation"] == "count"
    assert args["service"] == "test-svc"
    assert args["groupBy"] == ["name"]
    validate_tool_arguments(tool_name, args, official_manifest)


@pytest.mark.asyncio
async def test_get_metrics_compatibility(official_manifest):
    client = SigNozMCPClient()
    captured_calls = []

    async def mock_call(tool_name, args=None):
        captured_calls.append((tool_name, args or {}))
        return AsyncMock(success=True, raw_content=[])

    with patch.object(client, "_call_tool", side_effect=mock_call):
        await client.get_metrics(metric_name="gen_ai.total_tokens", group_by=["agent.name"])

    assert len(captured_calls) == 1
    tool_name, args = captured_calls[0]
    assert tool_name == "signoz_query_metrics"
    assert args["metricName"] == "gen_ai.total_tokens"
    assert args["groupBy"] == ["agent.name"]
    validate_tool_arguments(tool_name, args, official_manifest)


@pytest.mark.asyncio
async def test_list_services_compatibility(official_manifest):
    client = SigNozMCPClient()
    captured_calls = []

    async def mock_call(tool_name, args=None):
        captured_calls.append((tool_name, args or {}))
        return AsyncMock(success=True, raw_content=[])

    with patch.object(client, "_call_tool", side_effect=mock_call):
        await client.list_services()

    assert len(captured_calls) == 1
    tool_name, args = captured_calls[0]
    assert tool_name == "signoz_list_services"
    validate_tool_arguments(tool_name, args, official_manifest)


@pytest.mark.asyncio
async def test_list_alerts_compatibility(official_manifest):
    client = SigNozMCPClient()
    captured_calls = []

    async def mock_call(tool_name, args=None):
        captured_calls.append((tool_name, args or {}))
        return AsyncMock(success=True, raw_content=[])

    with patch.object(client, "_call_tool", side_effect=mock_call):
        await client.list_alerts()

    assert len(captured_calls) == 1
    tool_name, args = captured_calls[0]
    assert tool_name == "signoz_list_alert_rules"
    validate_tool_arguments(tool_name, args, official_manifest)


@pytest.mark.asyncio
async def test_list_metrics_compatibility(official_manifest):
    client = SigNozMCPClient()
    captured_calls = []

    async def mock_call(tool_name, args=None):
        captured_calls.append((tool_name, args or {}))
        return AsyncMock(success=True, raw_content=[])

    with patch.object(client, "_call_tool", side_effect=mock_call):
        await client.list_metrics(search_text="gen_ai")

    assert len(captured_calls) == 1
    tool_name, args = captured_calls[0]
    assert tool_name == "signoz_list_metrics"
    assert args["searchText"] == "gen_ai"
    validate_tool_arguments(tool_name, args, official_manifest)


@pytest.mark.asyncio
async def test_execute_builder_query_compatibility(official_manifest):
    client = SigNozMCPClient()
    captured_calls = []

    async def mock_call(tool_name, args=None):
        captured_calls.append((tool_name, args or {}))
        return AsyncMock(success=True, raw_content=[])

    with patch.object(client, "_call_tool", side_effect=mock_call):
        await client.execute_builder_query(query={"builderQueries": {}})

    assert len(captured_calls) == 1
    tool_name, args = captured_calls[0]
    assert tool_name == "signoz_execute_builder_query"
    assert "query" in args
    validate_tool_arguments(tool_name, args, official_manifest)
