"""
DevOps Incident Response Multi-Agent Workflow.

Workflow: Monitor → Diagnosis → Fix → Report

Each node is fully instrumented with rich OTel spans (LLM, Tool, Redis, DB SQL, Third-Party API).
The workflow uses LangGraph StateGraph with typed state.
"""
import asyncio
import os
import uuid
import time
from typing import TypedDict, Annotated, List, Optional
from enum import Enum

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from opentelemetry import trace
from opentelemetry.trace import StatusCode

from instrumentation.agent_spans import (
    llm_span, tool_span, redis_span, db_span, third_party_api_span,
    record_llm_usage, record_agent_transition
)
from instrumentation.cost_tracker import WorkflowCostSummary, workflow_duration_histogram
from chaos.injector import chaos_check_llm, chaos_corrupt_output, get_chaos_state

tracer = trace.get_tracer("agentops.workflow")


class WorkflowStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentState(TypedDict):
    """Shared state passed between all agents in the workflow."""
    workflow_id: str
    incident_scenario: str          # The incident to investigate
    messages: Annotated[List[BaseMessage], add_messages]
    # Per-agent outputs
    monitor_output: Optional[str]
    diagnosis_output: Optional[str]
    fix_output: Optional[str]
    report_output: Optional[str]
    # Metadata
    status: WorkflowStatus
    error: Optional[str]
    cost_summary: Optional[dict]
    agent_timings: dict             # {agent_name: duration_ms}
    current_agent: str


class AgentWorkflow:
    """LangGraph-based multi-agent workflow for DevOps incident response."""
    
    def __init__(self, model: str | None = None):
        self.model_name = model or os.getenv("DEFAULT_MODEL", "groq/llama-3.1-8b-instant")
        self._llm = self._create_llm()
        self.graph = self._build_graph()
    
    def _create_llm(self):
        """Create LLM instance supporting Groq, OpenRouter, or OpenAI."""
        if self.model_name.startswith("groq/"):
            from langchain_groq import ChatGroq
            model = self.model_name.replace("groq/", "")
            return ChatGroq(model=model, temperature=0.1, max_tokens=512)
        
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if self.model_name.startswith("openrouter/") or openrouter_key:
            model = self.model_name.replace("openrouter/", "")
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=model,
                openai_api_key=openrouter_key or os.getenv("OPENAI_API_KEY"),
                openai_api_base="https://openrouter.ai/api/v1",
                temperature=0.1,
                max_tokens=512,
                default_headers={
                    "HTTP-Referer": "https://github.com/agentops-center",
                    "X-Title": "AgentOps Center"
                }
            )
        elif self.model_name.startswith("openai/") or self.model_name.startswith("gpt"):
            from langchain_openai import ChatOpenAI
            model = self.model_name.replace("openai/", "")
            return ChatOpenAI(model=model, temperature=0.1, max_tokens=512)
        else:
            if openrouter_key:
                from langchain_openai import ChatOpenAI
                return ChatOpenAI(
                    model=self.model_name,
                    openai_api_key=openrouter_key,
                    openai_api_base="https://openrouter.ai/api/v1",
                    temperature=0.1,
                    max_tokens=512
                )
            from langchain_groq import ChatGroq
            return ChatGroq(model="llama-3.1-8b-instant", temperature=0.1, max_tokens=512)
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph StateGraph with 4 agents."""
        workflow = StateGraph(AgentState)
        
        workflow.add_node("monitor", self.monitor_node)
        workflow.add_node("diagnosis", self.diagnosis_node)
        workflow.add_node("fix", self.fix_node)
        workflow.add_node("report", self.report_node)
        
        workflow.set_entry_point("monitor")
        workflow.add_edge("monitor", "diagnosis")
        workflow.add_edge("diagnosis", "fix")
        workflow.add_edge("fix", "report")
        workflow.add_edge("report", END)
        
        return workflow.compile()
    
    async def monitor_node(self, state: AgentState) -> AgentState:
        """Monitor Agent: Detect and characterize the incident."""
        start_time = time.monotonic()
        wf_id = state["workflow_id"]
        scenario = state["incident_scenario"].lower()
        agent_name = "monitor_agent"
        
        with tracer.start_as_current_span(f"agent.{agent_name}") as span:
            span.set_attribute("agent.name", agent_name)
            span.set_attribute("agent.workflow_id", wf_id)
            span.set_attribute("agent.node", "monitor")
            
            cost_summary = WorkflowCostSummary(workflow_id=wf_id)
            
            # Emit component-specific spans based on scenario attributes
            if "redis" in scenario:
                with redis_span("GET", "user_session_token", wf_id, cache_hit=False) as rs:
                    await asyncio.sleep(0.1)
            
            if any(k in scenario for k in ["database", "sql", "pool"]):
                with db_span("SELECT * FROM transactions WHERE status = 'PENDING'", wf_id, active_connections=48, max_connections=50) as ds:
                    await asyncio.sleep(0.2)
                    
            if any(k in scenario for k in ["payment", "api", "rate limit", "third party"]):
                with third_party_api_span("StripePaymentGateway", "https://api.stripe.com/v1/charges", wf_id, status_code=429, rate_limit_remaining=0) as ps:
                    await asyncio.sleep(0.15)
            
            # Simulate metrics check tool call
            with tool_span("metrics_check", agent_name, wf_id, state["incident_scenario"]) as ts:
                await asyncio.sleep(0.3)
                metrics_data = {
                    "cpu_usage": 94.2,
                    "error_rate": 0.34,
                    "p99_latency_ms": 8420,
                    "active_alerts": 3
                }
                ts.set_attribute("tool.output", str(metrics_data))
            
            record_agent_transition("", agent_name, wf_id, "workflow_start")
            
            try:
                await chaos_check_llm(agent_name, wf_id)
                
                prompt = f"""You are a DevOps monitor agent. Analyze this production incident scenario:

