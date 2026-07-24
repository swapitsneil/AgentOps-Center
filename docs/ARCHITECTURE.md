# AgentOps Center Architecture Specification

AgentOps Center is an AI Operations Center designed to observe, explain, debug, and optimize multi-agent AI systems using OpenTelemetry and SigNoz.

```
                    ┌─────────────────────────┐
                    │ Next.js 15 Frontend UI  │
                    │   (Port 3000 / Next)    │
                    └────────────┬────────────┘
                                 │ REST / SSE
                                 ▼
                    ┌─────────────────────────┐
                    │ FastAPI Python Backend  │
                    │       (Port 8000)       │
                    └────────────┬────────────┘
                                 │ OTLP gRPC / HTTP
                                 ▼
                    ┌─────────────────────────┐
                    │  SigNoz OTel Collector  │
                    │       (Port 4317)       │
                    └─────────────────────────┘
```

## Key Components

1. **Multi-Agent LangGraph Engine** (`backend/agents/graph.py`)
   - `monitor_agent`: Detects incident severity and characterizes metrics.
   - `diagnosis_agent`: Performs root cause analysis via log/trace correlation.
   - `fix_agent`: Generates 3-step runbook remediation.
   - `report_agent`: Produces executive postmortems.

2. **OpenTelemetry Instrumentation** (`backend/instrumentation/`)
   - GenAI Semantic Conventions (`gen_ai.system`, `gen_ai.usage.input_tokens`).
   - Redis Spans (`db.system = "redis"`, `cache.hit`).
   - Database Spans (`db.system = "postgresql"`, `db.pool.active_connections`).
   - Third-Party API Spans (`third_party.api.name`, `rate_limit.remaining`).

3. **Root Cause Copilot V3** (`backend/api/copilot.py`)
   - Grounded in SigNoz OpenTelemetry data.
   - Enforces Evidence Before Conclusion & Technology-Specific Component Telemetry Validation.
