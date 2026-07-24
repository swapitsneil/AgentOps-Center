"""
OpenTelemetry & SigNoz Observability Module for AgentOps Center.
Imports and exposes tracer, meter, and instrumentation setup helpers.
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from instrumentation.setup import setup_telemetry, shutdown_telemetry, instrument_fastapi
from instrumentation.agent_spans import llm_span, tool_span, redis_span, db_span, third_party_api_span

__all__ = [
    "setup_telemetry",
    "shutdown_telemetry",
    "instrument_fastapi",
    "llm_span",
    "tool_span",
    "redis_span",
    "db_span",
    "third_party_api_span",
]