Scenario: {state['incident_scenario']}
Current Metrics: CPU={metrics_data['cpu_usage']}%, Error Rate={metrics_data['error_rate']*100:.1f}%, P99 Latency={metrics_data['p99_latency_ms']}ms, Active Alerts={metrics_data['active_alerts']}

Provide a brief incident characterization (2-3 sentences): severity level, affected systems, and immediate impact."""
                
                with llm_span(agent_name, self.model_name, "chat", wf_id, "openai", prompt[:100]) as ls:
                    response = await self._llm.ainvoke([HumanMessage(content=prompt)])
                    usage = response.usage_metadata or {}
                    cost = record_llm_usage(
                        ls,
                        input_tokens=usage.get("input_tokens", 120),
                        output_tokens=usage.get("output_tokens", 80),
                        model=self.model_name,
                        completion_summary=response.content[:200],
                    )
                    cost_summary.add_llm_call(agent_name, usage.get("input_tokens", 120), usage.get("output_tokens", 80), cost)
                
                monitor_output = chaos_corrupt_output(response.content, agent_name, wf_id)
                span.set_attribute("agent.output", monitor_output[:300])
                
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(StatusCode.ERROR, str(exc))
                return {**state, "status": WorkflowStatus.FAILED, "error": str(exc), 
                        "monitor_output": f"[ERROR] {exc}", "current_agent": agent_name}
            
            duration_ms = int((time.monotonic() - start_time) * 1000)
            span.set_attribute("agent.duration_ms", duration_ms)
            
            return {
                **state,
                "monitor_output": monitor_output,
                "messages": [AIMessage(content=monitor_output, name=agent_name)],
                "agent_timings": {**state.get("agent_timings", {}), agent_name: duration_ms},
                "current_agent": "diagnosis_agent",
                "cost_summary": cost_summary.to_dict(),
            }
    
    async def diagnosis_node(self, state: AgentState) -> AgentState:
        """Diagnosis Agent: Perform root cause analysis."""
        start_time = time.monotonic()
        wf_id = state["workflow_id"]
        scenario = state["incident_scenario"].lower()
        agent_name = "diagnosis_agent"
        
        if state.get("status") == WorkflowStatus.FAILED:
            return state
        
        with tracer.start_as_current_span(f"agent.{agent_name}") as span:
            span.set_attribute("agent.name", agent_name)
            span.set_attribute("agent.workflow_id", wf_id)
            span.set_attribute("agent.node", "diagnosis")
            
            record_agent_transition("monitor_agent", agent_name, wf_id, "monitor_complete")
            
            # Emit diagnosis component spans
            if "redis" in scenario:
                with redis_span("KEYS", "cache:*:stale", wf_id, cache_hit=False) as rs:
                    await asyncio.sleep(0.15)
            
            if any(k in scenario for k in ["database", "sql", "pool"]):
                with db_span("SELECT pg_stat_activity WHERE state = 'active'", wf_id, active_connections=50, max_connections=50) as ds:
                    await asyncio.sleep(0.25)
            
            with tool_span("log_search", agent_name, wf_id, "search error logs last 1h") as ts:
                await asyncio.sleep(0.4)
                ts.set_attribute("tool.output", "Found 847 ERROR entries in service-gateway")
            
            try:
                await chaos_check_llm(agent_name, wf_id)
                
                prompt = f"""You are a DevOps diagnosis agent performing root cause analysis.

