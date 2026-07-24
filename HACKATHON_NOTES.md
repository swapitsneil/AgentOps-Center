# HACKATHON_NOTES.md
# Agents of SigNoz Hackathon 2026 — AI Usage Declaration

> **IMPORTANT:** Per hackathon rules, all AI tool usage must be declared.
> Failure to declare = disqualification risk.

---

## AI Tools Used

| Tool | Purpose | Extent |
|---|---|---|
| Google Gemini (Antigravity) | Architecture planning, code generation, infrastructure config | Significant — generated initial boilerplate and structure |
| Claude Sonnet 4.6 | Code review, instrumentation strategy | Used for thinking-mode architecture decisions |

## What AI Generated

- Initial project skeleton and directory structure
- FastAPI + LangGraph agent scaffolding
- OpenTelemetry instrumentation boilerplate
- Docker Compose configuration
- Next.js 15 frontend component scaffolding
- OTel Collector configuration

## What Was Manually Written / Reviewed

- All agent business logic and prompts
- Chaos injection strategy and implementation
- OTel span attribute selection (GenAI semantic conventions)
- Demo scenario design (DevOps Incident Response)
- Architecture decisions (cut scope to 6 core features)
- Cost tracking formulas (pricing table)

---

## Architecture Decisions Log

### Decision 1: Cut from 12 to 6 features
**Rationale:** Depth > breadth for hackathon judges.
Execution Replay, Hallucination Detection, Compare Runs, Redis were cut.
Better to have 6 excellent features than 12 half-finished ones.

### Decision 2: DevOps Incident Response demo scenario
**Rationale:** Meta-narrative — an agent that diagnoses incidents, itself observed by SigNoz, which is an incident response tool. Judges will appreciate the recursion.

### Decision 3: Self-hosted SigNoz via Docker Compose
**Rationale:** Reproducible demo. Judges can run it locally without cloud accounts.

### Decision 4: LiteLLM + LangChain abstraction
**Rationale:** Provider-agnostic. Demo can use Groq (free/fast) or OpenAI depending on availability.

### Decision 5: OpenInference auto-instrumentation + custom spans
**Rationale:** Auto-instrumentation gives baseline coverage; custom spans add business context (cost, agent transitions) that OpenInference doesn't capture.

---

## OTel Instrumentation Approach

### GenAI Semantic Conventions Used

```
gen_ai.system
gen_ai.operation.name
gen_ai.request.model
gen_ai.usage.input_tokens
gen_ai.usage.output_tokens
gen_ai.usage.cost_usd          # Custom extension
agent.name                     # Custom
agent.workflow_id              # Custom
agent.node                     # Custom
agent.transition.from          # Custom
agent.transition.to            # Custom
tool.name                      # Custom
tool.duration_ms               # Custom
chaos.mode                     # Custom
chaos.injected                 # Custom
```

### What Each Span Captures

| Span | Attributes |
|---|---|
| `workflow.incident_response` | workflow.id, scenario, agents, status, duration |
| `agent.<name>` | agent.name, workflow_id, node, duration_ms |
| `gen_ai.chat <agent>` | full GenAI semconv + cost_usd |
| `tool.<name>` | tool.name, input, output, success, duration_ms |
| `chaos.*` | chaos.mode, injected=true, error status |

---

## Demo Script (5 minutes)

```
00:00 - Open AgentOps Center (http://localhost:3000)
        Show Command Center — live system status
        
00:30 - Trigger Incident Response workflow
        → 4 agents start executing
        → Watch Timeline update live
        
01:30 - Open Agent Timeline
        → Click workflow to expand Gantt chart
        → Drill into each agent's output
        → Note cost counter
        
02:00 - Open SigNoz (http://localhost:8080)
        → Show traces for the workflow
        → Expand individual spans
        → Show gen_ai.* attributes
        
02:30 - "Let's break something"
        → Open Chaos Engineering tab
        → Enable LLM_TIMEOUT at 70%
        → Trigger another workflow
        
03:30 - Watch SigNoz light up with error spans
        → Show chaos.injected=true attribute
        → Show error status propagation
        
04:00 - Open Root Cause Copilot
        → Select the failed workflow
        → Ask: "Why did the last workflow fail?"
        → Copilot analyzes trace context
        → Streams back RCA with fix suggestion
        
04:30 - Close with Cost Intelligence
        → Before vs after chaos (retries cost more)
        → Per-agent cost breakdown
        
05:00 - "AgentOps Center: because blind agents aren't production-ready"
```

---

## SigNoz Dashboard Queries

### Query: Average cost per workflow
```
SELECT avg(gen_ai.usage.cost_usd) as avg_cost
FROM traces
WHERE gen_ai.usage.cost_usd IS NOT NULL
GROUP BY workflow.id
```

### Query: Agent failure rate
```
SELECT 
  agent.name,
  count(*) as total,
  countIf(status = 'ERROR') as errors,
  errors/total as failure_rate
FROM traces
GROUP BY agent.name
```

### Query: P99 latency by agent
```
SELECT
  agent.name,
  quantile(0.99)(duration_ms) as p99_ms
FROM traces
WHERE agent.name IS NOT NULL
GROUP BY agent.name
ORDER BY p99_ms DESC
```

---

## Blog Post Outline

**Title:** "We Built an AI Ops Center That Watches AI Think — Here's What We Found"

**Hook:** Your AI agents are black boxes. When they fail at 3am, you're blind.

**Sections:**
1. The Problem: Why AI agents are the new microservices
2. The Solution: Treating agents like production services
3. Architecture: LangGraph + FastAPI + OTel + SigNoz
4. Implementation: GenAI Semantic Conventions in practice
5. Demo: What chaos engineering revealed about our agents
6. Learnings: The surprising things we saw in traces
7. What's Next: Production-grade agent observability

**Key Screenshots to Capture:**
- [ ] SigNoz trace view showing full agent workflow
- [ ] span detail with gen_ai.* attributes
- [ ] Chaos mode enabled → error spans in SigNoz
- [ ] Cost Intelligence dashboard
- [ ] Root Cause Copilot in action
- [ ] Agent Timeline Gantt chart
