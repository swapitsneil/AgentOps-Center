# Agents of SigNoz Hackathon 2026 — Official Hackathon Guide & AI Declaration

> **AI Operations & Multi-Agent Observability Platform powered by OpenTelemetry + SigNoz + MCP**

---

## 🌐 Live Production Links

| Component | Live Production URL | Host | Status |
| :--- | :--- | :--- | :--- |
| **AgentOps Center UI** | 🚀 [https://agent-ops-center-kohl.vercel.app](https://agent-ops-center-kohl.vercel.app/) | **Vercel** | 🟢 Live |
| **Backend Service** | ⚡ [https://agentops-center-backend.onrender.com](https://agentops-center-backend.onrender.com) | **Render** | 🟢 Live |
| **API Documentation** | 📖 [https://agentops-center-backend.onrender.com/docs](https://agentops-center-backend.onrender.com/docs) | **Render** | 🟢 Live |
| **Health Monitor** | 🩺 [https://agentops-center-backend.onrender.com/health](https://agentops-center-backend.onrender.com/health) | **Render** | 🟢 Live |

---

## 📦 Foundry Deployment & Reproducibility (`casting.yaml`)

Per SigNoz Hackathon requirements, this repository includes both **`casting.yaml`** and **`casting.yaml.lock`** for 1-step Foundry deployment reproduction:

```bash
# Reproduce the full SigNoz + AgentOps Center stack via Foundry:
foundryctl cast -f casting.yaml
```

---

## 🤖 AI Usage Declaration

Per hackathon rules, all AI tool usage during development is declared below:

| Tool | Purpose | Extent |
|---|---|---|
| Google Gemini (Antigravity) | Architecture planning, code generation, infrastructure config | Generated initial boilerplate, OTel instrumentation, and UI structure |
| Claude 3.5 Sonnet / 4.6 | Code review, instrumentation strategy | Architecture decisions and reasoning engine validation |

---

## 🏗️ What Was Built & Verified

- **FastAPI + LangGraph 4-Agent Workflow**: Monitor → Diagnosis → Fix → Report sequential execution.
- **OpenTelemetry Instrumentation**: Full `gen_ai.*` semantic conventions compliance emitting spans for every LLM token, model latency, and tool invocation.
- **SigNoz MCP Server Integration**: Sidecar query bridge fetching verified trace evidence, log exceptions, and metric samples.
- **Root Cause Copilot**: Evidence-driven reasoning engine with dynamic confidence badges (`🟢 HIGH`, `🟡 MEDIUM`, `🟠 LOW`).
- **Chaos Engineering Engine**: Runtime fault injection testing system resilience across 6 failure modes.
- **Production Cloud Deployment**: Next.js UI deployed to Vercel connected to live FastAPI backend on Render.
