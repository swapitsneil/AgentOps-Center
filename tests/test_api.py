"""
FastAPI endpoint tests.
Uses AsyncClient + ASGITransport to test API routes cleanly.
All LLM and MCP calls are mocked.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest
import pytest_asyncio
import httpx
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def async_client():
    """Create an AsyncClient for the FastAPI app with all external services mocked."""
    with patch("instrumentation.setup.setup_telemetry") as mock_setup:
        mock_setup.return_value = (MagicMock(), MagicMock())
        with patch("instrumentation.setup.instrument_fastapi"):
            with patch("instrumentation.setup.LangChainInstrumentor"):
                with patch("instrumentation.setup.HTTPXClientInstrumentor"):
                    with patch("instrumentation.setup.LoggingInstrumentor"):
                        from main import app
                        transport = httpx.ASGITransport(app=app)
                        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                            yield client


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_endpoint(async_client):
    resp = await async_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "system" in data
    assert "chaos" in data


# ---------------------------------------------------------------------------
# Runs endpoints
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_runs_empty(async_client):
    resp = await async_client.get("/api/runs/")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_scenarios_list(async_client):
    resp = await async_client.get("/api/runs/scenarios/list")
    assert resp.status_code == 200
    data = resp.json()
    assert "scenarios" in data
    assert len(data["scenarios"]) > 0


@pytest.mark.asyncio
async def test_get_nonexistent_run(async_client):
    resp = await async_client.get("/api/runs/nonexistent-id-12345")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Chaos endpoints
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_chaos_state(async_client):
    resp = await async_client.get("/api/chaos/state")
    assert resp.status_code == 200
    data = resp.json()
    assert "active" in data
    assert "modes" in data
    assert "total_injected" in data


@pytest.mark.asyncio
async def test_chaos_modes(async_client):
    resp = await async_client.get("/api/chaos/modes")
    assert resp.status_code == 200
    data = resp.json()
    assert "modes" in data
    # Should have all 6 chaos modes
    assert len(data["modes"]) == 6


@pytest.mark.asyncio
async def test_enable_chaos(async_client):
    resp = await async_client.post("/api/chaos/enable", json={"mode": "llm_error", "intensity": 0.7})
    assert resp.status_code == 200
    data = resp.json()
    state = data.get("state", {})
    assert state.get("active") is True
    assert state["modes"].get("llm_error") == 0.7


@pytest.mark.asyncio
async def test_disable_chaos(async_client):
    # First enable
    await async_client.post("/api/chaos/enable", json={"mode": "llm_error", "intensity": 0.7})
    # Then disable
    resp = await async_client.post("/api/chaos/disable", json={"mode": "llm_error"})
    assert resp.status_code == 200
    data = resp.json()
    state = data.get("state", {})
    assert "llm_error" not in state.get("modes", {})


@pytest.mark.asyncio
async def test_disable_all_chaos(async_client):
    await async_client.post("/api/chaos/enable", json={"mode": "llm_error", "intensity": 0.5})
    await async_client.post("/api/chaos/enable", json={"mode": "llm_timeout", "intensity": 0.5})
    resp = await async_client.post("/api/chaos/disable", json={})
    assert resp.status_code == 200
    data = resp.json()
    state = data.get("state", {})
    assert state.get("active") is False
    assert len(state.get("modes", {})) == 0


@pytest.mark.asyncio
async def test_enable_chaos_invalid_intensity(async_client):
    # Intensity out of range — API should still accept and clamp
    resp = await async_client.post("/api/chaos/enable", json={"mode": "llm_error", "intensity": 2.5})
    assert resp.status_code == 200  # Clamping happens in injector


# ---------------------------------------------------------------------------
# Copilot suggestions endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_copilot_suggestions(async_client):
    resp = await async_client.get("/api/copilot/suggestions")
    assert resp.status_code == 200
    data = resp.json()
    assert "suggestions" in data
    assert len(data["suggestions"]) >= 5


# ---------------------------------------------------------------------------
# Compare Runs endpoint — key name fix
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_compare_runs_not_found(async_client):
    resp = await async_client.post("/api/copilot/compare", json={"run_id_a": "fake-1", "run_id_b": "fake-2"})
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data


# ---------------------------------------------------------------------------
# OTel span attribute tests (unit-level)
# ---------------------------------------------------------------------------

def test_gen_ai_system_auto_detect():
    """Verify gen_ai.system is correctly detected from model names."""
    from instrumentation.agent_spans import _detect_provider
    assert _detect_provider("groq/llama-3.1-8b-instant") == "groq"
    assert _detect_provider("openai/gpt-4o") == "openai"
    assert _detect_provider("gpt-4o-mini") == "openai"
    assert _detect_provider("anthropic/claude-3-haiku") == "anthropic"
    assert _detect_provider("claude-3-5-sonnet") == "anthropic"
    assert _detect_provider("google/gemini-pro") == "google_vertexai"
    assert _detect_provider("gemini-1.5-flash") == "google_vertexai"
    assert _detect_provider("openrouter/mistral-7b") == "openrouter"
    assert _detect_provider("unknown-model") == "unknown"
    assert _detect_provider("custom/some-model") == "custom"
