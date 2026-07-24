"""
Helper utilities for creating rich OTel spans following
OpenTelemetry GenAI Semantic Conventions (gen_ai.*) and component-specific conventions (db.*, cache.*, third_party.*).
"""
import time
from contextlib import contextmanager
from typing import Any, Generator, Optional
from opentelemetry import trace
from opentelemetry.trace import Span, StatusCode

tracer = trace.get_tracer("agentops.spans")

# GenAI Semantic Convention keys
GEN_AI_SYSTEM = "gen_ai.system"
GEN_AI_OPERATION = "gen_ai.operation.name"
GEN_AI_MODEL = "gen_ai.request.model"
GEN_AI_INPUT_TOKENS = "gen_ai.usage.input_tokens"
GEN_AI_OUTPUT_TOKENS = "gen_ai.usage.output_tokens"
GEN_AI_COST = "gen_ai.usage.cost_usd"
GEN_AI_PROMPT = "gen_ai.prompt"
GEN_AI_COMPLETION = "gen_ai.completion"

# Agent-specific keys
AGENT_NAME = "agent.name"
AGENT_NODE = "agent.node"
AGENT_WORKFLOW_ID = "agent.workflow_id"
AGENT_FROM = "agent.transition.from"
AGENT_TO = "agent.transition.to"

# Tool call keys
TOOL_NAME = "tool.name"
TOOL_INPUT = "tool.input"
TOOL_OUTPUT = "tool.output"
TOOL_SUCCESS = "tool.success"
TOOL_DURATION_MS = "tool.duration_ms"


def _detect_provider(model: str) -> str:
    """
    Auto-detect the LLM provider from the model name prefix.
    Follows OpenTelemetry GenAI semantic conventions for gen_ai.system.
    Recognized values: 'openai', 'anthropic', 'groq', 'google_vertexai',
    'openrouter', 'cohere', 'mistral_ai'.
    """
    m = model.lower()
    if m.startswith("groq/"):
        return "groq"
    if m.startswith("openai/") or m.startswith("gpt-") or m.startswith("o1") or m.startswith("o3"):
        return "openai"
    if m.startswith("anthropic/") or m.startswith("claude"):
        return "anthropic"
    if m.startswith("google/") or m.startswith("gemini"):
        return "google_vertexai"
    if m.startswith("openrouter/"):
        return "openrouter"
    if m.startswith("cohere/") or m.startswith("command"):
        return "cohere"
    if m.startswith("mistral/") or m.startswith("mixtral"):
        return "mistral_ai"
    # Default for unknown providers — use the prefix before "/" if present
    if "/" in m:
        return m.split("/")[0]
    return "unknown"


@contextmanager
def llm_span(
    agent_name: str,
    model: str,
    operation: str = "chat",
    workflow_id: str = "",
    system: str | None = None,   # None = auto-detect from model name
    prompt_summary: str = "",
) -> Generator[Span, None, None]:
    """Context manager that wraps an LLM call in a properly attributed span.

    gen_ai.system is auto-detected from the model name prefix if system is None.
    This ensures correct provider attribution in SigNoz traces per the
    OpenTelemetry GenAI semantic conventions.
    """
    detected_system = system if system is not None else _detect_provider(model)
    span_name = f"gen_ai.{operation} {agent_name}"
    with tracer.start_as_current_span(span_name) as span:
        span.set_attribute(GEN_AI_SYSTEM, detected_system)
        span.set_attribute(GEN_AI_OPERATION, operation)
        span.set_attribute(GEN_AI_MODEL, model)
        span.set_attribute(AGENT_NAME, agent_name)
        span.set_attribute(AGENT_WORKFLOW_ID, workflow_id)
        if prompt_summary:
            span.set_attribute(GEN_AI_PROMPT, prompt_summary[:500])
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(StatusCode.ERROR, str(exc))
            raise


def record_llm_usage(
    span: Span,
    input_tokens: int,
    output_tokens: int,
    model: str,
    completion_summary: str = "",
) -> float:
    """Record token usage + calculated cost on the span. Returns cost in USD."""
    PRICING = {
        "llama-3.1-8b-instant": (0.05, 0.08),
        "llama-3.3-70b-versatile": (0.59, 0.79),
        "gpt-4o-mini": (0.15, 0.60),
        "gpt-4o": (2.50, 10.00),
    }
    model_key = model.split("/")[-1]
    inp_price, out_price = PRICING.get(model_key, (0.10, 0.30))
    cost = (input_tokens * inp_price + output_tokens * out_price) / 1_000_000
    
    span.set_attribute(GEN_AI_INPUT_TOKENS, input_tokens)
    span.set_attribute(GEN_AI_OUTPUT_TOKENS, output_tokens)
    span.set_attribute(GEN_AI_COST, round(cost, 8))
    if completion_summary:
        span.set_attribute(GEN_AI_COMPLETION, completion_summary[:500])
    return cost


