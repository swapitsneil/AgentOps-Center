# Migration Report — AgentOps Center Architectural Refactor

**Date**: 2026-07-23  
**Refactor**: Safe architectural fix — no UI changes, preserved API contracts

See the full report in the artifacts: [MIGRATION_REPORT.md](../MIGRATION_REPORT.md)

## Summary of Changes

### 1. MCP Integration (was: empty `__init__.py`)
- **New**: `backend/mcp/client.py` — real `SigNozMCPClient` using HTTP JSON-RPC 2.0
- Connects to `signoz-mcp-server` sidecar at `SIGNOZ_MCP_URL`
- Calls: `signoz_list_services`, `signoz_search_traces`, `signoz_query_metrics`, `signoz_search_logs`, `signoz_list_alert_rules`
- Graceful fallback when server unreachable

### 2. Evidence Engine (was: nothing)
- **New**: `backend/copilot/evidence_engine.py`
- Collects `VerifiedEvidence` from real MCP tool calls
- Every field sourced from named MCP tool — no fabrication possible

### 3. Reasoning Engine (was: nothing)  
- **New**: `backend/copilot/reasoning.py`
- Grades confidence: HIGH / MEDIUM / LOW / NONE
- Builds anti-hallucination system prompt grounded in evidence
- LLM cannot cite trace IDs not present in evidence

### 4. Chaos Engine Fixes
- **TOOL_FAILURE**: Now calls `chaos_check_tool()` inside `tool_span()` → works
- **INVALID_OUTPUT**: Now calls `chaos_corrupt_output()` after each LLM response → works
- Both produce OTel ERROR spans visible in SigNoz

### 5. gen_ai.system Fix
- Was: hardcoded `"openai"` for all providers
- Now: `_detect_provider(model)` auto-detects groq/openai/anthropic/google/openrouter

### 6. Compare Runs Fix
- Response keys changed from `duration_ms`/`cost_usd` to `total_duration_ms`/`total_cost_usd`
- Frontend now displays real values instead of undefined/NaN

### 7. Foundry casting.yaml
- Was: invented format
- Now: real SigNoz Foundry `apiVersion: v1alpha1` schema (docker/compose flavor)

### 8. Docker Compose
- Added `signoz-mcp` sidecar service (`signoz/signoz-mcp-server:latest`)
- Available at `http://localhost:18080/mcp`
- Backend wired via `SIGNOZ_MCP_URL=http://signoz-mcp:8000/mcp`

### 9. Tests
- `tests/conftest.py`: fixtures, env mocks, mock MCP, mock LLM
- `tests/test_chaos.py`: 16 tests, all 6 chaos modes
- `tests/test_copilot.py`: 14 evidence + reasoning engine tests
- `tests/test_api.py`: 15 API endpoint tests + OTel unit tests