Incident Summary: {state.get('monitor_output', 'Unknown incident')}
System: {state['incident_scenario']}

Provide root cause analysis (2-3 sentences): What is the likely root cause? What system is the origin?"""
                
                with llm_span(agent_name, self.model_name, "chat", wf_id, "openai", prompt[:100]) as ls:
                    response = await self._llm.ainvoke([HumanMessage(content=prompt)])
                    usage = response.usage_metadata or {}
                    cost = record_llm_usage(
                        ls,
                        input_tokens=usage.get("input_tokens", 150),
                        output_tokens=usage.get("output_tokens", 100),
                        model=self.model_name,
                        completion_summary=response.content[:200],
                    )
                
                diagnosis_output = chaos_corrupt_output(response.content, agent_name, wf_id)
                span.set_attribute("agent.output", diagnosis_output[:300])
                
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(StatusCode.ERROR, str(exc))
                return {**state, "status": WorkflowStatus.FAILED, "error": str(exc),
                        "diagnosis_output": f"[ERROR] {exc}", "current_agent": agent_name}
            
            duration_ms = int((time.monotonic() - start_time) * 1000)
            span.set_attribute("agent.duration_ms", duration_ms)
            
            return {
                **state,
                "diagnosis_output": diagnosis_output,
                "messages": [AIMessage(content=diagnosis_output, name=agent_name)],
                "agent_timings": {**state.get("agent_timings", {}), agent_name: duration_ms},
                "current_agent": "fix_agent",
            }
    
    async def fix_node(self, state: AgentState) -> AgentState:
        """Fix Agent: Generate remediation steps."""
        start_time = time.monotonic()
        wf_id = state["workflow_id"]
        agent_name = "fix_agent"
        
        if state.get("status") == WorkflowStatus.FAILED:
            return state
        
        with tracer.start_as_current_span(f"agent.{agent_name}") as span:
            span.set_attribute("agent.name", agent_name)
            span.set_attribute("agent.workflow_id", wf_id)
            span.set_attribute("agent.node", "fix")
            
            record_agent_transition("diagnosis_agent", agent_name, wf_id, "diagnosis_complete")
            
            with tool_span("runbook_lookup", agent_name, wf_id, "database connection pool") as ts:
                await asyncio.sleep(0.3)
                ts.set_attribute("tool.output", "Runbook DB-003: Connection Pool Exhaustion")
            
            try:
                await chaos_check_llm(agent_name, wf_id)
                
                prompt = f"""You are a DevOps fix agent. Generate remediation steps.

Root Cause: {state.get('diagnosis_output', 'Unknown')}
System: {state['incident_scenario']}

