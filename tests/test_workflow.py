"""
Integration test suite for AgentOps Center multi-agent workflow.
"""
import pytest
import asyncio
from agents.graph import AgentWorkflow

@pytest.mark.asyncio
async def test_workflow_execution():
    workflow = AgentWorkflow()
    result = await workflow.run("Database connection pool exhaustion scenario")
    assert result["status"] in ["completed", "failed"]
    assert "workflow_id" in result
