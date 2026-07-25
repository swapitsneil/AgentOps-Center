# Agents of SigNoz Hackathon 2026 — Official Hackathon Guide & AI Declaration

> **AI Operations & Multi-Agent Observability Platform powered by OpenTelemetry + SigNoz + MCP**

---

## 🌐 Live Production & Media Links

| Resource | Live Production / Post URL | Host / Platform | Status |
| :--- | :--- | :--- | :--- |
| **AgentOps Center UI** | 🚀 [https://agent-ops-center-kohl.vercel.app](https://agent-ops-center-kohl.vercel.app/) | **Vercel** | 🟢 Live |
| **Backend Service** | ⚡ [https://agentops-center-backend.onrender.com](https://agentops-center-backend.onrender.com) | **Render** | 🟢 Live |
| **SigNoz MCP Bridge** | ⚙️ `http://agentops-signoz-mcp:10000/mcp` | **Render Private Net** | 🟢 Active |
| **API Documentation** | 📖 [https://agentops-center-backend.onrender.com/docs](https://agentops-center-backend.onrender.com/docs) | **Render** | 🟢 Live |
| **Medium Article** | 📝 [Why is my AI agent taking 45 seconds when nothing is even broken?](https://medium.com/@swapnilnicolsondadel/why-is-my-ai-agent-taking-45-seconds-when-nothing-is-even-broken-5308685e5da7) | **Medium** | 🟢 Published |
| **Twitter / X** | 🐦 [@swappingcodes](https://x.com/swappingcodes) | **X / Twitter** | 🟢 Active |
| **LinkedIn** | 💼 [Swapnil Nicolson Dadel](https://www.linkedin.com/in/swapnil-nicolson-dadel/) | **LinkedIn** | 🟢 Active |

---

## 📦 Foundry Deployment & Reproducibility (`casting.yaml`)

Per SigNoz Hackathon requirements, this repository includes both **`casting.yaml`** and **`casting.yaml.lock`** for 1-step Foundry deployment reproduction:

```bash
# Reproduce the full SigNoz + AgentOps Center stack via Foundry:
foundryctl cast -f casting.yaml
```

---

## 🤖 AI Usage Declaration

Per hackathon rules, all AI assistants and tools used during development are declared below:

| Tool / Model | Role / Purpose | Extent of Usage |
| :--- | :--- | :--- |
| **Google Antigravity IDE** | Primary IDE, codebase architecture planning, OTel setup, and component scaffolding | Generated initial project skeleton, Docker stack, and UI boilerplate |
| **Claude Sonnet 4.6** | Code review, instrumentation strategy, and reasoning engine validation | Refactored MCP client payloads and verified telemetry signals |
| **Claude Opus 4.6** | Deep architectural review and root cause confidence scoring logic | Evaluated evidence grading algorithm and system resilience |

---

## 🏗️ What Was Built & Verified

- **FastAPI + LangGraph 4-Agent Workflow**: Monitor → Diagnosis → Fix → Report sequential execution.
- **OpenTelemetry Instrumentation**: Full `gen_ai.*` semantic conventions compliance emitting spans for every LLM token, model latency, and tool invocation.
- **SigNoz MCP Server Integration**: Sidecar query bridge fetching verified trace evidence, log exceptions, and metric samples.
- **Root Cause Copilot**: Evidence-driven reasoning engine with dynamic confidence badges (`🟢 HIGH`, `🟡 MEDIUM`, `🟠 LOW`).
- **Chaos Engineering Engine**: Runtime fault injection testing system resilience across 6 failure modes.
- **Production Cloud Deployment**: Next.js UI deployed to Vercel connected to live FastAPI backend on Render.