Provide exactly 3 numbered remediation steps, each one sentence."""
                
                with llm_span(agent_name, self.model_name, "chat", wf_id, "openai", prompt[:100]) as ls:
                    response = await self._llm.ainvoke([HumanMessage(content=prompt)])
                    usage = response.usage_metadata or {}
                    cost = record_llm_usage(
                        ls,
                        input_tokens=usage.get("input_tokens", 130),
                        output_tokens=usage.get("output_tokens", 90),
                        model=self.model_name,
                        completion_summary=response.content[:200],
                    )
                
                fix_output = chaos_corrupt_output(response.content, agent_name, wf_id)
                span.set_attribute("agent.output", fix_output[:300])
                
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(StatusCode.ERROR, str(exc))
                return {**state, "status": WorkflowStatus.FAILED, "error": str(exc),
                        "fix_output": f"[ERROR] {exc}", "current_agent": agent_name}
            
            duration_ms = int((time.monotonic() - start_time) * 1000)
            span.set_attribute("agent.duration_ms", duration_ms)
            
            return {
                **state,
                "fix_output": fix_output,
                "messages": [AIMessage(content=fix_output, name=agent_name)],
                "agent_timings": {**state.get("agent_timings", {}), agent_name: duration_ms},
                "current_agent": "report_agent",
            }
    
    async def report_node(self, state: AgentState) -> AgentState:
        """Report Agent: Generate final incident report."""
        start_time = time.monotonic()
        wf_id = state["workflow_id"]
        agent_name = "report_agent"
        
        if state.get("status") == WorkflowStatus.FAILED:
            return state
        
        with tracer.start_as_current_span(f"agent.{agent_name}") as span:
            span.set_attribute("agent.name", agent_name)
            span.set_attribute("agent.workflow_id", wf_id)
            span.set_attribute("agent.node", "report")
            
            record_agent_transition("fix_agent", agent_name, wf_id, "fix_complete")
            
            try:
                await chaos_check_llm(agent_name, wf_id)
                
                prompt = f"""You are a DevOps report agent. Generate a brief incident report summary.

Incident: {state['incident_scenario']}
Characterization: {state.get('monitor_output', '')[:150]}
Diagnosis: {state.get('diagnosis_output', '')[:150]}
Fix Plan: {state.get('fix_output', '')[:150]}

Provide an executive incident postmortem summary in 3 concise bullet points."""
                
                with llm_span(agent_name, self.model_name, "chat", wf_id, "openai", prompt[:100]) as ls:
                    response = await self._llm.ainvoke([HumanMessage(content=prompt)])
                    usage = response.usage_metadata or {}
                    cost = record_llm_usage(
                        ls,
                        input_tokens=usage.get("input_tokens", 160),
                        output_tokens=usage.get("output_tokens", 110),
                        model=self.model_name,
                        completion_summary=response.content[:200],
                    )
                
                report_output = chaos_corrupt_output(response.content, agent_name, wf_id)
                span.set_attribute("agent.output", report_output[:300])
                
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(StatusCode.ERROR, str(exc))
                return {**state, "status": WorkflowStatus.FAILED, "error": str(exc),
                        "report_output": f"[ERROR] {exc}", "current_agent": agent_name}
            
            duration_ms = int((time.monotonic() - start_time) * 1000)
            span.set_attribute("agent.duration_ms", duration_ms)
            
            total_duration = sum({**state.get("agent_timings", {}), agent_name: duration_ms}.values())
            workflow_duration_histogram.record(total_duration, {"workflow.id": wf_id})
            
            return {
                **state,
                "report_output": report_output,
                "messages": [AIMessage(content=report_output, name=agent_name)],
                "agent_timings": {**state.get("agent_timings", {}), agent_name: duration_ms},
                "status": WorkflowStatus.COMPLETED,
                "current_agent": "complete",
            }
    
    async def run(self, incident_scenario: str, workflow_id: str | None = None) -> dict:
        """Run the full multi-agent workflow."""
        wf_id = workflow_id or f"wf-{uuid.uuid4().hex[:8]}"
        initial_state: AgentState = {
            "workflow_id": wf_id,
            "incident_scenario": incident_scenario,
            "messages": [],
            "monitor_output": None,
            "diagnosis_output": None,
            "fix_output": None,
            "report_output": None,
            "status": WorkflowStatus.RUNNING,
            "error": None,
            "cost_summary": None,
            "agent_timings": {},
            "current_agent": "monitor",
        }
        
        with tracer.start_as_current_span(f"agent.workflow {wf_id}") as span:
            span.set_attribute("agent.workflow_id", wf_id)
            span.set_attribute("agent.scenario", incident_scenario)
            
            try:
                final_state = await self.graph.ainvoke(initial_state)
                status = final_state.get("status", WorkflowStatus.COMPLETED)
                span.set_attribute("agent.workflow.status", status.value if isinstance(status, WorkflowStatus) else status)
                return final_state
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(StatusCode.ERROR, str(exc))
                return {
                    **initial_state,
                    "status": WorkflowStatus.FAILED,
                    "error": str(exc),
                }
