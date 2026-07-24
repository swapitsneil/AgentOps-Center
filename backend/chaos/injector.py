"""
Chaos Engineering Engine for AgentOps Center.
Allows runtime injection of failures to demonstrate SigNoz observability.

Design: A global chaos state dict controls active fault types.
Agents check this before operations — injected faults create error spans
that appear in SigNoz with full context.

Fixed: TOOL_FAILURE and INVALID_OUTPUT now fully implemented.
"""
import asyncio
import random
import time
from enum import Enum
from typing import Dict, Any
from opentelemetry import trace
from opentelemetry.trace import StatusCode


class ChaosMode(str, Enum):
    LLM_TIMEOUT = "llm_timeout"           # Simulates LLM provider timeout
    LLM_ERROR = "llm_error"               # Simulates LLM API error (429, 500)
    TOOL_FAILURE = "tool_failure"          # Simulates tool/function call failure
    SLOW_RESPONSE = "slow_response"        # Adds latency to all operations
    INVALID_OUTPUT = "invalid_output"      # LLM returns malformed JSON/output
    AGENT_CRASH = "agent_crash"           # Agent raises unhandled exception


# Global chaos state — shared across all agents
_chaos_state: Dict[str, Any] = {
    "active": False,
    "modes": {},         # ChaosMode -> intensity (0.0-1.0)
    "total_injected": 0,
    "last_injection": None,
}


def get_chaos_state() -> Dict[str, Any]:
    return dict(_chaos_state)


def enable_chaos(mode: ChaosMode, intensity: float = 0.5) -> None:
    """Enable a chaos mode with given failure rate (0.0 = never, 1.0 = always)."""
    _chaos_state["active"] = True
    _chaos_state["modes"][mode.value] = max(0.0, min(1.0, intensity))


def disable_chaos(mode: ChaosMode | None = None) -> None:
    """Disable a specific mode or all chaos."""
    if mode is None:
        _chaos_state["active"] = False
        _chaos_state["modes"].clear()
    else:
        _chaos_state["modes"].pop(mode.value, None)
        if not _chaos_state["modes"]:
            _chaos_state["active"] = False


def _should_inject(mode: ChaosMode) -> bool:
    """Probabilistic check — returns True if chaos should be injected now."""
    if not _chaos_state["active"]:
        return False
    intensity = _chaos_state["modes"].get(mode.value, 0.0)
    return random.random() < intensity


def _record_injection(span, mode: ChaosMode, agent_name: str, workflow_id: str, error_msg: str) -> None:
    """Record chaos injection on current span and update global counter."""
    span.set_attribute("chaos.mode", mode.value)
    span.set_attribute("chaos.injected", True)
    span.set_attribute("agent.name", agent_name)
    span.set_attribute("agent.workflow_id", workflow_id)
    span.set_status(StatusCode.ERROR, error_msg)
    _chaos_state["total_injected"] += 1
    _chaos_state["last_injection"] = time.time()


async def chaos_check_llm(agent_name: str, workflow_id: str) -> None:
    """
    Call this BEFORE every LLM invocation.
    May raise an exception or add latency based on active chaos modes.
    Records injected failures as OTel error spans.
    """
    tracer = trace.get_tracer("agentops.chaos")

    if _should_inject(ChaosMode.SLOW_RESPONSE):
        delay = random.uniform(2.0, 8.0)
        with tracer.start_as_current_span("chaos.slow_response") as span:
            _record_injection(span, ChaosMode.SLOW_RESPONSE, agent_name, workflow_id,
                              f"Slow response injected: {delay:.1f}s delay")
            span.set_attribute("chaos.delay_seconds", delay)
        await asyncio.sleep(delay)

    if _should_inject(ChaosMode.LLM_TIMEOUT):
        with tracer.start_as_current_span("chaos.llm_timeout") as span:
            _record_injection(span, ChaosMode.LLM_TIMEOUT, agent_name, workflow_id,
                              "LLM timeout (chaos injected)")
        raise TimeoutError(f"[CHAOS] LLM timeout injected for {agent_name}")

    if _should_inject(ChaosMode.LLM_ERROR):
        with tracer.start_as_current_span("chaos.llm_error") as span:
            _record_injection(span, ChaosMode.LLM_ERROR, agent_name, workflow_id,
                              "LLM API error 429 (chaos injected)")
        raise RuntimeError(f"[CHAOS] LLM API error (429 Rate Limited) for {agent_name}")

    if _should_inject(ChaosMode.AGENT_CRASH):
        with tracer.start_as_current_span("chaos.agent_crash") as span:
            _record_injection(span, ChaosMode.AGENT_CRASH, agent_name, workflow_id,
                              "Agent crash (chaos injected)")
        raise RuntimeError(f"[CHAOS] Agent {agent_name} crashed unexpectedly")


def chaos_check_tool(tool_name: str, agent_name: str, workflow_id: str) -> None:
    """
    Call this BEFORE every tool invocation.
    Raises ToolFailureError if TOOL_FAILURE chaos is active.
    Records injected failure as an OTel error span visible in SigNoz.

    FIX: This was previously defined but never called. Now wired into tool_span.
    """
    if not _should_inject(ChaosMode.TOOL_FAILURE):
        return

    tracer = trace.get_tracer("agentops.chaos")
    with tracer.start_as_current_span("chaos.tool_failure") as span:
        _record_injection(span, ChaosMode.TOOL_FAILURE, agent_name, workflow_id,
                          f"Tool '{tool_name}' failure (chaos injected)")
        span.set_attribute("chaos.tool_name", tool_name)

    raise RuntimeError(f"[CHAOS] Tool '{tool_name}' failed (chaos injected for {agent_name})")


def chaos_corrupt_output(output: str, agent_name: str, workflow_id: str) -> str:
    """
    Call this AFTER every LLM response to potentially corrupt the output.
    If INVALID_OUTPUT chaos is active, returns a malformed/corrupted response
    that downstream agents cannot process cleanly.
    Records the injection as an OTel warning span.

    FIX: This was previously defined but never implemented. Corrupts LLM output
    in a deterministic-but-unrealistic way that is detectable in SigNoz traces.
    """
    if not _should_inject(ChaosMode.INVALID_OUTPUT):
        return output

    tracer = trace.get_tracer("agentops.chaos")
    corruption_type = random.choice([
        "truncate", "inject_nulls", "inject_garbage", "empty"
    ])

    with tracer.start_as_current_span("chaos.invalid_output") as span:
        _record_injection(span, ChaosMode.INVALID_OUTPUT, agent_name, workflow_id,
                          f"LLM output corrupted: {corruption_type}")
        span.set_attribute("chaos.corruption_type", corruption_type)
        span.set_attribute("chaos.original_length", len(output))

    if corruption_type == "empty":
        corrupted = "[CHAOS: empty output]"
    elif corruption_type == "truncate":
        cut = max(1, len(output) // 4)
        corrupted = output[:cut] + " [CHAOS: output truncated]"
    elif corruption_type == "inject_nulls":
        corrupted = output[:20] + "\x00\x00\x00 [CHAOS: null bytes injected]"
    else:  # inject_garbage
        corrupted = "CHAOS_CORRUPTED_OUTPUT: {invalid json: <<<>>>}"

    return corrupted
