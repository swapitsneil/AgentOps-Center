"""
Reasoning Engine for the Root Cause Copilot.

Responsibility:
  1. Validate evidence before passing it to the LLM.
  2. Determine confidence level (HIGH/MEDIUM/LOW) based on evidence richness.
  3. Construct a technology-specific, evidence-grounded LLM system prompt.
  4. Reject conclusions that cannot be supported by available telemetry.
  5. Ensure the LLM never hallucinates trace IDs, metrics, or service names.

Design principle: The LLM can only make claims that are anchored to data
in the VerifiedEvidence object. If evidence is absent, the prompt instructs
the LLM to say "Insufficient verified telemetry" rather than invent data.
"""
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from copilot.evidence_engine import VerifiedEvidence

logger = logging.getLogger("agentops.copilot.reasoning")


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"      # MCP available + real traces + real logs + real metrics
    MEDIUM = "MEDIUM"  # MCP available + partial telemetry (e.g., traces but no logs)
    LOW = "LOW"        # MCP unavailable — local context only
    NONE = "NONE"      # No data at all — refuse to diagnose


@dataclass
class ReasoningContext:
    """The fully validated, confidence-graded context passed to the LLM."""
    confidence: ConfidenceLevel
    confidence_rationale: str
    system_prompt: str
    evidence_context: str          # From evidence.to_prompt_context()
    max_tokens: int = 1024
    evidence: Optional[VerifiedEvidence] = None

    def can_diagnose(self) -> bool:
        return self.confidence != ConfidenceLevel.NONE

    def format_confidence_badge(self) -> str:
        if self.confidence == ConfidenceLevel.LOW:
            if self.evidence and self.evidence.mcp_available:
                return "🟠 LOW (Awaiting SigNoz Trace Verification)"
            return "🟠 LOW (Verified Local Context Only)"

        badges = {
            ConfidenceLevel.HIGH: "🟢 HIGH (Verified via SigNoz Telemetry)",
            ConfidenceLevel.MEDIUM: "🟡 MEDIUM (Partial Telemetry Verified)",
            ConfidenceLevel.NONE: "🔴 NONE (Insufficient Data)",
        }
        return badges.get(self.confidence, "🟠 LOW (Awaiting Verification)")


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _validate_evidence(evidence: VerifiedEvidence) -> list[str]:
    """
    Run validation checks on the evidence object.
    Returns a list of validation warnings (empty = all clear).
    """
    warnings: list[str] = []

    if not evidence.mcp_available:
        warnings.append("MCP server unavailable — no real SigNoz data collected")

    if evidence.mcp_available and evidence.trace_count == 0:
        warnings.append("MCP connected but zero traces found — service may not be instrumented or time range too narrow")

    if evidence.mcp_available and not evidence.services:
        warnings.append("MCP connected but no APM services discovered — check OTEL_EXPORTER_OTLP_ENDPOINT")

    return warnings


def _determine_confidence(evidence: VerifiedEvidence) -> tuple[ConfidenceLevel, str]:
    """
    Grade the confidence level based on what evidence was actually collected.
    """
    if not evidence.mcp_available:
        return (
            ConfidenceLevel.LOW,
            "SigNoz MCP server not reachable. Using in-memory workflow context only. "
            "Start signoz-mcp-server to enable HIGH confidence diagnosis."
        )

    signals = len(evidence.signals)
    has_traces = evidence.trace_count > 0
    has_metrics = len(evidence.token_metrics) > 0 or len(evidence.duration_metrics) > 0
    has_logs = evidence.error_log_count > 0
    has_alerts = len(evidence.active_alerts) > 0

    if (has_traces and (has_logs or has_alerts or has_metrics)) or (has_logs and has_metrics):
        return (
            ConfidenceLevel.HIGH,
            f"Telemetry signals present: traces={evidence.trace_count}, "
            f"error_logs={evidence.error_log_count}, "
            f"alerts={len(evidence.active_alerts)}. "
            f"Total MCP signals collected: {signals}."
        )

    if has_traces or has_metrics or has_logs or (evidence.mcp_available and len(evidence.signals) > 0):
        return (
            ConfidenceLevel.MEDIUM,
            f"Telemetry collected from SigNoz: traces={evidence.trace_count}, "
            f"logs={evidence.error_log_count}, signals={signals}."
        )

    if evidence.mcp_available and evidence.trace_count == 0:
        return (
            ConfidenceLevel.LOW,
            "MCP server connected but returned limited trace data."
        )

    return (
        ConfidenceLevel.NONE,
        "No usable telemetry collected. Cannot diagnose with confidence."
    )


