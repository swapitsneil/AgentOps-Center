"""
Root Cause Copilot — Production Architecture.

Data flow:
    User Question
        → Evidence Engine  (calls SigNoz MCP tools → VerifiedEvidence)
        → Reasoning Engine (validates evidence, grades confidence, builds prompt)
        → LLM             (receives ONLY verified evidence + graded prompt)
        → Streaming Response

The LLM NEVER receives raw _runs dicts.
The LLM NEVER fabricates trace IDs — it can only cite what's in VerifiedEvidence.
"""
import json
import logging
import os
from typing import Optional, AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage, SystemMessage
from opentelemetry import trace
from pydantic import BaseModel

from chaos.injector import disable_chaos, get_chaos_state
from copilot.evidence_engine import EvidenceEngine
from copilot.reasoning import ReasoningEngine, ConfidenceLevel

logger = logging.getLogger("agentops.api.copilot")
router = APIRouter(prefix="/api/copilot", tags=["copilot"])
tracer = trace.get_tracer("agentops.api.copilot")

# Module-level singletons — built once at import time, not per-request
_evidence_engine = EvidenceEngine()
_reasoning_engine = ReasoningEngine()

# Cached LLM — not recreated on every request
_copilot_llm = None


def _get_copilot_llm():
    """Return a cached LLM instance (singleton per process)."""
    global _copilot_llm  # noqa: PLW0603
    if _copilot_llm is not None:
        return _copilot_llm

    model = os.getenv("DEFAULT_MODEL", "groq/llama-3.1-8b-instant")

    if model.startswith("groq/"):
        from langchain_groq import ChatGroq
        _copilot_llm = ChatGroq(
            model=model.replace("groq/", ""),
            temperature=0.1,
            max_tokens=2048,  # Fixed: was 1000 — now allows complete responses
        )
    elif model.startswith("openrouter/"):
        from langchain_openai import ChatOpenAI
        _copilot_llm = ChatOpenAI(
            model=model.replace("openrouter/", ""),
            openai_api_key=os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY"),
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0.1,
            max_tokens=2048,
            default_headers={
                "HTTP-Referer": "https://github.com/agentops-center",
                "X-Title": "AgentOps Center",
            },
        )
    else:
        # OpenAI or unknown provider
        from langchain_openai import ChatOpenAI
        _copilot_llm = ChatOpenAI(
            model=model.replace("openai/", ""),
            temperature=0.1,
            max_tokens=2048,
        )

    return _copilot_llm


def _classify_intent(question: str) -> str:
    """Classify user query intent for telemetry tagging."""
    q = question.lower()
    if any(k in q for k in ["compare", "versus", "vs"]):
        return "COMPARE_RUNS"
    if any(k in q for k in ["which agent", "agent failure", "failing agent", "agent latency"]):
        return "AGENT_ANALYTICS"
    if any(k in q for k in ["most expensive", "cost", "token", "llm spend"]):
        return "COST_ANALYTICS"
    if any(k in q for k in ["workflow latency", "slowest", "workflow performance"]):
        return "WORKFLOW_ANALYTICS"
    if any(k in q for k in ["service", "database", "dependency", "redis", "postgres"]):
        return "SERVICE_ANALYTICS"
    if any(k in q for k in ["timeline", "replay", "sequence", "order"]):
        return "TIMELINE_QUERY"
    return "INCIDENT_ANALYSIS"


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class CopilotRequest(BaseModel):
    question: str
    workflow_id: Optional[str] = None
    execution_mode: Optional[str] = "SCENARIO_INVESTIGATION"
    context: Optional[str] = None


class CompareRequest(BaseModel):
    run_id_a: str
    run_id_b: str


class ExplainSpanRequest(BaseModel):
    workflow_id: str
    agent_name: str
    span_name: Optional[str] = None


# ---------------------------------------------------------------------------
# Main copilot endpoint
# ---------------------------------------------------------------------------

