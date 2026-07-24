"""
Tests for the MCP client, Evidence Engine, and Reasoning Engine.
All MCP calls are mocked — no real SigNoz required.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from unittest.mock import patch, AsyncMock, MagicMock

from mcp.client import MCPService, MCPTrace, MCPLogRecord, MCPUnavailable, MCPToolResult
from copilot.evidence_engine import EvidenceEngine, VerifiedEvidence
from copilot.reasoning import ReasoningEngine, ConfidenceLevel


# ---------------------------------------------------------------------------
# Evidence Engine tests (using mock MCP client)
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_mcp_available():
    """Mock MCP client that returns rich telemetry."""
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock()
    client.is_available = AsyncMock(return_value=True)
    client.mcp_url = "http://mock-mcp/mcp"
    client.list_services = AsyncMock(return_value=[
        MCPService(service_name="agentops-center-backend", p99_latency_ms=245.0, error_rate=0.03)
    ])
    client.search_traces = AsyncMock(return_value=[
        MCPTrace(trace_id="aabbccdd11223344", error=True, total_duration_ms=3200.0, span_count=12),
        MCPTrace(trace_id="eeff55667788aabb", error=False, total_duration_ms=450.0, span_count=8),
    ])
    client.get_metrics = AsyncMock(return_value=[])
    client.search_logs = AsyncMock(return_value=[
        MCPLogRecord(body="[ERROR] LLM timeout", severity="ERROR", service_name="agentops-center-backend"),
    ])
    client.list_alerts = AsyncMock(return_value=[])
    return client


@pytest.fixture
def mock_mcp_unavailable():
    """Mock MCP client that simulates server being down."""
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock()
    client.is_available = AsyncMock(return_value=False)
    client.mcp_url = "http://unreachable-mcp/mcp"
    return client


@pytest.mark.asyncio
async def test_evidence_engine_mcp_available(mock_mcp_available):
    engine = EvidenceEngine(mcp_client=mock_mcp_available)
    evidence = await engine.collect(
        workflow_id="wf-test-001",
        service_name="agentops-center-backend",
        local_run_context={"status": "failed", "scenario": "db_overload", "workflow_id": "wf-test-001"},
    )

    assert evidence.mcp_available is True
    assert len(evidence.services) == 1
    assert evidence.services[0].service_name == "agentops-center-backend"
    assert evidence.trace_count == 2
    assert evidence.error_log_count == 1
    assert evidence.has_real_telemetry() is True


@pytest.mark.asyncio
async def test_evidence_engine_mcp_unavailable(mock_mcp_unavailable):
    engine = EvidenceEngine(mcp_client=mock_mcp_unavailable)
    evidence = await engine.collect(
        workflow_id="wf-test-002",
        service_name="agentops-center-backend",
        local_run_context={"status": "completed"},
    )

    assert evidence.mcp_available is False
    assert evidence.has_real_telemetry() is False
    assert evidence.local_workflow_context is not None
    # Should have at least 1 signal (the local context signal)
    assert len(evidence.signals) >= 1
    # The signal should be marked as unverified
    assert not evidence.signals[0].is_verified


@pytest.mark.asyncio
async def test_evidence_prompt_context_no_fake_trace_ids(mock_mcp_available):
    """Verify that to_prompt_context() only includes trace IDs from MCP."""
    engine = EvidenceEngine(mcp_client=mock_mcp_available)
    evidence = await engine.collect(workflow_id="wf-001", service_name="agentops-center-backend")
    ctx = evidence.to_prompt_context()

    # Should mention the real trace IDs we set in the mock
    assert "aabbccdd" in ctx or "trace_id" in ctx.lower()
    # Should NOT contain invented trace IDs
    assert "XXXX" not in ctx
    assert "fake" not in ctx.lower()


@pytest.mark.asyncio
async def test_evidence_collection_time_measured(mock_mcp_available):
    engine = EvidenceEngine(mcp_client=mock_mcp_available)
    evidence = await engine.collect(workflow_id="wf-001", service_name="agentops-center-backend")
    assert evidence.evidence_collection_ms > 0
    assert evidence.collected_at_unix > 0


# ---------------------------------------------------------------------------
# Reasoning Engine tests
# ---------------------------------------------------------------------------

def make_evidence(mcp_available=True, traces=2, error_logs=1, services=1):
    """Helper: build a VerifiedEvidence with controlled richness."""
    e = VerifiedEvidence()
    e.mcp_available = mcp_available
    e.mcp_server_url = "http://mock/mcp"
    e.trace_count = traces
    e.error_log_count = error_logs

    if mcp_available and traces > 0:
        e.recent_traces = [MCPTrace(trace_id="aabbcc112233", error=True, total_duration_ms=1200.0)]
    if mcp_available and error_logs > 0:
        e.error_logs = [MCPLogRecord(body="ERROR: LLM timeout", severity="ERROR", service_name="svc")]
    if services > 0:
        e.services = [MCPService(service_name="agentops-center-backend")]
    return e


def test_reasoning_high_confidence():
    engine = ReasoningEngine()
    e = make_evidence(mcp_available=True, traces=5, error_logs=3)
    # Add some metrics
    from mcp.client import MCPMetricPoint
    import time
    e.token_metrics = [MCPMetricPoint(metric_name="gen_ai.total_tokens", value=5000, timestamp_unix_ms=int(time.time()*1000))]
    ctx = engine.build_context(e, question="Why did the last workflow fail?")
    assert ctx.confidence == ConfidenceLevel.HIGH
    assert ctx.max_tokens >= 2048


def test_reasoning_low_confidence_when_mcp_unavailable():
    engine = ReasoningEngine()
    e = make_evidence(mcp_available=False, traces=0, error_logs=0)
    ctx = engine.build_context(e, question="Why did the workflow fail?")
    assert ctx.confidence == ConfidenceLevel.LOW
    assert "MCP" in ctx.system_prompt or "mcp" in ctx.system_prompt.lower()


def test_reasoning_medium_confidence_partial_telemetry():
    engine = ReasoningEngine()
    e = make_evidence(mcp_available=True, traces=3, error_logs=0)  # traces but no logs
    ctx = engine.build_context(e, question="What is wrong?")
    assert ctx.confidence in (ConfidenceLevel.MEDIUM, ConfidenceLevel.HIGH)


def test_reasoning_system_prompt_contains_antihalucination_rules():
    engine = ReasoningEngine()
    e = make_evidence(mcp_available=True, traces=2, error_logs=1)
    ctx = engine.build_context(e, question="Diagnose this")
    # Should contain the strict no-hallucination instruction
    assert "NEVER" in ctx.system_prompt or "never" in ctx.system_prompt.lower()
    assert "fabricat" in ctx.system_prompt.lower() or "invent" in ctx.system_prompt.lower()


def test_reasoning_can_diagnose_with_local_context_only():
    engine = ReasoningEngine()
    e = make_evidence(mcp_available=False, traces=0, error_logs=0)
    e.local_workflow_context = {"status": "failed", "scenario": "db_overload"}
    ctx = engine.build_context(e, question="What failed?")
    assert ctx.can_diagnose() is True  # Local context allows low-confidence diagnosis


def test_reasoning_evidence_context_serialized():
    engine = ReasoningEngine()
    e = make_evidence(mcp_available=True, traces=1, error_logs=1)
    ctx = engine.build_context(e)
    # Should serialize the evidence into prompt context
    assert len(ctx.evidence_context) > 100
    assert "VERIFIED" in ctx.evidence_context or "SIGNOZ" in ctx.evidence_context


# ---------------------------------------------------------------------------
# MCP client model tests
# ---------------------------------------------------------------------------

def test_mcp_unavailable_is_falsy():
    u = MCPUnavailable(reason="Connection refused")
    assert u.is_available is False


def test_mcp_tool_result_success():
    r = MCPToolResult(tool_name="signoz_list_services", success=True, raw_content=[{"type": "text", "text": "service-a"}])
    assert r.success is True
    assert r.raw_content[0]["text"] == "service-a"


def test_mcp_service_model():
    svc = MCPService(service_name="checkout", p99_latency_ms=123.0, error_rate=0.05)
    assert svc.service_name == "checkout"
    assert svc.error_rate == 0.05