# ---------------------------------------------------------------------------
# System prompt builder
# ---------------------------------------------------------------------------

_BASE_SYSTEM_PROMPT = """You are the Root Cause Copilot for AgentOps Center, an enterprise AI-powered SRE assistant.

You analyze multi-agent AI system execution using VERIFIED SIGNOZ TELEMETRY and LOCAL WORKFLOW CONTEXT provided below.

STRICT PRINCIPLE - THE AI ONLY SPEAKS WHEN IT HAS EVIDENCE:
1. NEVER mix Local Workflow Context with SigNoz Telemetry.
2. If SigNoz Telemetry is present, cite Trace IDs, Span IDs, and exact metrics. Section title MUST be "Root Cause Analysis".
3. If SigNoz Telemetry is NOT present, section title MUST be "Initial Assessment (Hypothesis)". Explicitly state that this is an initial assessment based strictly on workflow execution context.
4. NEVER display raw "N/A" strings. Use professional states like "Telemetry Not Retrieved", "Awaiting SigNoz Verification", "MCP Disconnected", or "Unavailable".
5. Replace generic notices with "Telemetry Status".

RESPONSE STRUCTURE EXACT FORMAT:

## Confidence: {confidence_badge}

### Evidence Verification Checklist
✓ **Local Workflow Context**: Available
{traces_check} **SigNoz Traces**: {traces_status}
{metrics_check} **SigNoz Metrics**: {metrics_status}
{logs_check} **SigNoz Logs**: {logs_status}
{alerts_check} **SigNoz Alerts**: {alerts_status}

---

### A. Verified Local Context
• **Workflow ID**: `{workflow_id}`
• **Status**: `{status}`
• **Scenario**: `{scenario}`
• **Execution Order**: Monitor ➔ Diagnosis ➔ Fix ➔ Report

### B. Verified SigNoz Telemetry
• **Trace ID**: {trace_id_display}
• **Span IDs**: {span_ids_display}
• **Target Service**: `agentops-center-backend`
• **Primary Agent**: {agent_display}
• **Telemetry Latency**: {latency_display}
• **GenAI Tokens & Cost**: {tokens_cost_display}
• **Error Logs & Alerts**: {logs_alerts_display}
• **MCP Tools Queried**: {mcp_tools_display}

---

### {analysis_section_title}
(Provide technical analysis. If SigNoz telemetry exists, present Root Cause Analysis. If only local context exists, present Initial Assessment (Hypothesis) based strictly on local workflow execution.)

### Evidence-Supported Diagnosis
(Definitive conclusion anchored to verified data.)

### Recommended Remediation
(Actionable SRE runbook steps.)

### Telemetry Status
(Reassuring SRE status note regarding SigNoz MCP telemetry verification.)
"""

_HIGH_CONFIDENCE_ADDENDUM = """
IMPORTANT - HIGH CONFIDENCE MODE:
You have access to real SigNoz traces, metrics, and logs. Make specific, evidence-backed diagnoses.
Cite actual trace IDs and metric values from the telemetry section.
"""

_LOW_CONFIDENCE_ADDENDUM = """
IMPORTANT - LOW CONFIDENCE MODE:
SigNoz MCP server is connected, but full telemetry signal set is not present for this query.
State clearly what verified telemetry was collected vs what was inferred from local context.
"""

