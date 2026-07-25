"""
Real SigNoz MCP Client for AgentOps Center.

Architecture:
    The SigNoz MCP server is a Go binary that can be run in two transport modes:
    - stdio: subprocess piping (for development)
    - HTTP: REST endpoint at /mcp (for production/Docker)

    This client connects to the signoz-mcp-server in HTTP mode via the
    Model Context Protocol (MCP) JSON-RPC 2.0 protocol.

    The signoz-mcp-server translates MCP tool calls into SigNoz API calls,
    returning real observability data (traces, metrics, logs, alerts).

    Configuration (via environment variables):
        SIGNOZ_MCP_URL: URL of the signoz-mcp-server HTTP endpoint
                        (default: http://localhost:18080/mcp)
        SIGNOZ_URL:     Your SigNoz instance URL (passed through to MCP server)
        SIGNOZ_API_KEY: Your SigNoz API key (passed through to MCP server)
        MCP_TIMEOUT:    HTTP timeout in seconds (default: 30)

    When SIGNOZ_MCP_URL is not reachable, all methods return MCPUnavailable
    responses with is_available=False. The copilot detects this and degrades
    gracefully to local-context-only mode (clearly labelled as such).

References:
    - https://github.com/SigNoz/signoz-mcp-server
    - https://signoz.io/docs/ai/signoz-mcp-server/
    - https://modelcontextprotocol.io/specification
"""
import json
import logging
import os
import time
import uuid
from typing import Any, Optional

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger("agentops.mcp.client")


def _get_time_range_ms(minutes_ago: int = 60) -> tuple[int, int]:
    end_ms = int(time.time() * 1000)
    start_ms = end_ms - (minutes_ago * 60 * 1000)
    return start_ms, end_ms


# ---------------------------------------------------------------------------
# Pydantic response models
# ---------------------------------------------------------------------------

class MCPSpan(BaseModel):
    """Represents a single span from a SigNoz trace."""
    span_id: str = ""
    trace_id: str = ""
    parent_span_id: Optional[str] = None
    service_name: str = ""
    operation_name: str = ""
    duration_ms: float = 0.0
    status: str = "unset"
    attributes: dict[str, Any] = Field(default_factory=dict)
    start_time_unix_nano: int = 0


class MCPTrace(BaseModel):
    """A complete trace with all spans."""
    trace_id: str
    spans: list[MCPSpan] = Field(default_factory=list)
    root_service: str = ""
    total_duration_ms: float = 0.0
    error: bool = False
    span_count: int = 0


class MCPMetricPoint(BaseModel):
    """A single metric data point."""
    metric_name: str
    value: float
    timestamp_unix_ms: int = 0
    labels: dict[str, str] = Field(default_factory=dict)


class MCPLogRecord(BaseModel):
    """A single log entry."""
    timestamp: str = ""
    severity: str = ""
    body: str = ""
    service_name: str = ""
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class MCPAlertRule(BaseModel):
    """A SigNoz alert rule summary."""
    id: str = ""
    name: str = ""
    state: str = ""
    severity: str = ""
    condition: str = ""
    labels: dict[str, str] = Field(default_factory=dict)


class MCPService(BaseModel):
    """A service discovered in SigNoz APM."""
    service_name: str
    p99_latency_ms: float = 0.0
    error_rate: float = 0.0
    request_rate: float = 0.0
    call_count: int = 0


class MCPToolResult(BaseModel):
    """Wrapper for any raw MCP tool call result."""
    tool_name: str
    success: bool
    raw_content: list[dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None
    duration_ms: float = 0.0


class MCPUnavailable(BaseModel):
    """Returned when SigNoz MCP server is not reachable."""
    is_available: bool = False
    reason: str = ""


# ---------------------------------------------------------------------------
# MCP JSON-RPC protocol helpers
# ---------------------------------------------------------------------------

def _build_initialize_payload() -> dict:
    """MCP initialization handshake (required before tool calls)."""
    return {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "clientInfo": {
                "name": "agentops-center",
                "version": "0.1.0",
            },
        },
    }


