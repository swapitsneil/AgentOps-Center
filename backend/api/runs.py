"""
Workflow execution API endpoints.
Supports triggering runs and streaming real-time status via SSE.
"""
import asyncio
import json
import uuid
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from opentelemetry import trace

from agents.graph import AgentWorkflow, WorkflowStatus

router = APIRouter(prefix="/api/runs", tags=["runs"])
tracer = trace.get_tracer("agentops.api.runs")

# In-memory run store (demo only)
_runs: dict = {}
_workflow = None

DEFAULT_SCENARIOS = [
    "Database connection pool exhaustion causing 500 errors in payment service",
    "Memory leak in recommendation engine causing OOM kills every 2 hours",
    "Third-party API rate limiting causing cascade failures in checkout flow",
    "Misconfigured load balancer routing 80% traffic to single pod",
    "Redis cache invalidation bug causing stale data serving to users",
]


class RunRequest(BaseModel):
    scenario: Optional[str] = None  # If None, pick random default
    model: Optional[str] = None


class RunResponse(BaseModel):
    workflow_id: str
    status: str
    scenario: str


def get_workflow(model: str | None = None) -> AgentWorkflow:
    global _workflow
    if _workflow is None or model:
        _workflow = AgentWorkflow(model=model)
    return _workflow


@router.post("/trigger", response_model=RunResponse)
async def trigger_run(req: RunRequest, background_tasks: BackgroundTasks):
    """Trigger a new incident response workflow run."""
    import random
    workflow_id = f"wf-{uuid.uuid4().hex[:8]}"
    scenario = req.scenario or random.choice(DEFAULT_SCENARIOS)
    
    _runs[workflow_id] = {
        "workflow_id": workflow_id,
        "status": "running",
        "scenario": scenario,
        "result": None,
    }
    
    async def _execute():
        workflow = get_workflow(req.model)
        result = await workflow.run(scenario, workflow_id)
        _runs[workflow_id]["status"] = result.get("status", "unknown")
        _runs[workflow_id]["result"] = {
            "monitor_output": result.get("monitor_output"),
            "diagnosis_output": result.get("diagnosis_output"),
            "fix_output": result.get("fix_output"),
            "report_output": result.get("report_output"),
            "agent_timings": result.get("agent_timings", {}),
            "cost_summary": result.get("cost_summary"),
            "error": result.get("error"),
        }
    
    background_tasks.add_task(_execute)
    return RunResponse(workflow_id=workflow_id, status="running", scenario=scenario)


@router.get("/{workflow_id}")
async def get_run(workflow_id: str):
    """Get the status and result of a workflow run."""
    if workflow_id not in _runs:
        raise HTTPException(status_code=404, detail=f"Run {workflow_id} not found")
    return _runs[workflow_id]


@router.get("/")
async def list_runs():
    """List all workflow runs."""
    return list(reversed(list(_runs.values())))[:20]


@router.get("/{workflow_id}/stream")
async def stream_run(workflow_id: str):
    """SSE endpoint: stream real-time status updates for a run."""
    async def generate():
        while True:
            run = _runs.get(workflow_id)
            if not run:
                yield f"data: {json.dumps({'error': 'not found'})}\n\n"
                return
            
            yield f"data: {json.dumps(run)}\n\n"
            
            if run["status"] in ("completed", "failed"):
                return
            
            await asyncio.sleep(0.5)
    
    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})


@router.get("/scenarios/list")
async def get_scenarios():
    """Return the list of demo incident scenarios."""
    return {"scenarios": DEFAULT_SCENARIOS}
