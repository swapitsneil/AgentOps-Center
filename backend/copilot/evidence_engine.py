"""
Evidence Engine for the Root Cause Copilot.

Responsibility: Collect REAL telemetry from SigNoz via the MCP client,
structure it into a VerifiedEvidence object, and pass ONLY verified
data to the reasoning engine and LLM.

The LLM must NEVER receive raw _runs dicts or fabricated trace IDs.
It receives ONLY evidence that was returned by actual MCP tool calls.
"""
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from mcp.client import (
    MCPAlertRule, MCPLogRecord, MCPMetricPoint, MCPService,
    MCPSpan, MCPTrace, MCPUnavailable, SigNozMCPClient,
)

logger = logging.getLogger("agentops.copilot.evidence")


# ---------------------------------------------------------------------------
# Evidence data structures
# ---------------------------------------------------------------------------

@dataclass
class TelemetrySignal:
    """A single verified telemetry signal with its source."""
    signal_type: str          # "trace", "metric", "log", "alert"
    source_tool: str          # The MCP tool that returned this (e.g. "signoz_search_traces")
    value: str                # Human-readable representation
    is_verified: bool = True  # False if MCP was unavailable
    raw: object = None        # Original Pydantic model for detailed inspection


@dataclass
class VerifiedEvidence:
    """
    The complete body of verified telemetry evidence for one copilot question.

    IMPORTANT: Every field in this class came from a real MCP tool call.
    The reasoning engine and LLM must use only these fields — never the
    _runs dict, never fabricated data.
    """
    # Availability
    mcp_available: bool = False
    mcp_server_url: str = ""
    evidence_collection_ms: float = 0.0
    collected_at_unix: float = 0.0

    # Service context
    services: list[MCPService] = field(default_factory=list)
    target_service: str = "agentops-center-backend"

    # Traces
    recent_traces: list[MCPTrace] = field(default_factory=list)
    error_traces: list[MCPTrace] = field(default_factory=list)
    trace_count: int = 0
    error_trace_count: int = 0

    # Metrics
    token_metrics: list[MCPMetricPoint] = field(default_factory=list)
    cost_metrics: list[MCPMetricPoint] = field(default_factory=list)
    duration_metrics: list[MCPMetricPoint] = field(default_factory=list)
    llm_call_metrics: list[MCPMetricPoint] = field(default_factory=list)

    # Logs
    error_logs: list[MCPLogRecord] = field(default_factory=list)
    recent_logs: list[MCPLogRecord] = field(default_factory=list)
    error_log_count: int = 0

    # Alerts
    active_alerts: list[MCPAlertRule] = field(default_factory=list)

    # Aggregated signals for the LLM
    signals: list[TelemetrySignal] = field(default_factory=list)

    # Local workflow context (in-memory, not from MCP — clearly labelled)
    local_workflow_context: Optional[dict] = None

    def has_real_telemetry(self) -> bool:
        """True if at least some real MCP data was collected."""
        return self.mcp_available and (
            len(self.recent_traces) > 0
            or len(self.token_metrics) > 0
            or len(self.error_logs) > 0
            or len(self.active_alerts) > 0
            or len(self.services) > 0
        )

    def to_prompt_context(self) -> str:
        """
        Serialize evidence into a structured string for the LLM prompt.
        Every section is clearly labelled with its source (MCP tool name).
        """
        lines: list[str] = []

        lines.append("=== VERIFIED SIGNOZ TELEMETRY (Source: SigNoz MCP Tools) ===")
        lines.append(f"MCP Server: {self.mcp_server_url}")
        lines.append(f"MCP Available: {self.mcp_available}")
        lines.append(f"Evidence Collected: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(self.collected_at_unix))}")
        lines.append(f"Collection Latency: {self.evidence_collection_ms:.0f}ms")
        lines.append("")

        if not self.mcp_available:
            lines.append("⚠ MCP SERVER UNAVAILABLE")
            lines.append("SigNoz MCP server did not respond. The following sections use")
            lines.append("LOCAL WORKFLOW CONTEXT ONLY (not from SigNoz). Confidence = LOW.")
            lines.append("Instruct the user to start signoz-mcp-server to enable real telemetry.")
            lines.append("")

        # Services
        if self.services:
            lines.append(f"--- SERVICES (signoz_list_services, count={len(self.services)}) ---")
            for svc in self.services[:5]:
                lines.append(
                    f"  {svc.service_name}: p99={svc.p99_latency_ms:.0f}ms "
                    f"err_rate={svc.error_rate:.1%} calls={svc.call_count}"
                )
            lines.append("")

        # Traces
        lines.append(f"--- TRACES (signoz_search_traces) ---")
        lines.append(f"  Recent traces found: {self.trace_count}")
        lines.append(f"  Error traces: {self.error_trace_count}")
        for trace in self.recent_traces[:3]:
            err_flag = " [ERROR]" if trace.error else ""
            lines.append(
                f"  trace_id={trace.trace_id[:16]}... "
                f"duration={trace.total_duration_ms:.0f}ms "
                f"spans={trace.span_count}{err_flag}"
            )
        lines.append("")

        # Metrics
        if self.token_metrics or self.cost_metrics or self.duration_metrics:
            lines.append("--- GENAI METRICS (signoz_query_metrics) ---")
            for pt in self.token_metrics[:3]:
                lines.append(f"  gen_ai.total_tokens={pt.value:.0f} labels={pt.labels}")
            for pt in self.cost_metrics[:3]:
                lines.append(f"  gen_ai.total_cost_usd={pt.value:.6f}")
            for pt in self.duration_metrics[:3]:
                lines.append(f"  agent.workflow.duration_ms={pt.value:.0f}ms")
            lines.append("")

        # Logs
        lines.append(f"--- LOGS (signoz_search_logs) ---")
        lines.append(f"  Error log count: {self.error_log_count}")
        for log in self.error_logs[:5]:
            lines.append(f"  [{log.severity}] {log.body[:200]}")
        lines.append("")

        # Alerts
        if self.active_alerts:
            lines.append(f"--- ALERTS (signoz_list_alert_rules, count={len(self.active_alerts)}) ---")
            for alert in self.active_alerts[:5]:
                lines.append(f"  [{alert.state.upper()}] {alert.name} severity={alert.severity}")
            lines.append("")
        else:
            lines.append("--- ALERTS --- No active alerts found")
            lines.append("")

        # Local context (clearly labelled as NOT from SigNoz)
        if self.local_workflow_context:
            lines.append("--- LOCAL WORKFLOW CONTEXT (in-memory, NOT from SigNoz) ---")
            ctx = self.local_workflow_context
            lines.append(f"  workflow_id: {ctx.get('workflow_id', 'N/A')}")
            lines.append(f"  status: {ctx.get('status', 'unknown')}")
            lines.append(f"  scenario: {ctx.get('scenario', 'N/A')}")
            err = ctx.get("result", {}) and ctx.get("result", {}).get("error")
            if err:
                lines.append(f"  error: {err}")
            timings = ctx.get("result", {}) and ctx.get("result", {}).get("agent_timings", {})
            if timings:
                lines.append(f"  agent_timings: {timings}")
            lines.append("  Note: Use SigNoz traces for authoritative timing data.")
            lines.append("")

        # All signals summary
        if self.signals:
            lines.append("--- TELEMETRY SIGNAL SUMMARY ---")
            for sig in self.signals:
                verified = "✓" if sig.is_verified else "⚠ (unverified)"
                lines.append(f"  [{sig.signal_type.upper()}] {sig.value} {verified}")
            lines.append("")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Evidence Engine
