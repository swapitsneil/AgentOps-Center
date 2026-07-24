# AgentOps Center 🔭

> **The AI Operations & Multi-Agent Observability Platform powered by OpenTelemetry + SigNoz + MCP**
> Observe, debug, chaos-test, and analyze your multi-agent AI systems with evidence-driven telemetry.

[![Built for Agents of SigNoz Hackathon 2026](https://img.shields.io/badge/Agents%20of%20SigNoz-Hackathon%202026-blue?style=flat-square)](https://wemakedevs.org)
[![OpenTelemetry](https://img.shields.io/badge/OpenTelemetry-Instrumented-orange?style=flat-square)](https://opentelemetry.io)
[![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-green?style=flat-square)](https://langchain-ai.github.io/langgraph/)
[![SigNoz MCP](https://img.shields.io/badge/SigNoz--MCP-Integration-purple?style=flat-square)](https://github.com/SigNoz/signoz-mcp-server)

---

## 📸 Application Screenshots

### 1. Command Center & Incident Response Trigger
> *Real-time observability dashboard displaying active runs, LLM spend, chaos mode state, and agent fleet metrics.*
![Command Center](images/command_center.png)

---

### 2. Agent Timeline & Execution Replay
> *Gantt-style execution replay tracking per-agent latency bars (`Monitor`, `Diagnosis`, `Fix`, `Report`) across multi-agent runs.*
![Agent Timeline](images/agent_timeline.png)

---

### 3. Root Cause Copilot (SigNoz MCP Telemetry Verified)
> *AI Incident Investigator using SigNoz MCP tools to gather verified telemetry signals and grade confidence levels.*
![Root Cause Copilot](images/root_cause_copilot.png)

---

### 4. Cost Intelligence & Token Analytics
> *Real-time GenAI token consumption and cost tracking broken down per agent and per workflow run.*
![Cost Intelligence](images/cost_intelligence.png)

---

### 5. Chaos Engineering Engine
> *One-click runtime fault injection engine for testing SRE resilience and SigNoz telemetry alert generation.*
![Chaos Engineering](images/chaos_engine.png)

---

## 🎯 What It Does

AgentOps Center is a **production-grade observability platform for multi-agent AI systems**. It instruments every LLM call, tool invocation, agent transition, and error with OpenTelemetry — sending full telemetry to SigNoz for real-time monitoring, cost tracking, and AI-powered root cause analysis via the **SigNoz Model Context Protocol (MCP) Server**.

- **The Problem:** AI agents operate as opaque black boxes. When multi-agent loops stall or fail, engineers don't know *which agent* broke or *why*.
- **The Solution:** Treat AI agents like microservices. Instrument every decision, measure latency/tokens, stream OTel telemetry into SigNoz, and query verified traces using SigNoz MCP.

---

## ⚙️ How It Works (End-to-End Architecture)

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                   AgentOps Center                                      │
│                                                                                        │
│  ┌─────────────────────────┐      ┌──────────────────────────┐      ┌───────────────┐ │
│  │   Next.js 15 Frontend   │◄────►│  FastAPI Python Backend  │◄────►│   LangGraph   │ │
│  │   (Command Center UI)   │      │  (Instrumentation & API) │      │ 4-Agent Fleet │ │
│  └─────────────────────────┘      └────────────┬─────────────┘      └───────────────┘ │
│                                                │ OTLP gRPC                            │
│                                       ┌────────▼─────────┐                            │
│                                       │  OTel Collector  │ (Port 4317)                │
│                                       └────────┬─────────┘                            │
│                                                │                                      │
│                                       ┌────────▼─────────┐                            │
│                                       │ ClickHouse /     │                            │
│                                       │ SigNoz Engine    │                            │
│                                       └────────┬─────────┘                            │
│                                                │ HTTP API                             │
│  ┌─────────────────────────┐          ┌────────▼─────────┐                            │
│  │   Root Cause Copilot    │◄─────────┤  SigNoz MCP      │ (JSON-RPC 2.0 /mcp)       │
│  │ (Evidence-Driven RCA)   │  Tools   │  Server Sidecar  │                            │
│  └─────────────────────────┘          └──────────────────┘                            │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Step-by-Step Telemetry Execution Flow:

1. **Workflow Trigger & LangGraph Execution**:
   When an incident workflow is triggered, a 4-agent SRE fleet (**Monitor Agent** → **Diagnosis Agent** → **Fix Agent** → **Report Agent**) executes sequentially using LangGraph.

2. **OpenTelemetry Auto & Manual Instrumentation**:
   - Every LLM invocation emits OpenTelemetry spans following **GenAI Semantic Conventions** (`gen_ai.system`, `gen_ai.request.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `gen_ai.usage.cost_usd`).
   - Every tool call (`log_search`, `metrics_check`) and agent state transition emits structured span events.
   - Spans are pushed asynchronously via OTLP gRPC to `signoz-otel-collector` (port `4317`).

3. **ClickHouse Telemetry Storage**:
   The OpenTelemetry Collector writes spans and metrics into ClickHouse database tables (`signoz_traces.signoz_spans`, `signoz_traces.top_level_operations`, `signoz_metrics.samples_v2`).

4. **SigNoz MCP Server Tool Integration**:
   The `signoz-mcp-server` runs as a sidecar container in HTTP JSON-RPC mode. The backend `EvidenceEngine` queries SigNoz MCP tools:
   - `signoz_list_services` — Discovers active APM services.
   - `signoz_search_traces` — Fetches trace execution durations and error spans.
   - `signoz_query_metrics` — Retrieves GenAI token and cost metrics.
   - `signoz_search_logs` — Finds correlated log exceptions.

5. **Evidence-Driven Root Cause Copilot**:
   The Copilot aggregates verified telemetry signals from SigNoz MCP into a `VerifiedEvidence` context. The reasoning engine grades the confidence badge (`🟢 HIGH`, `🟡 MEDIUM`, `🟠 LOW`) and provides evidence-supported postmortems without hallucinating fake trace IDs.

6. **Chaos Injection Engine**:
   Engineers can inject 6 distinct fault modes (`LLM_TIMEOUT`, `LLM_ERROR`, `TOOL_FAILURE`, `SLOW_RESPONSE`, `INVALID_OUTPUT`, `AGENT_CRASH`) at runtime. Faults emit error spans to SigNoz to test system resilience.

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 🤖 **4-Agent LangGraph Workflow** | Monitor → Diagnosis → Fix → Report sequential incident response |
| 📡 **GenAI OTel Instrumentation** | Native support for `gen_ai.*` semantic conventions |
| 📊 **Agent Timeline** | Replay agent executions with Gantt-style latency visualizations |
| 💰 **Cost & Token Intelligence** | Live USD cost and token analytics per agent |
| 🔥 **Chaos Engineering Engine** | Inject 6 fault types at 0–100% failure rates |
| 🧠 **SigNoz MCP Copilot** | Evidence-based RCA querying SigNoz via MCP JSON-RPC |
| 🐳 **Full Docker Stack** | Single `docker compose up -d` brings up all 8 services |

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose (at least 6GB available RAM)
- Groq API Key ([console.groq.com](https://console.groq.com)) OR OpenAI / OpenRouter API key

### 1. Clone & Configure

```bash
git clone https://github.com/swapitsneil/AgentOps-Center.git
cd AgentOps-Center

# Copy environment template
cp .env.example .env

# Edit .env to add your API key:
# GROQ_API_KEY=gsk_...
```

### 2. Start the Stack

```bash
docker compose up -d
```

### 3. Open Services

| Component | URL | Purpose |
|---|---|---|
| **AgentOps Center UI** | [http://localhost:3000](http://localhost:3000) | Main Command Center Dashboard |
| **SigNoz UI** | [http://localhost:8080](http://localhost:8080) | Native SigNoz Observability UI |
| **Backend API Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) | FastAPI OpenAPI Documentation |
| **SigNoz MCP Server** | [http://localhost:18080/mcp](http://localhost:18080/mcp) | MCP JSON-RPC Endpoint |

---

## 🔬 OTel Attribute Specification

Every LLM call emits spans with standard OpenTelemetry GenAI attributes:

```json
{
  "gen_ai.system": "groq",
  "gen_ai.operation.name": "chat",
  "gen_ai.request.model": "llama-3.1-8b-instant",
  "gen_ai.usage.input_tokens": 142,
  "gen_ai.usage.output_tokens": 89,
  "gen_ai.usage.cost_usd": 0.00000710,
  "agent.name": "diagnosis_agent",
  "agent.workflow_id": "wf-86785cb5",
  "agent.node": "diagnosis"
}
```

---

## 📁 Repository Directory Structure

```
AgentOps-Center/
├── docker-compose.yml          # Multi-container orchestration (8 services)
├── .env.example                # Safe environment template
├── images/                     # UI Screenshot previews
│   ├── command_center.png
│   ├── agent_timeline.png
│   ├── root_cause_copilot.png
│   ├── cost_intelligence.png
│   └── chaos_engine.png
├── backend/                    # FastAPI + LangGraph Engine
│   ├── main.py                 # FastAPI application entry
│   ├── agents/graph.py         # 4-agent LangGraph workflow
│   ├── copilot/                # EvidenceEngine & Copilot reasoning
│   ├── mcp/client.py           # SigNoz MCP JSON-RPC Client
│   ├── instrumentation/        # OpenTelemetry setup & GenAI spans
│   └── chaos/injector.py       # Failure injection engine
├── frontend/                   # Next.js 15 Application
│   └── src/app/               # Command Center, Timeline, Copilot, Chaos pages
├── otel-collector/             # OpenTelemetry Collector pipeline config
├── clickhouse/                 # ClickHouse server configuration XMLs
└── docs/                       # Architecture diagrams and runbooks
```

---

## 🤖 AI Usage Declaration

Per hackathon guidelines, AI assistance (Gemini/Claude) was used for initial boilerplate creation and architectural refactoring. Full declarations are detailed in [HACKATHON_NOTES.md](./HACKATHON_NOTES.md).

---

## 📝 License

MIT — Built for the **Agents of SigNoz Hackathon 2026**
