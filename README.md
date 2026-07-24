# AgentOps Center 🔭

> **The AI Operations Center for Multi-Agent Systems**
> Observe, debug, and improve your AI agents with OpenTelemetry + SigNoz.

[![Built for Agents of SigNoz Hackathon 2026](https://img.shields.io/badge/Agents%20of%20SigNoz-Hackathon%202026-blue?style=flat-square)](https://wemakedevs.org)
[![OpenTelemetry](https://img.shields.io/badge/OpenTelemetry-Instrumented-orange?style=flat-square)](https://opentelemetry.io)
[![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-green?style=flat-square)](https://langchain-ai.github.io/langgraph/)

---

## 🎯 What It Does

AgentOps Center is a **production-grade observability platform for multi-agent AI systems**. It instruments every LLM call, tool invocation, agent transition, and error with OpenTelemetry — sending full telemetry to SigNoz for real-time monitoring, cost tracking, and AI-powered root cause analysis.

**The problem:** AI agents are black boxes. When they fail, you don't know *why*.

**The solution:** Treat AI agents like production services. Instrument everything. Observe everything.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AgentOps Center                          │
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  Next.js 15  │    │   FastAPI    │    │   LangGraph  │  │
│  │  Command     │◄──►│   + Python   │◄──►│  4-Agent     │  │
│  │  Center UI   │    │   Backend    │    │  Workflow     │  │
│  └──────────────┘    └──────┬───────┘    └──────────────┘  │
│                             │ OTLP gRPC                     │
│                    ┌────────▼────────┐                      │
│                    │  OTel Collector │                      │
│                    └────────┬────────┘                      │
│                             │                               │
│                    ┌────────▼────────┐                      │
│                    │    SigNoz       │                      │
│                    │  (self-hosted)  │                      │
│                    │  ClickHouse     │                      │
│                    └─────────────────┘                      │
└─────────────────────────────────────────────────────────────┘
```

---

## ✨ Features

| Feature | Description |
|---|---|
| 🤖 **4-Agent Workflow** | Monitor → Diagnosis → Fix → Report (LangGraph) |
| 📡 **Deep OTel Instrumentation** | Every LLM call, tool, transition = OTel span |
| 📊 **Agent Timeline** | Gantt-style execution replay per workflow |
| 💰 **Cost Intelligence** | Real-time token/cost tracking per agent |
| 🔥 **Chaos Engineering** | One-click failure injection (6 fault types) |
| 🤖 **Root Cause Copilot** | LLM-powered RCA with trace context |
| 🧪 **GenAI Semantic Conventions** | Full `gen_ai.*` attribute compliance |

---

## 🚀 Quick Start

### Prerequisites
- Docker + Docker Compose (with at least 6GB RAM)
- A Groq API key (free at [console.groq.com](https://console.groq.com)) OR OpenAI API key

### 1. Clone & Configure

```bash
git clone https://github.com/your-repo/agentops-center
cd agentops-center

# Configure your API keys
cp .env.example .env
# Edit .env: add GROQ_API_KEY or OPENAI_API_KEY
```

### 2. Start Everything

```bash
docker compose up -d
```

Wait ~60 seconds for SigNoz to initialize.

### 3. Open the Apps

| Service | URL |
|---|---|
| **AgentOps Center** | http://localhost:3000 |
| **SigNoz UI** | http://localhost:8080 |
| **Backend API Docs** | http://localhost:8000/docs |

### 4. Run Your First Workflow

1. Open http://localhost:3000
2. Click **"Trigger Incident Response"**
3. Watch 4 agents execute in real-time
4. Open SigNoz → Traces to see full instrumentation

---

## 🔬 OTel Instrumentation Details

Every operation emits spans with [GenAI Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/):

```python
# Example span attributes on each LLM call:
{
    "gen_ai.system": "groq",
    "gen_ai.operation.name": "chat",
    "gen_ai.request.model": "llama-3.1-8b-instant",
    "gen_ai.usage.input_tokens": 142,
    "gen_ai.usage.output_tokens": 89,
    "gen_ai.usage.cost_usd": 0.00000710,
    "agent.name": "diagnosis_agent",
    "agent.workflow_id": "wf-abc123",
    "agent.node": "diagnosis",
}
```

**What's instrumented:**
- ✅ Every LLM invocation (tokens, cost, latency)
- ✅ Every tool/function call
- ✅ Every agent-to-agent transition (span events)
- ✅ Every chaos-injected failure (error spans)
- ✅ FastAPI request traces
- ✅ HTTP client calls
- ✅ Workflow-level spans with aggregated metrics

---

## 🔥 Chaos Engineering

Enable failure injection to see SigNoz detect issues in real-time:

1. Go to **Chaos Engineering** tab
2. Enable `LLM Timeout` at 70% intensity
3. Trigger a workflow
4. Watch error spans appear in SigNoz within seconds

Available fault types:
- `LLM_TIMEOUT` — provider connection drops
- `LLM_ERROR` — 429 rate limit simulation
- `TOOL_FAILURE` — tool/function call failures
- `SLOW_RESPONSE` — 2-8s latency injection
- `INVALID_OUTPUT` — malformed LLM responses
- `AGENT_CRASH` — unhandled exception

---

## 🧠 Root Cause Copilot

Ask natural language questions about your traces:

> "Why did the last workflow fail?"
> "Which agent is causing the most failures?"
> "Generate a postmortem for workflow wf-abc123"

The copilot fetches trace context from your recent runs and uses an LLM to provide actionable root cause analysis.

---

## 📁 Project Structure

```
agentops-center/
├── docker-compose.yml          # Full stack orchestration
├── .env.example                # Configuration template
├── backend/                    # FastAPI + LangGraph
│   ├── main.py                 # App entry point
│   ├── agents/graph.py         # LangGraph 4-agent workflow
│   ├── instrumentation/        # OTel setup + span helpers
│   ├── chaos/injector.py       # Failure injection engine
│   └── api/                    # REST endpoints
├── frontend/                   # Next.js 15
│   └── src/
│       ├── app/                # Pages
│       └── components/         # UI components
├── otel-collector/config.yaml  # OTel Collector config
└── clickhouse/                 # SigNoz storage config
```

---

## 🛠️ Local Development (without Docker)

```bash
# Backend
cd backend
pip install -e .
# Set env vars or copy .env
uvicorn main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

---

## 📊 SigNoz Dashboards

After running workflows, explore in SigNoz:
- **Traces** → Search `service.name = agentops-center-backend`
- **Metrics** → `gen_ai.total_tokens`, `gen_ai.total_cost_usd`
- **Logs** → Structured logs with trace correlation

---

## 🤖 AI Usage Declaration

This project was built with AI assistance (Gemini/Claude) for code generation and architecture review. All AI usage is declared in [HACKATHON_NOTES.md](./HACKATHON_NOTES.md) per hackathon requirements.

---

## 📝 License

MIT — Built for the Agents of SigNoz Hackathon 2026