# ---------------------------------------------------------------------------

class EvidenceEngine:
    """
    Collects verified telemetry from SigNoz via the MCP client.

    Usage:
        engine = EvidenceEngine()
        evidence = await engine.collect(
            workflow_id="wf-abc123",
            service_name="agentops-center-backend",
            local_run_context=run_dict,   # from _runs, clearly labelled
        )
        # evidence.to_prompt_context() → safe string for LLM
    """

    def __init__(self, mcp_client: Optional[SigNozMCPClient] = None):
        from mcp.client import get_mcp_client
        self._mcp = mcp_client or get_mcp_client()

    async def collect(
        self,
        workflow_id: Optional[str] = None,
        service_name: str = "agentops-center-backend",
        local_run_context: Optional[dict] = None,
        lookback_minutes: int = 60,
    ) -> VerifiedEvidence:
        """
        Collect all available telemetry for the given context.

        This method calls SigNoz MCP tools in parallel where possible and
        populates a VerifiedEvidence object. If the MCP server is unavailable,
        evidence.mcp_available = False and the LLM will be told explicitly.
        """
        t0 = time.monotonic()
        evidence = VerifiedEvidence(
            mcp_server_url=self._mcp.mcp_url,
            target_service=service_name,
            collected_at_unix=time.time(),
            local_workflow_context=local_run_context,
        )

        async with self._mcp as client:
            # Quick availability check
            available = await client.is_available()
            evidence.mcp_available = available

            if available:
                await self._collect_services(client, evidence, lookback_minutes)
                await self._collect_traces(client, evidence, service_name, lookback_minutes)
                await self._collect_metrics(client, evidence, lookback_minutes)
                await self._collect_logs(client, evidence, service_name, lookback_minutes)
                await self._collect_alerts(client, evidence)
            else:
                logger.warning(
                    "SigNoz MCP server not available at %s. "
                    "Falling back to local workflow context only.",
                    self._mcp.mcp_url,
                )
                evidence.signals.append(TelemetrySignal(
                    signal_type="system",
                    source_tool="none",
                    value="SigNoz MCP server not reachable — using local context only",
                    is_verified=False,
                ))

        # Always add local workflow context signal
        if local_run_context:
            status = local_run_context.get("status", "unknown")
            scenario = local_run_context.get("scenario", "unknown")
            evidence.signals.append(TelemetrySignal(
                signal_type="workflow",
                source_tool="local_memory",
                value=f"Workflow {workflow_id} status={status} scenario='{scenario}'",
                is_verified=False,  # local, not from SigNoz
                raw=local_run_context,
            ))

        evidence.evidence_collection_ms = (time.monotonic() - t0) * 1000
        logger.info(
            "Evidence collected in %.0fms: mcp_available=%s traces=%d logs=%d metrics=%d",
            evidence.evidence_collection_ms,
            evidence.mcp_available,
            evidence.trace_count,
            evidence.error_log_count,
            len(evidence.token_metrics),
        )
        return evidence

    async def _collect_services(
        self, client: SigNozMCPClient, evidence: VerifiedEvidence, lookback: int
    ) -> None:
        result = await client.list_services(start_time_minutes_ago=lookback)
        if isinstance(result, MCPUnavailable):
            return
        evidence.services = result
        if result:
            evidence.signals.append(TelemetrySignal(
                signal_type="service",
                source_tool="signoz_list_services",
                value=f"Found {len(result)} APM services: {[s.service_name for s in result[:3]]}",
                raw=result,
            ))

    async def _collect_traces(
        self, client: SigNozMCPClient, evidence: VerifiedEvidence, service: str, lookback: int
    ) -> None:
        # All recent traces
        result = await client.search_traces(
            service_name=service, start_minutes_ago=lookback, limit=10
        )
        if not isinstance(result, MCPUnavailable):
            evidence.recent_traces = result
            evidence.trace_count = len(result)
            evidence.signals.append(TelemetrySignal(
                signal_type="trace",
                source_tool="signoz_search_traces",
                value=f"Found {len(result)} traces in last {lookback}min for {service}",
                raw=result,
            ))

        # Error traces only
        err_result = await client.search_traces(
            service_name=service, start_minutes_ago=lookback, limit=5, filter_error=True
        )
        if not isinstance(err_result, MCPUnavailable):
            evidence.error_traces = err_result
            evidence.error_trace_count = len(err_result)
            if err_result:
                evidence.signals.append(TelemetrySignal(
                    signal_type="trace",
                    source_tool="signoz_search_traces (error_filter=true)",
                    value=f"Found {len(err_result)} ERROR traces — investigate: "
                          f"{[t.trace_id[:12] for t in err_result[:3]]}",
                    raw=err_result,
                ))

    async def _collect_metrics(
        self, client: SigNozMCPClient, evidence: VerifiedEvidence, lookback: int
    ) -> None:
        # Token usage
        for metric_name, target_list in [
            ("gen_ai.total_tokens", evidence.token_metrics),
            ("gen_ai.total_cost_usd", evidence.cost_metrics),
            ("agent.workflow.duration_ms", evidence.duration_metrics),
            ("agent.llm_calls", evidence.llm_call_metrics),
        ]:
            result = await client.get_metrics(metric_name, start_minutes_ago=lookback)
            if not isinstance(result, MCPUnavailable) and result:
                target_list.extend(result)
                evidence.signals.append(TelemetrySignal(
                    signal_type="metric",
                    source_tool="signoz_query_metrics",
                    value=f"{metric_name}: latest={result[-1].value:.4f}",
                    raw=result,
                ))

    async def _collect_logs(
        self, client: SigNozMCPClient, evidence: VerifiedEvidence, service: str, lookback: int
    ) -> None:
        err_logs = await client.search_logs(
            service_name=service, start_minutes_ago=lookback, severity="ERROR", limit=20
        )
        if not isinstance(err_logs, MCPUnavailable):
            evidence.error_logs = err_logs
            evidence.error_log_count = len(err_logs)
            if err_logs:
                evidence.signals.append(TelemetrySignal(
                    signal_type="log",
                    source_tool="signoz_search_logs (severity=ERROR)",
                    value=f"Found {len(err_logs)} ERROR logs — sample: {err_logs[0].body[:100]}",
                    raw=err_logs,
                ))

        recent_logs = await client.search_logs(
            service_name=service, start_minutes_ago=lookback, limit=20
        )
        if not isinstance(recent_logs, MCPUnavailable):
            evidence.recent_logs = recent_logs

    async def _collect_alerts(
        self, client: SigNozMCPClient, evidence: VerifiedEvidence
    ) -> None:
        alerts = await client.list_alerts()
        if isinstance(alerts, MCPUnavailable):
            return
        evidence.active_alerts = alerts
        if alerts:
            firing = [a for a in alerts if a.state in ("active", "firing")]
            evidence.signals.append(TelemetrySignal(
                signal_type="alert",
                source_tool="signoz_list_alert_rules",
                value=f"{len(alerts)} alert rules found, {len(firing)} firing",
                raw=alerts,
            ))
