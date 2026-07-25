# 🔭 AgentOps Center

> **AI Operations Center for Multi-Agent Systems powered by OpenTelemetry, SigNoz & Model Context Protocol (MCP)**

Observe. Debug. Chaos Test. Explain.  
Gain end-to-end visibility into autonomous AI agent workflows using **real telemetry, evidence-backed reasoning, and official SigNoz observability infrastructure**.

<p align="center">

[![Agents of SigNoz Hackathon](https://img.shields.io/badge/Agents%20of%20SigNoz-Hackathon%202026-blue?style=for-the-badge)](https://wemakedevs.org)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![NextJS](https://img.shields.io/badge/Next.js-15-black?style=for-the-badge&logo=next.js)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi)
![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-success?style=for-the-badge)
![OpenTelemetry](https://img.shields.io/badge/OpenTelemetry-Instrumented-orange?style=for-the-badge)
![SigNoz](https://img.shields.io/badge/SigNoz-v0.144.6-purple?style=for-the-badge)
[![Medium Blog](https://img.shields.io/badge/Medium-Technical%20Article-black?style=for-the-badge&logo=medium)](https://medium.com/@swapnilnicolsondadel/why-is-my-ai-agent-taking-45-seconds-when-nothing-is-even-broken-5308685e5da7)
[![Twitter Follow](https://img.shields.io/badge/Twitter-@swappingcodes-1DA1F2?style=for-the-badge&logo=x)](https://x.com/swappingcodes)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0A66C2?style=for-the-badge&logo=linkedin)](https://www.linkedin.com/in/swapnil-nicolson-dadel/)

</p>

---

## 🌐 Live Deployment & Media Links

| Resource | Link / URL | Platform | Status |
| :--- | :--- | :--- | :---: |
| **AgentOps Center UI** | 🚀 [https://agent-ops-center-kohl.vercel.app](https://agent-ops-center-kohl.vercel.app/) | **Vercel** | 🟢 Live |
| **Backend API Service** | ⚡ [https://agentops-center-backend.onrender.com](https://agentops-center-backend.onrender.com) | **Render** | 🟢 Live |
| **Backend API Docs** | 📖 [https://agentops-center-backend.onrender.com/docs](https://agentops-center-backend.onrender.com/docs) | **Render** | 🟢 Live |
| **Medium Article** | 📝 [Read Technical Deep Dive](https://medium.com/@swapnilnicolsondadel/why-is-my-ai-agent-taking-45-seconds-when-nothing-is-even-broken-5308685e5da7) | **Medium** | 🟢 Published |
| **X / Twitter** | 🐦 [@swappingcodes](https://x.com/swappingcodes) | **X** | 🟢 Active |
| **LinkedIn Profile** | 💼 [Swapnil Nicolson Dadel](https://www.linkedin.com/in/swapnil-nicolson-dadel/) | **LinkedIn** | 🟢 Connected |

---

## 💡 Problem Statement

Large Language Model (LLM) applications are rapidly transitioning from single-prompt scripts into **complex multi-agent systems**. Autonomous agents break down tasks, call external APIs, query databases, and pass state between specialized nodes.

However, traditional APM tools were designed for REST APIs and microservices—not non-deterministic AI agent loops. When an AI workflow fails or degrades, engineers struggle to answer critical questions:

- **Which agent node failed or looped indefinitely?**
- **Which external tool or API returned rate limits or errors?**
- **Why did a workflow take 45 seconds when no exception was thrown?**
- **How much money in token cost was consumed by each sub-agent?**
- **Is the Root Cause Copilot providing verified facts or hallucinating?**

Most AI monitoring tools attempt to solve this by storing unverified prompt logs or asking LLMs to guess root causes without real system context.

---

## ✨ The Solution: Telemetry-Backed Agent Operations

**AgentOps Center replaces guesswork with empirical telemetry.**

Every LLM call, agent node transition, tool execution, token count, latency measurement, and runtime exception is instrumented using **OpenTelemetry GenAI Semantic Conventions (`gen_ai.*`)**, exported to **SigNoz ClickHouse (`v0.144.6`)**, and queried by an **Evidence Engine** over the **SigNoz Model Context Protocol (MCP)**.

```
                                  User / UI
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │    Next.js 15 Frontend    │
                        │    (Vercel Production)    │
                        └─────────────┬─────────────┘
                                      │ REST / SSE
                                      ▼
                        ┌───────────────────────────┐
                        │    FastAPI + LangGraph    │
                        │    (Render Production)    │
                        └──────┬─────────────┬──────┘
                               │             │
                    OTLP gRPC  │             │ MCP JSON-RPC
                    (Port 4317)│             │ (Port 18080)
                               ▼             ▼
                    ┌──────────────┐   ┌────────────────────┐
                    │OTel Collector│   │ SigNoz MCP Server  │
                    └──────┬───────┘   └─────────┬──────────┘
                           │                     │
                           ▼                     │
                    ┌──────────────┐             │ HTTP API
                    │ ClickHouse   │             │ (Port 8080)
                    │ (v24.1.2)    │             │
                    └──────┬───────┘             │
                           │                     │
                           ▼                     │
                    ┌────────────────────────────┴─────┐
                    │       SigNoz Query Service       │
                    │            (v0.144.6)            │
                    └──────────────────────────────────┘
```

---

## 🏆 Key Architectural Highlights

### 1. Native OpenTelemetry GenAI Instrumentation
- Full adherence to standard OTel GenAI conventions (`gen_ai.system`, `gen_ai.operation.name`, `gen_ai.request.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `gen_ai.usage.cost_usd`).
- Custom span attributes for agent transitions (`agent.name`, `agent.node`, `agent.workflow_id`, `agent.transition.from`, `agent.transition.to`).
- Rich tool execution spans tracking exact parameters, duration, and error status (`tool.name`, `tool.input`, `tool.output`, `tool.duration_ms`).

### 2. SigNoz MCP Tool Integration
The **Root Cause Copilot** connects to the official `signoz/signoz-mcp-server:latest` via HTTP JSON-RPC 2.0. The Copilot invokes official SigNoz tools:
- `signoz_search_traces`: Fetches exact trace hierarchies and span execution times.
- `signoz_search_logs`: Queries structured error logs and exception stack traces.
- `signoz_query_metrics`: Retrieves aggregated token consumption, cost metrics, and duration histograms.
- `signoz_list_alert_rules`: Evaluates active observability alerts.

### 3. Evidence Engine & Grounded Confidence Badging
The Copilot never exposes raw unverified data or hallucinations to the user. The **Evidence Engine**:
1. Invokes SigNoz MCP tools to gather empirical telemetry.
2. Constructs a `VerifiedEvidence` data structure.
3. Automatically grades the response with evidence badges:
   - **`🟢 HIGH Confidence`**: Verified by 2+ real MCP telemetry signals (traces/logs/metrics).
   - **`🟡 MEDIUM Confidence`**: Partial telemetry signals verified.
   - **`🟠 LOW Confidence`**: Unverified or local fallback context only.

### 4. Chaos Engineering & Incident Injection
Built-in Chaos Engine allows on-demand fault injection during agent workflow runs to evaluate SigNoz observability in real-time:
- **`LLM_TIMEOUT`**: Simulates provider timeout (504).
- **`LLM_ERROR`**: Injects 429 Rate Limiting / 500 Server Errors.
- **`TOOL_FAILURE`**: Forces tool execution failure.
- **`SLOW_RESPONSE`**: Introduces latency delays (2s - 8s).
- **`AGENT_CRASH`**: Injects unhandled agent exceptions.

---

## 🛠️ Technology Stack

| Layer | Technologies Used |
| :--- | :--- |
| **Agent Orchestration** | LangGraph, LangChain, Python 3.11+ |
| **Backend API** | FastAPI, Uvicorn, AsyncIO, SSE (Server-Sent Events) |
| **LLM Router** | LiteLLM (Groq `llama-3.1-8b-instant`, OpenAI `gpt-4o-mini`) |
| **Observability SDK** | OpenTelemetry Python SDK, OpenInference LangChain Instrumentor |
| **Telemetry Pipeline** | SigNoz OTel Collector `v0.144.6`, ClickHouse `24.1.2-alpine` |
| **Query Engine** | SigNoz Query Service `v0.144.6` |
| **Protocol Bridge** | SigNoz MCP Server `v0.9.0` (Model Context Protocol HTTP transport) |
| **Frontend UI** | Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS, Lucide Icons |
| **Deployment** | SigNoz Foundry (`casting.yaml`), Docker Compose, Vercel, Render |

---

## 📁 Repository Structure

```text
.
├── backend/
│   ├── agents/
│   │   └── graph.py          # LangGraph Multi-Agent StateGraph (Monitor, Diagnosis, Fix, Report)
│   ├── api/
│   │   ├── copilot.py        # Copilot SSE streaming endpoints (/api/copilot/ask)
│   │   ├── runs.py           # Workflow execution endpoints (/api/runs/trigger)
│   │   └── metrics.py        # Telemetry metrics endpoints
│   ├── chaos/
│   │   └── injector.py       # Chaos Engineering fault injection engine
│   ├── copilot/
│   │   ├── evidence_engine.py# Evidence Engine (gathers & structures MCP telemetry)
│   │   └── reasoning.py      # LLM reasoning engine & confidence grading logic
│   ├── instrumentation/
│   │   ├── setup.py          # OTel TracerProvider & MeterProvider initialization
│   │   ├── agent_spans.py    # OTel GenAI semantic convention context managers
│   │   └── cost_tracker.py   # Token usage counter & cost calculation
│   ├── mcp/
│   │   └── client.py         # SigNoz MCP HTTP JSON-RPC 2.0 Client
│   ├── Dockerfile            # Container definition for FastAPI backend
│   └── main.py               # FastAPI application entrypoint
├── frontend/
│   ├── src/
│   │   ├── app/              # Next.js 15 App Router pages (Dashboard, Copilot, Chaos, Timeline)
│   │   └── components/       # UI Components & Live Telemetry Viewers
│   └── Dockerfile            # Container definition for Next.js frontend
├── otel-collector/
│   └── config.yaml           # OTel Collector pipeline configuration (OTLP gRPC -> ClickHouse)
├── scratch/
│   └── smoke_tests.py        # End-to-end automated verification suite
├── casting.yaml              # Official SigNoz Foundry deployment manifest
├── casting.yaml.lock         # Foundry lockfile
├── docker-compose.yml        # Full 9-container local stack definition
├── requirements.txt          # Python dependencies
└── README.md                 # Project documentation
```

---

## 🚀 Quickstart & Local Development

### Prerequisites
- **Docker Desktop** (with Docker Compose v2+)
- **Python 3.11+**
- **Node.js 18+** (optional, for local frontend development)

### 1. Clone the Repository
```bash
git clone https://github.com/swapitsneil/AgentOps-Center.git
cd AgentOps-Center
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Provide at least one LLM provider API key in `.env`:
```env
GROQ_API_KEY=your_groq_api_key_here
# OR
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. Start the Complete Docker Stack
Start all 9 containers (ClickHouse, Zookeeper, OTel Collector, Query Service, Schema Migrator, Frontend UI, Backend API, SigNoz MCP Server, SigNoz UI):
```bash
docker compose up -d
```

### 4. Verify Container Health
```bash
docker compose ps
```
All services should be in state `running` or `healthy`:
- **AgentOps Center UI**: `http://localhost:3000`
- **Backend API**: `http://localhost:8000`
- **SigNoz UI**: `http://localhost:8080`
- **SigNoz MCP Server**: `http://localhost:18080/mcp`
- **ClickHouse HTTP**: `http://localhost:8123`

---

## 🚢 SigNoz Foundry Deployment

AgentOps Center includes an official SigNoz Foundry manifest (`casting.yaml`) for 1-step deployment:

```yaml
apiVersion: v1alpha1
metadata:
  name: agentops-center
  version: "0.1.0"
spec:
  deployment:
    mode: docker
    flavor: compose
    composeFile: ./docker-compose.yml
```

To deploy via Foundry:
```bash
foundryctl cast -f casting.yaml
```

---

## 🧪 Running Automated Smoke Tests

Verify end-to-end telemetry flow (Workflow execution ➔ OTel export ➔ ClickHouse persistence ➔ MCP retrieval ➔ Copilot reasoning with HIGH confidence):

```bash
python scratch/smoke_tests.py
```

Expected output:
```text
=======================================================
SMOKE TEST SUMMARY RESULTS
=======================================================
Run #1: PASSED (wf-958c2184 | Spans: 2340 | Confidence: HIGH)
Run #2: PASSED (wf-5dd5034a | Spans: 2915 | Confidence: HIGH)
Run #3: PASSED (wf-064a9377 | Spans: 3559 | Confidence: HIGH)

ALL 3 SMOKE TEST RUNS PASSED CLEANLY!
```

---

## 📸 Interface Preview & Screenshots

### Command Center Dashboard
Overview of active workflows, total token consumption, estimated USD cost, and agent execution graph:
![Command Center](images/command_center.png)

### Root Cause Copilot
Real-time SSE streaming copilot displaying verified SigNoz trace evidence and `🟢 HIGH Confidence` badges:
![Root Cause Copilot](images/root_cause_copilot.png)

### Agent Timeline & Span Hierarchy
Detailed trace span visualization showing agent transition flow and sub-span durations:
![Agent Timeline](images/agent_timeline.png)

### Chaos Engineering Control Plane
Runtime fault injection interface for testing observability under simulated failures:
![Chaos Engine](images/chaos_engine.png)

### Cost & Token Intelligence
Granular breakdown of input/output token usage and USD cost across monitor, diagnosis, fix, and report agents:
![Cost Intelligence](images/cost_intelligence.png)

---

## 📄 License & Acknowledgements

This project is open-source under the [MIT License](LICENSE).

Special thanks to the **SigNoz Team** for building world-class open-source observability infrastructure and organizing the **Agents of SigNoz Hackathon 2026**.