def _build_tool_call_payload(tool_name: str, arguments: dict) -> dict:
    """Build an MCP tools/call JSON-RPC request."""
    return {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments,
        },
    }


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class SigNozMCPClient:
    """
    HTTP client for the SigNoz MCP server.

    The signoz-mcp-server runs as a sidecar (Docker container or local binary)
    Async client for communicating with signoz-mcp-server via JSON-RPC over HTTP.
    """
    def __init__(
        self,
        mcp_url: str | None = None,
        api_key: str | None = None,
        timeout: float | None = None,
    ):
        # Default candidates: env var > signoz-mcp-server:8080 > localhost:8080
        env_url = os.getenv("SIGNOZ_MCP_URL")
        self.mcp_candidates = [
            url.rstrip("/") for url in [
                env_url,
                "http://signoz-mcp-server:8080/mcp",
                "http://localhost:8080/mcp",
                "http://signoz-query-service:8080/mcp",
                "http://localhost:3301/mcp",
            ] if url
        ]
        self.mcp_url = (mcp_url or self.mcp_candidates[0]).rstrip("/")
        self.api_key = api_key or os.getenv("SIGNOZ_API_KEY", "")
        self.signoz_url = os.getenv("SIGNOZ_URL", "http://localhost:8080").rstrip("/")
        self.timeout = timeout or float(os.getenv("MCP_TIMEOUT", "15"))
        self._client: httpx.AsyncClient | None = None
        self._initialized: bool = False
        self._direct_query_service_mode: bool = False

    async def __aenter__(self) -> "SigNozMCPClient":
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["SIGNOZ-API-KEY"] = self.api_key
        self._client = httpx.AsyncClient(
            headers=headers,
            timeout=self.timeout,
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()

    async def _ensure_initialized(self) -> bool:
        """Send MCP initialize handshake across candidates, with retry & fallback."""
        if self._initialized:
            return True

        payload = _build_initialize_payload()

        # Try MCP endpoints first
        for target_url in self.mcp_candidates:
            try:
                resp = await self._client.post(target_url, content=json.dumps(payload))
                if resp.status_code == 200:
                    data = resp.json()
                    if "result" in data:
                        self.mcp_url = target_url
                        self._initialized = True
                        self._direct_query_service_mode = False
                        logger.info("SigNoz MCP server initialized at %s", target_url)
                        return True
            except Exception as exc:
                logger.debug("MCP target %s not reachable: %s", target_url, exc)

        # Fallback: Check direct SigNoz Query Service health endpoint
        for qs_url in [self.signoz_url, "http://query-service:8080", "http://localhost:8080", "http://localhost:3301"]:
            try:
                resp = await self._client.get(f"{qs_url}/api/v1/health")
                if resp.status_code == 200:
                    self.signoz_url = qs_url
                    self._initialized = True
                    self._direct_query_service_mode = True
                    logger.info("Connected to SigNoz Query Service directly at %s (REST fallback mode)", qs_url)
                    return True
            except Exception:
                pass

        logger.warning("SigNoz MCP Server and Query Service unreachable across all candidates.")
        return False

    async def _call_tool(self, tool_name: str, arguments: dict | None = None) -> MCPToolResult:
        """
        Execute a single MCP tool call and return the raw result.
        Returns MCPToolResult with success=False if the server is unreachable.
        """
        if arguments is None:
            arguments = {}
        # Add searchContext as required by MCP server spec
        arguments.setdefault("searchContext", f"agentops-center RCA query for tool {tool_name}")

        if not await self._ensure_initialized():
            return MCPToolResult(
                tool_name=tool_name, success=False,
                error="MCP server not initialized or unreachable",
            )

        payload = _build_tool_call_payload(tool_name, arguments)
        t0 = time.monotonic()

        try:
            resp = await self._client.post(self.mcp_url, content=json.dumps(payload))
            resp.raise_for_status()
            duration_ms = (time.monotonic() - t0) * 1000
            data = resp.json()

            if "error" in data:
                err_msg = data["error"].get("message", "MCP error")
                logger.error("MCP tool call error (%s): %s", tool_name, err_msg)
                return MCPToolResult(
                    tool_name=tool_name, success=False,
                    error=err_msg, duration_ms=duration_ms,
                )

            res = data.get("result", {})
            content = res.get("content", [])
            is_error = res.get("isError", False)

            return MCPToolResult(
                tool_name=tool_name,
                success=not is_error,
                raw_content=content,
                duration_ms=duration_ms,
                error="MCP tool reported isError=True" if is_error else None,
            )
        except Exception as exc:
            logger.error("MCP tool call failed (%s): %s", tool_name, exc)
            return MCPToolResult(
                tool_name=tool_name, success=False,
                error=str(exc),
                duration_ms=(time.monotonic() - t0) * 1000,
            )

    def _extract_text(self, result: MCPToolResult) -> str:
        """Extract text content from an MCP tool result."""
        if not result.success or not result.raw_content:
            return ""
        texts = []
        for item in result.raw_content:
            if item.get("type") == "text":
                texts.append(item.get("text", ""))
        return "\n".join(texts)

    # -----------------------------------------------------------------------
    # Public API methods — map to real signoz-mcp-server tools
    # -----------------------------------------------------------------------

    async def is_available(self) -> bool:
        """Check if the SigNoz MCP server is reachable."""
        try:
            if self._client is None:
                async with self:
                    return await self._ensure_initialized()
            return await self._ensure_initialized()
        except Exception:
            return False

    async def list_services(self, start_time_minutes_ago: int = 60) -> list[MCPService] | MCPUnavailable:
        """
        List APM services active in the last N minutes.
        MCP tool: signoz_list_services
        """
        start_ms, end_ms = _get_time_range_ms(start_time_minutes_ago)
        result = await self._call_tool("signoz_list_services", {
            "start": start_ms,
            "end": end_ms,
        })
        if not result.success:
            return MCPUnavailable(reason=result.error or "MCP unavailable")

        text = self._extract_text(result)
        # Parse the text response into structured objects.
        # The MCP server returns human-readable text; we parse key lines.
        services: list[MCPService] = []
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Best-effort parse: "service_name: p99=XXms errors=X%"
            parts = line.split()
            svc_name = parts[0].rstrip(":") if parts else "unknown"
            svc = MCPService(service_name=svc_name)
            for part in parts[1:]:
                if part.startswith("p99="):
                    try:
                        svc.p99_latency_ms = float(part.replace("p99=", "").replace("ms", ""))
                    except ValueError:
                        pass
                elif "error" in part.lower() and "=" in part:
                    try:
                        svc.error_rate = float(part.split("=")[1].replace("%", "")) / 100
                    except ValueError:
                        pass
            services.append(svc)

        return services if services else [MCPService(service_name="agentops-center-backend")]

    async def search_traces(
        self,
        service_name: str = "agentops-center-backend",
        start_minutes_ago: int = 60,
        limit: int = 5,
        filter_error: bool = False,
    ) -> list[MCPTrace] | MCPUnavailable:
        """
        Search for traces in SigNoz.
        MCP tool: signoz_search_traces
        Uses native MCP schema parameters: 'service' and 'error'.
        """
        start_ms, end_ms = _get_time_range_ms(start_minutes_ago)
        args: dict[str, Any] = {
            "start": start_ms,
            "end": end_ms,
            "limit": limit,
            "service": service_name,
        }
        if filter_error:
            args["error"] = True

        result = await self._call_tool("signoz_search_traces", args)
        if not result.success:
            return MCPUnavailable(reason=result.error or "MCP unavailable")

        text = self._extract_text(result)
        # Parse trace IDs and basic metadata from text response
        traces: list[MCPTrace] = []
        current_trace: dict[str, Any] | None = None
        for line in text.splitlines():
            line = line.strip()
            if "traceID" in line or "trace_id" in line.lower() or "traceid" in line.lower():
                parts = line.split(":")
                if len(parts) >= 2:
                    tid = parts[1].strip().strip('"').strip(",")
                    if tid:
                        current_trace = {"trace_id": tid, "error": False}
                        traces.append(MCPTrace(trace_id=tid))
            if current_trace and "error" in line.lower() and "true" in line.lower():
                if traces:
                    traces[-1].error = True
            if current_trace and "duration" in line.lower():
                try:
                    dur_str = line.split(":")[-1].strip().replace("ms", "").replace(",", "")
                    if traces:
                        traces[-1].total_duration_ms = float(dur_str)
                except ValueError:
                    pass

        return traces

    async def get_trace_details(self, trace_id: str) -> MCPTrace | MCPUnavailable:
        """
        Get full span hierarchy for a specific trace.
        MCP tool: signoz_get_trace_details
        Uses native MCP schema parameter: 'traceId'.
        """
        result = await self._call_tool("signoz_get_trace_details", {"traceId": trace_id})
        if not result.success:
            return MCPUnavailable(reason=result.error or "MCP unavailable")

        text = self._extract_text(result)
        spans: list[MCPSpan] = []
        for line in text.splitlines():
            line = line.strip()
            if "spanID" in line or "span_id" in line.lower() or "spanid" in line.lower():
                parts = line.split(":")
                if len(parts) >= 2:
                    sid = parts[1].strip().strip('"').strip(",")
                    if sid:
                        spans.append(MCPSpan(span_id=sid, trace_id=trace_id))
        return MCPTrace(trace_id=trace_id, spans=spans, span_count=len(spans))

    async def get_metrics(
        self,
        metric_name: str,
        start_minutes_ago: int = 60,
        group_by: list[str] | None = None,
    ) -> list[MCPMetricPoint] | MCPUnavailable:
        """
        Query metric values from SigNoz.
        MCP tool: signoz_query_metrics
        Uses native MCP schema parameter: 'metricName'.
        """
        start_ms, end_ms = _get_time_range_ms(start_minutes_ago)
        args: dict[str, Any] = {
            "metricName": metric_name,
            "start": start_ms,
            "end": end_ms,
        }
        if group_by:
            args["groupBy"] = group_by

        result = await self._call_tool("signoz_query_metrics", args)
        if not result.success:
            return MCPUnavailable(reason=result.error or "MCP unavailable")

        text = self._extract_text(result)
        points: list[MCPMetricPoint] = []
        for line in text.splitlines():
            line = line.strip()
            if "value" in line.lower() and "=" in line:
                try:
                    val_str = line.split("=")[-1].strip().split()[0]
                    points.append(MCPMetricPoint(
                        metric_name=metric_name,
                        value=float(val_str),
                        timestamp_unix_ms=int(time.time() * 1000),
                    ))
                except (ValueError, IndexError):
                    pass
        return points

    async def search_logs(
        self,
        service_name: str = "agentops-center-backend",
        start_minutes_ago: int = 60,
        severity: str | None = None,
        limit: int = 20,
    ) -> list[MCPLogRecord] | MCPUnavailable:
        """
        Search logs in SigNoz.
        MCP tool: signoz_search_logs
        Uses native MCP schema parameters: 'service' and 'severity'.
        """
        start_ms, end_ms = _get_time_range_ms(start_minutes_ago)
        args: dict[str, Any] = {
            "start": start_ms,
            "end": end_ms,
            "limit": limit,
            "service": service_name,
        }
        if severity:
            args["severity"] = severity.upper()

        result = await self._call_tool("signoz_search_logs", args)
        if not result.success:
            return MCPUnavailable(reason=result.error or "MCP unavailable")

        text = self._extract_text(result)
        logs: list[MCPLogRecord] = []
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                # Each line is a log record in human-readable form
                severity_detected = "INFO"
                if "ERROR" in line.upper():
                    severity_detected = "ERROR"
                elif "WARN" in line.upper():
                    severity_detected = "WARN"
                logs.append(MCPLogRecord(
                    body=line[:500],
                    severity=severity_detected,
                    service_name=service_name,
                ))
        return logs

    async def list_alerts(self) -> list[MCPAlertRule] | MCPUnavailable:
        """
        List active alert rules in SigNoz.
        MCP tool: signoz_list_alert_rules
        """
        result = await self._call_tool("signoz_list_alert_rules", {})
        if not result.success:
            return MCPUnavailable(reason=result.error or "MCP unavailable")

        text = self._extract_text(result)
        alerts: list[MCPAlertRule] = []
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                alert_id = str(uuid.uuid4())
                state = "active" if "firing" in line.lower() else "ok"
                alerts.append(MCPAlertRule(
                    id=alert_id,
                    name=line[:200],
                    state=state,
                    severity="warning" if "warn" in line.lower() else "critical",
                    condition=line[:200],
                ))
        return alerts

    async def aggregate_traces(
        self,
        service_name: str = "agentops-center-backend",
        start_minutes_ago: int = 60,
        aggregation: str = "count",
        group_by: str = "name",
    ) -> MCPToolResult:
        """
        Aggregate trace statistics.
        MCP tool: signoz_aggregate_traces
        Uses native MCP schema parameters: 'aggregation', 'service', 'groupBy'.
        """
        start_ms, end_ms = _get_time_range_ms(start_minutes_ago)
        return await self._call_tool("signoz_aggregate_traces", {
            "start": start_ms,
            "end": end_ms,
            "service": service_name,
            "aggregation": aggregation,
            "groupBy": [group_by],
            "limit": 20,
        })

    async def get_service_top_operations(
        self,
        service_name: str = "agentops-center-backend",
        start_minutes_ago: int = 60,
    ) -> MCPToolResult:
        """
        Get top operations for a service (latency/error ranked).
        MCP tool: signoz_get_service_top_operations
        Uses native MCP schema parameter: 'service'.
        """
        start_ms, end_ms = _get_time_range_ms(start_minutes_ago)
        return await self._call_tool("signoz_get_service_top_operations", {
            "service": service_name,
            "start": start_ms,
            "end": end_ms,
        })

    async def list_metrics(self, search_text: str = "gen_ai") -> MCPToolResult:
        """
        Discover metric names matching a search term.
        MCP tool: signoz_list_metrics
        Uses native MCP schema parameter: 'searchText'.
        """
        return await self._call_tool("signoz_list_metrics", {
            "searchText": search_text,
            "limit": 50,
        })

    async def execute_builder_query(self, query: str | dict) -> MCPToolResult:
        """
        Execute a raw Query Builder v5 query in SigNoz.
        MCP tool: signoz_execute_builder_query
        Uses native MCP schema parameter: 'query'.
        """
        return await self._call_tool("signoz_execute_builder_query", {
            "query": query,
        })


# ---------------------------------------------------------------------------
# Module-level singleton factory
# ---------------------------------------------------------------------------

def get_mcp_client(
    mcp_url: str | None = None,
    api_key: str | None = None,
) -> SigNozMCPClient:
    """Factory function to create an MCP client with default config from env."""
    return SigNozMCPClient(mcp_url=mcp_url, api_key=api_key)
