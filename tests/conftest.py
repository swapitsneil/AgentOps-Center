"""
pytest fixtures and mocks for AgentOps Center tests.
All external services (LLM, SigNoz MCP) are mocked so tests
do NOT require paid API keys or running infrastructure.
"""
import asyncio
import os
import sys
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

# Ensure backend package is on sys.path
sys.path.insert(0, str(os.path.join(os.path.dirname(__file__), "..", "backend")))


# ---------------------------------------------------------------------------
# Environment setup — avoid hitting real APIs
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """Set safe env vars so no real API calls are made."""
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key-not-real")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key-not-real")
    monkeypatch.setenv("DEFAULT_MODEL", "groq/llama-3.1-8b-instant")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:14317")
    monkeypatch.setenv("OTEL_SERVICE_NAME", "agentops-test")
    monkeypatch.setenv("SIGNOZ_MCP_URL", "http://localhost:19999/mcp")
    monkeypatch.setenv("SIGNOZ_URL", "http://localhost:19998")
    monkeypatch.setenv("SIGNOZ_API_KEY", "test-key")


# ---------------------------------------------------------------------------
# OTel mock — capture spans in memory instead of exporting
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def mock_otel():
    """Replace OTel exporters with in-memory exporters for assertions."""
    with patch("opentelemetry.sdk.trace.export.BatchSpanProcessor") as mock_bsp:
        mock_bsp.return_value = MagicMock()
        yield mock_bsp


# ---------------------------------------------------------------------------
# Mock LLM — returns deterministic responses without API calls
# ---------------------------------------------------------------------------

def make_mock_llm(response_text: str = "Mock LLM response"):
    """Create a mock LangChain chat model."""
    mock_llm = MagicMock()
    mock_chunk = MagicMock()
    mock_chunk.content = response_text

    async def mock_astream(messages):
        yield mock_chunk

    mock_llm.astream = mock_astream
    mock_llm.invoke = MagicMock(return_value=MagicMock(content=response_text))
    mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content=response_text))
    return mock_llm


# ---------------------------------------------------------------------------
# Mock MCP client — returns pre-canned responses
# ---------------------------------------------------------------------------

class MockMCPClient:
    """Mock SigNozMCPClient that returns realistic but fake MCP responses."""

    mcp_url = "http://mock-mcp/mcp"
    api_key = "test"

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def is_available(self) -> bool:
        return True

    async def list_services(self, **kwargs):
        from mcp.client import MCPService
        return [
            MCPService(service_name="agentops-center-backend", p99_latency_ms=245.0, error_rate=0.03, call_count=150),
            MCPService(service_name="agentops-center-frontend", p99_latency_ms=12.0, error_rate=0.0, call_count=50),
        ]

    async def search_traces(self, **kwargs):
        from mcp.client import MCPTrace
        filter_error = kwargs.get("filter_error", False)
        if filter_error:
            return [MCPTrace(trace_id="aaaa1111bbbb2222", error=True, total_duration_ms=3200.0, span_count=12)]
        return [
            MCPTrace(trace_id="aaaa1111bbbb2222", error=True, total_duration_ms=3200.0, span_count=12),
            MCPTrace(trace_id="cccc3333dddd4444", error=False, total_duration_ms=450.0, span_count=8),
        ]

    async def get_metrics(self, metric_name: str, **kwargs):
        from mcp.client import MCPMetricPoint
        import time
        return [MCPMetricPoint(metric_name=metric_name, value=1234.0, timestamp_unix_ms=int(time.time() * 1000))]

    async def search_logs(self, **kwargs):
        from mcp.client import MCPLogRecord
        severity = kwargs.get("severity", "INFO")
        if severity == "ERROR":
            return [
                MCPLogRecord(body="[ERROR] LLM timeout for monitor_agent after 30s", severity="ERROR", service_name="agentops-center-backend"),
                MCPLogRecord(body="[ERROR] Redis connection refused: localhost:6379", severity="ERROR", service_name="agentops-center-backend"),
            ]
        return [MCOLogRecord(body="[INFO] Workflow completed", severity="INFO", service_name="agentops-center-backend")]

    async def list_alerts(self):
        from mcp.client import MCPAlertRule
        return [
            MCPAlertRule(id="alert-1", name="LLM Error Rate > 5%", state="active", severity="warning", condition="error_rate > 0.05"),
        ]

    async def get_trace_details(self, trace_id: str):
        from mcp.client import MCPTrace, MCPSpan
        return MCPTrace(
            trace_id=trace_id,
            spans=[
                MCPSpan(span_id="span-001", trace_id=trace_id, operation_name="gen_ai.chat monitor_agent", duration_ms=2800.0, status="ERROR"),
                MCPSpan(span_id="span-002", trace_id=trace_id, operation_name="tool.log_search", duration_ms=120.0, status="OK"),
            ],
            span_count=2,
            error=True,
        )


@pytest.fixture
def mock_mcp_client():
    return MockMCPClient()