@router.post("/ask")
async def ask_copilot(req: CopilotRequest):
    """
    Root Cause Copilot endpoint.

    Architecture:
        1. Collect local workflow context (from _runs, clearly labelled)
        2. Call Evidence Engine → MCP → SigNoz → VerifiedEvidence
        3. Call Reasoning Engine → confidence grading + system prompt
        4. Stream LLM response grounded in verified telemetry
    """
    with tracer.start_as_current_span("copilot.ask") as span:
        mode = req.execution_mode or "SCENARIO_INVESTIGATION"
        intent = _classify_intent(req.question)

        span.set_attribute("copilot.question", req.question[:300])
        span.set_attribute("copilot.execution_mode", mode)
        span.set_attribute("copilot.intent", intent)
        span.set_attribute("copilot.workflow_id", req.workflow_id or "")

        if mode == "SCENARIO_INVESTIGATION":
            disable_chaos()

        # Step 1: Gather local workflow context (in-memory, NOT from SigNoz)
        from api.runs import _runs
        local_run_context: Optional[dict] = None
        if req.workflow_id and req.workflow_id in _runs:
            local_run_context = _runs[req.workflow_id]
        elif _runs:
            local_run_context = list(_runs.values())[-1]

        target_service = "agentops-center-backend"

        # Step 2: Collect verified telemetry from SigNoz via MCP
        evidence = await _evidence_engine.collect(
            workflow_id=req.workflow_id,
            service_name=target_service,
            local_run_context=local_run_context,
            lookback_minutes=60,
        )

        span.set_attribute("copilot.mcp_available", evidence.mcp_available)
        span.set_attribute("copilot.trace_count", evidence.trace_count)
        span.set_attribute("copilot.error_log_count", evidence.error_log_count)
        span.set_attribute("copilot.evidence_signals", len(evidence.signals))
        span.set_attribute("copilot.evidence_collection_ms", evidence.evidence_collection_ms)

        # Step 3: Build validated reasoning context
        reasoning_ctx = _reasoning_engine.build_context(evidence, question=req.question)

        span.set_attribute("copilot.confidence", reasoning_ctx.confidence.value)

        # Step 4: Stream LLM response
        async def stream_response() -> AsyncGenerator[str, None]:
            llm = _get_copilot_llm()

            # The LLM receives: system prompt (evidence-grounded rules) +
            # evidence context (only verified MCP data) + user question
            user_prompt = (
                f"User Question: {req.question}\n\n"
                f"Execution Mode: {mode}\n"
                f"Query Intent: {intent}\n"
                f"Confidence Grade: {reasoning_ctx.confidence.value}\n"
                f"Confidence Rationale: {reasoning_ctx.confidence_rationale}\n\n"
                f"{reasoning_ctx.evidence_context}\n\n"
                f"Provide your Root Cause Analysis now:"
            )

            messages = [
                SystemMessage(content=reasoning_ctx.system_prompt),
                HumanMessage(content=user_prompt),
            ]

            try:
                async for chunk in llm.astream(messages):
                    if chunk.content:
                        yield f"data: {json.dumps({'content': chunk.content, 'done': False})}\n\n"
                yield f"data: {json.dumps({'content': '', 'done': True, 'metadata': {'confidence': reasoning_ctx.confidence.value, 'mcp_available': evidence.mcp_available, 'signals': len(evidence.signals)}})}\n\n"
            except Exception as exc:
                span.record_exception(exc)
                logger.error("Copilot LLM stream error: %s", exc)
                yield f"data: {json.dumps({'content': f'Copilot error: {exc}', 'done': True})}\n\n"

        return StreamingResponse(
            stream_response(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )


# ---------------------------------------------------------------------------
# Compare Runs — fixed key name mismatch (audit issue #7)
# ---------------------------------------------------------------------------

@router.post("/compare")
async def compare_runs(req: CompareRequest):
    """
    Compare two workflow runs side-by-side.
    Fixed: Frontend expects 'total_duration_ms' and 'total_cost_usd' —
    now returns keys that match what the frontend CompareRuns component reads.
    """
    from api.runs import _runs

    run_a = _runs.get(req.run_id_a)
    run_b = _runs.get(req.run_id_b)
    if not run_a or not run_b:
        return {"error": "One or both run IDs not found"}

    def _summarize(run: dict) -> dict:
        res = run.get("result") or {}
        timings = res.get("agent_timings") or {}
        cost = res.get("cost_summary") or {}
        return {
            "id": run.get("workflow_id", ""),
            "status": run.get("status", "unknown"),
            "scenario": run.get("scenario", ""),
            # Frontend reads total_duration_ms
            "total_duration_ms": sum(timings.values()) if timings else 0,
            # Frontend reads total_cost_usd
            "total_cost_usd": cost.get("total_cost_usd", 0),
            "agent_timings": timings,
            "error": res.get("error"),
        }

    a = _summarize(run_a)
    b = _summarize(run_b)

    duration_delta = a["total_duration_ms"] - b["total_duration_ms"]
    cost_delta = a["total_cost_usd"] - b["total_cost_usd"]

    return {
        "comparison": {
            "run_a": a,
            "run_b": b,
            "delta": {
                "status_change": f"{a['status']} → {b['status']}",
                "duration_delta_ms": round(duration_delta, 2),
                "cost_delta_usd": round(cost_delta, 8),
                "faster_run": req.run_id_b if duration_delta > 0 else req.run_id_a,
                "cheaper_run": req.run_id_b if cost_delta > 0 else req.run_id_a,
            },
        }
    }


@router.post("/explain-span")
async def explain_span(req: ExplainSpanRequest):
    """Explain a specific agent span."""
    from api.runs import _runs

    run = _runs.get(req.workflow_id)
    if not run:
        return {"error": f"Workflow run {req.workflow_id} not found"}

    res = run.get("result") or {}
    timings = res.get("agent_timings") or {}
    output_key = f"{req.agent_name.replace('_agent', '')}_output"
    agent_output = res.get(output_key) or res.get("error")

    return {
        "span_explanation": {
            "workflow_id": req.workflow_id,
            "agent_name": req.agent_name,
            "duration_ms": timings.get(req.agent_name, 0),
            "output_snippet": str(agent_output)[:400] if agent_output else "No output",
            "note": "For detailed span attributes, open SigNoz Traces and search for this workflow_id",
        }
    }


@router.get("/suggestions")
async def get_suggestions():
    """Return pre-loaded copilot question prompts."""
    return {
        "suggestions": [
            "Why did the last workflow fail?",
            "Which agent is causing the most failures?",
            "What is the root cause of the high latency?",
            "How can I reduce the cost of the diagnosis agent?",
            "Compare the performance of the last 3 runs",
            "Generate a postmortem for the last incident",
            "What is the p99 latency for agentops-center-backend?",
            "Which tool calls are failing most often?",
            "Are there any active alerts in SigNoz?",
            "Show me the top operations by error rate",
        ]
    }
