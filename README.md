# 🔭 AgentOps Center

> **AI Operations Center for Multi-Agent Systems powered by OpenTelemetry, SigNoz & Model Context Protocol (MCP)**

Observe. Debug. Chaos Test. Explain.  
Gain end-to-end visibility into your AI agents using **real telemetry**, not guesses.

<p align="center">

[![Agents of SigNoz Hackathon](https://img.shields.io/badge/Agents%20of%20SigNoz-Hackathon%202026-blue?style=for-the-badge)](https://wemakedevs.org)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![NextJS](https://img.shields.io/badge/Next.js-15-black?style=for-the-badge&logo=next.js)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi)
![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-success?style=for-the-badge)
![OpenTelemetry](https://img.shields.io/badge/OpenTelemetry-Instrumented-orange?style=for-the-badge)
![SigNoz](https://img.shields.io/badge/SigNoz-Observability-purple?style=for-the-badge)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker)

</p>

---

# Why AgentOps Center?

Large Language Model applications are rapidly evolving into **multi-agent systems**.

Unfortunately...

Traditional observability platforms were built for APIs and microservices—not autonomous AI agents.

When an AI workflow fails, engineers often struggle to answer critical questions:

- Which agent failed?
- Which tool caused the issue?
- How much did the failed execution cost?
- Which prompt produced the incorrect response?
- Where is the evidence proving the diagnosis?

Most AI debugging tools rely on assumptions.

**AgentOps Center replaces assumptions with telemetry.**

Every LLM request, tool invocation, workflow transition, latency spike, token usage, and runtime error is instrumented using **OpenTelemetry**, stored inside **SigNoz**, and queried through the **SigNoz Model Context Protocol (MCP)** to produce evidence-backed Root Cause Analysis.

---

# Why This Project?

AgentOps Center demonstrates what modern AI operations should look like.

Instead of treating AI agents like black boxes, it treats them exactly like distributed cloud services.

Every decision becomes observable.

Every failure becomes traceable.

Every diagnosis is backed by real telemetry.

---

# Architecture

```

                            User

                               │

                               ▼

┌─────────────────────────────────────────────────────┐
│                  Next.js Dashboard                  │
│                                                     │
│ Command Center • Timeline • Copilot • Chaos Engine │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│                 FastAPI Backend                     │
│                                                     │
│ Workflow Engine                                     │
│ OpenTelemetry Instrumentation                       │
│ REST API                                            │
│ MCP Client                                          │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼

             LangGraph Multi-Agent Workflow

     Monitor Agent
             │
             ▼
     Diagnosis Agent
             │
             ▼
        Fix Agent
             │
             ▼
      Report Agent

             │
             ▼

      OpenTelemetry Collector (OTLP)

             │
             ▼

          SigNoz Platform

     Traces
     Metrics
     Logs

             │
             ▼

     SigNoz MCP Server (JSON-RPC)

             │
             ▼

     Root Cause Copilot

```

---

# End-to-End Execution Flow

```text
Incident Trigger
        │
        ▼
LangGraph executes 4-agent workflow
        │
        ▼
Every agent emits OpenTelemetry spans
        │
        ▼
OTLP Collector exports telemetry
        │
        ▼
SigNoz stores traces, metrics & logs
        │
        ▼
Copilot queries SigNoz MCP
        │
        ▼
Evidence Engine verifies telemetry
        │
        ▼
AI generates Root Cause Analysis
        │
        ▼
Confidence Score assigned
(HIGH / MEDIUM / LOW)
```

---

# Core Features

## Multi-Agent Incident Response

- 4-agent LangGraph workflow
- Sequential orchestration
- Workflow replay
- Agent state transitions
- Live execution tracking

---

## OpenTelemetry Native

Every execution automatically generates:

- LLM spans
- Tool spans
- Agent spans
- Workflow spans
- Cost metrics
- Token metrics
- Error events

Using official **GenAI Semantic Conventions**.

---

## Root Cause Copilot

Unlike traditional AI assistants...

The Copilot **does not hallucinate** telemetry.

Instead it:

- Connects to SigNoz MCP
- Queries traces
- Retrieves metrics
- Searches logs
- Builds verified evidence
- Assigns confidence levels

Every diagnosis is backed by observability data.

---

## Chaos Engineering

Inject failures into running AI workflows.

Supported scenarios include:

- LLM Timeout
- Tool Failure
- Slow Response
- Invalid Output
- Agent Crash
- LLM Exception

Observe how failures propagate through traces.

---

## Cost Intelligence

Track:

- Input Tokens
- Output Tokens
- USD Cost
- Latency
- Cost Per Agent
- Cost Per Workflow
- Total Runtime

---

# Why SigNoz?

SigNoz is the observability backbone of AgentOps Center.

Instead of relying on locally cached context, the platform retrieves live telemetry using the **SigNoz MCP Server**.

The Copilot queries:

- Distributed traces
- Metrics
- Logs
- Services
- Time-series data

Every recommendation references actual observability evidence.

---

# Application Screenshots

## Command Center

Real-time monitoring dashboard displaying active workflows, latency, AI cost, agent status, and operational metrics.

![Command Center](images/command_center.png)

---

## Agent Timeline

Replay every workflow execution with Gantt-style visualization across all agents.

![Timeline](images/agent_timeline.png)

---

## Root Cause Copilot

Evidence-backed AI assistant powered by SigNoz MCP.

![Copilot](images/root_cause_copilot.png)

---

## Cost Intelligence

Monitor token usage and LLM cost in real time.

![Cost](images/cost_intelligence.png)

---

## Chaos Engineering

Inject production-style failures with a single click.

![Chaos](images/chaos_engine.png)

---

# Tech Stack

| Layer | Technologies |
|---------|--------------|
| Frontend | Next.js 15, React, Tailwind CSS |
| Backend | FastAPI, Python |
| AI Orchestration | LangGraph |
| Observability | OpenTelemetry |
| Telemetry Storage | SigNoz + ClickHouse |
| AI Diagnostics | SigNoz MCP |
| Containerization | Docker Compose |
| Database | ClickHouse |
| Collector | OpenTelemetry Collector |

---

# Repository Structure

```text
AgentOps-Center/

├── backend/
│   ├── agents/
│   ├── copilot/
│   ├── instrumentation/
│   ├── chaos/
│   ├── mcp/
│   └── main.py
│
├── frontend/
│
├── clickhouse/
│
├── otel-collector/
│
├── images/
│
├── docs/
│
├── docker-compose.yml
│
└── README.md
```

---

# Quick Start

## Prerequisites

- Docker
- Docker Compose
- Python 3.11+
- Groq/OpenAI/OpenRouter API Key

```bash
git clone https://github.com/swapitsneil/AgentOps-Center.git

cd AgentOps-Center

cp .env.example .env
```

Edit `.env`

```env
GROQ_API_KEY=your_api_key
```

Start everything:

```bash
docker compose up -d
```

Open:

| Service | URL |
|----------|-----|
| AgentOps Center | http://localhost:3000 |
| SigNoz | http://localhost:8080 |
| FastAPI Docs | http://localhost:8000/docs |
| MCP | http://localhost:18080/mcp |

---