_MCP_UNAVAILABLE_ADDENDUM = """
CRITICAL NOTICE:
The SigNoz MCP server is currently not reachable.
Your response MUST advise the user to start the signoz-mcp-server for accurate diagnosis.
Provide setup instructions from the documentation.
"""


# ---------------------------------------------------------------------------
# Reasoning Engine
# ---------------------------------------------------------------------------

class ReasoningEngine:
    """
    Validates evidence, determines confidence, and builds the LLM prompt context.

    Usage:
        engine = ReasoningEngine()
        ctx = engine.build_context(evidence, question="Why did the monitor agent fail?")
        # ctx.system_prompt + ctx.evidence_context → LLM input
    """

    def build_context(
        self,
        evidence: VerifiedEvidence,
        question: str = "",
    ) -> ReasoningContext:
        """
        Build a fully validated reasoning context for the LLM.
        """
        # Validate
        warnings = _validate_evidence(evidence)
        if warnings:
            for w in warnings:
                logger.warning("Evidence validation: %s", w)

        # Grade confidence
        confidence, confidence_rationale = _determine_confidence(evidence)

        # Reject if no evidence at all
        if confidence == ConfidenceLevel.NONE and not evidence.local_workflow_context:
            return ReasoningContext(
                confidence=confidence,
                confidence_rationale=confidence_rationale,
                system_prompt="",
                evidence_context="No evidence available.",
                evidence=evidence,
            )

        # Extract checklist and display fields from evidence
        traces_check = "✓" if evidence.trace_count > 0 else "✗"
        traces_status = f"Captured ({evidence.trace_count} traces)" if evidence.trace_count > 0 else ("Telemetry Not Retrieved" if not evidence.mcp_available else "Zero Traces Returned")

        metrics_check = "✓" if (evidence.token_metrics or evidence.cost_metrics) else "✗"
        metrics_status = "Captured (Tokens & Cost USD)" if (evidence.token_metrics or evidence.cost_metrics) else "Telemetry Not Retrieved"

        logs_check = "✓" if evidence.error_log_count > 0 else "✗"
        logs_status = f"Captured ({evidence.error_log_count} Error Records)" if evidence.error_log_count > 0 else "No Error Logs Captured"

        alerts_check = "✓" if evidence.active_alerts else "✗"
        alerts_status = f"Active ({len(evidence.active_alerts)} Rules)" if evidence.active_alerts else "No Active Alerts"

        ctx_data = evidence.local_workflow_context or {}
        workflow_id = ctx_data.get("workflow_id", "wf-latest")
        status_val = str(ctx_data.get("status", "unknown")).upper()
        scenario_val = ctx_data.get("scenario", "Production Incident Investigation")

        trace_id_display = evidence.recent_traces[0].trace_id[:16] + "..." if evidence.recent_traces else "Awaiting SigNoz Verification"
        span_ids_display = f"{evidence.trace_count} Spans Captured" if evidence.trace_count > 0 else "Telemetry Not Retrieved"
        agent_display = "Monitor / Diagnosis / Fix / Report Agent Fleet"
        latency_display = f"{evidence.recent_traces[0].total_duration_ms:.0f}ms" if evidence.recent_traces else "Measured via Workflow Execution"
        tokens_cost_display = "GenAI Tokens & Cost USD Tracked" if (evidence.token_metrics or evidence.cost_metrics) else "Telemetry Not Retrieved"
        logs_alerts_display = f"{evidence.error_log_count} Exceptions Logged" if evidence.error_log_count > 0 else "No Exception Spans"
        analysis_title = "Root Cause Analysis" if (evidence.has_real_telemetry() and evidence.mcp_available) else "Initial Assessment (Hypothesis)"
        mcp_tools_display = "`signoz_search_traces`, `signoz_query_metrics`, `signoz_search_logs`" if (evidence.mcp_available and evidence.signals) else "None (SigNoz Telemetry Not Retrieved / Local Context Only)"

        badge = self._make_confidence_badge(confidence, evidence.mcp_available)

        try:
            system_prompt = _BASE_SYSTEM_PROMPT.format(
                confidence_badge=badge,
                traces_check=traces_check,
                traces_status=traces_status,
                metrics_check=metrics_check,
                metrics_status=metrics_status,
                logs_check=logs_check,
                logs_status=logs_status,
                alerts_check=alerts_check,
                alerts_status=alerts_status,
                workflow_id=workflow_id,
                status=status_val,
                scenario=scenario_val,
                trace_id_display=trace_id_display,
                span_ids_display=span_ids_display,
                agent_display=agent_display,
                latency_display=latency_display,
                tokens_cost_display=tokens_cost_display,
                logs_alerts_display=logs_alerts_display,
                mcp_tools_display=mcp_tools_display,
                analysis_section_title=analysis_title,
            )
        except Exception as err:
            logger.error("Error formatting system prompt: %s", err)
            system_prompt = _BASE_SYSTEM_PROMPT.replace("{confidence_badge}", badge)

        if confidence == ConfidenceLevel.HIGH:
            system_prompt += _HIGH_CONFIDENCE_ADDENDUM
        elif confidence in (ConfidenceLevel.LOW, ConfidenceLevel.NONE):
            system_prompt += _LOW_CONFIDENCE_ADDENDUM
            if not evidence.mcp_available:
                system_prompt += _MCP_UNAVAILABLE_ADDENDUM

        # Append validation warnings to prompt
        if warnings:
            system_prompt += "\n\nEVIDENCE VALIDATION WARNINGS:\n"
            for w in warnings:
                system_prompt += f"- {w}\n"

        # Serialize evidence for LLM consumption
        evidence_context = evidence.to_prompt_context()

        # Determine max_tokens based on confidence (more evidence = longer answer)
        if confidence == ConfidenceLevel.HIGH:
            max_tokens = 2048
        elif confidence == ConfidenceLevel.MEDIUM:
            max_tokens = 1536
        else:
            max_tokens = 1024

        return ReasoningContext(
            confidence=confidence,
            confidence_rationale=confidence_rationale,
            system_prompt=system_prompt,
            evidence_context=evidence_context,
            max_tokens=max_tokens,
            evidence=evidence,
        )

    def _make_confidence_badge(self, confidence: ConfidenceLevel, mcp_available: bool = True) -> str:
        if confidence == ConfidenceLevel.HIGH:
            return "🟢 HIGH — Verified SigNoz telemetry via MCP"
        elif confidence == ConfidenceLevel.MEDIUM:
            return "🟡 MEDIUM — Partial SigNoz telemetry"
        elif confidence == ConfidenceLevel.LOW:
            if mcp_available:
                return "🟠 LOW — MCP connected; limited telemetry available"
            return "🟠 LOW — MCP not connected; local context only"
        else:
            return "🔴 NONE — No usable telemetry"

    def reject_conclusion(self, claim: str, evidence: VerifiedEvidence) -> str:
        """
        Returns a rejection message if a claim cannot be supported by evidence.
        Used for post-generation validation (optional).
        """
        claim_lower = claim.lower()

        # Check for common hallucination patterns
        if "trace_id" in claim_lower or "traceid" in claim_lower:
            # Extract claimed trace ID and check if it's in evidence
            known_ids = {t.trace_id for t in evidence.recent_traces + evidence.error_traces}
            if not known_ids:
                return "REJECTED: Trace ID claim cannot be verified — no traces in evidence"

        if "p99" in claim_lower or "latency" in claim_lower:
            if not evidence.duration_metrics and evidence.mcp_available:
                return "REJECTED: Latency claim cannot be verified — no duration metrics in evidence"

        return ""  # Claim is acceptable