@contextmanager
def tool_span(
    tool_name: str,
    agent_name: str,
    workflow_id: str = "",
    tool_input: str = "",
) -> Generator[Span, None, None]:
    """Context manager for a tool/function call span.

    Wires into the chaos engine: if TOOL_FAILURE chaos is active,
    chaos_check_tool() will raise before the tool body executes,
    producing an OTel error span visible in SigNoz.
    """
    # Lazy import avoids circular dependency (chaos -> instrumentation -> chaos)
    from chaos.injector import chaos_check_tool  # noqa: PLC0415
    chaos_check_tool(tool_name, agent_name, workflow_id)

    start = time.monotonic()
    with tracer.start_as_current_span(f"tool.{tool_name}") as span:
        span.set_attribute(TOOL_NAME, tool_name)
        span.set_attribute(AGENT_NAME, agent_name)
        span.set_attribute(AGENT_WORKFLOW_ID, workflow_id)
        span.set_attribute(TOOL_INPUT, str(tool_input)[:500])
        span.set_attribute(TOOL_SUCCESS, True)
        try:
            yield span
        except Exception as exc:
            span.set_attribute(TOOL_SUCCESS, False)
            span.record_exception(exc)
            span.set_status(StatusCode.ERROR, str(exc))
            raise
        finally:
            duration_ms = int((time.monotonic() - start) * 1000)
            span.set_attribute(TOOL_DURATION_MS, duration_ms)


@contextmanager
def redis_span(
    operation: str,
    key: str,
    workflow_id: str = "",
    cache_hit: bool = True,
) -> Generator[Span, None, None]:
    """Context manager for Redis cache operations."""
    start = time.monotonic()
    with tracer.start_as_current_span(f"redis.{operation}") as span:
        span.set_attribute("db.system", "redis")
        span.set_attribute("db.operation", operation)
        span.set_attribute("db.redis.key", key)
        span.set_attribute("cache.hit", cache_hit)
        span.set_attribute(AGENT_WORKFLOW_ID, workflow_id)
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(StatusCode.ERROR, str(exc))
            raise
        finally:
            span.set_attribute("redis.latency_ms", int((time.monotonic() - start) * 1000))


@contextmanager
def db_span(
    statement: str,
    workflow_id: str = "",
    active_connections: int = 15,
    max_connections: int = 50,
) -> Generator[Span, None, None]:
    """Context manager for Database SQL operations."""
    start = time.monotonic()
    with tracer.start_as_current_span("db.query") as span:
        span.set_attribute("db.system", "postgresql")
        span.set_attribute("db.statement", statement)
        span.set_attribute("db.pool.active_connections", active_connections)
        span.set_attribute("db.pool.max_connections", max_connections)
        span.set_attribute(AGENT_WORKFLOW_ID, workflow_id)
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(StatusCode.ERROR, str(exc))
            raise
        finally:
            span.set_attribute("db.duration_ms", int((time.monotonic() - start) * 1000))


@contextmanager
def third_party_api_span(
    api_name: str,
    endpoint: str,
    workflow_id: str = "",
    status_code: int = 200,
    rate_limit_remaining: int = 100,
) -> Generator[Span, None, None]:
    """Context manager for Third-Party External API calls."""
    start = time.monotonic()
    with tracer.start_as_current_span(f"third_party.{api_name}") as span:
        span.set_attribute("third_party.api.name", api_name)
        span.set_attribute("http.url", endpoint)
        span.set_attribute("http.status_code", status_code)
        span.set_attribute("rate_limit.remaining", rate_limit_remaining)
        span.set_attribute(AGENT_WORKFLOW_ID, workflow_id)
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(StatusCode.ERROR, str(exc))
            raise
        finally:
            span.set_attribute("http.duration_ms", int((time.monotonic() - start) * 1000))


def record_agent_transition(from_agent: str, to_agent: str, workflow_id: str, reason: str = "") -> None:
    """Emit a span event for agent-to-agent transitions."""
    current_span = trace.get_current_span()
    if current_span.is_recording():
        current_span.add_event(
            "agent.transition",
            attributes={
                AGENT_FROM: from_agent,
                AGENT_TO: to_agent,
                AGENT_WORKFLOW_ID: workflow_id,
                "agent.transition.reason": reason,
            },
        )
