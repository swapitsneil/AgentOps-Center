"""
Accumulates cost/token metrics across a workflow run.
Exposes OTel counters and histograms for SigNoz dashboards.
"""
from dataclasses import dataclass, field
from typing import Dict
from opentelemetry import metrics

meter = metrics.get_meter("agentops.costs")

# OTel metrics instruments
total_tokens_counter = meter.create_counter(
    name="gen_ai.total_tokens",
    unit="tokens",
    description="Total tokens consumed across all LLM calls",
)
cost_counter = meter.create_counter(
    name="gen_ai.total_cost_usd",
    unit="USD",
    description="Total estimated cost of LLM calls in USD",
)
workflow_duration_histogram = meter.create_histogram(
    name="agent.workflow.duration_ms",
    unit="ms",
    description="End-to-end duration of agent workflows",
)
agent_call_counter = meter.create_counter(
    name="agent.llm_calls",
    unit="calls",
    description="Number of LLM calls per agent",
)


@dataclass
class WorkflowCostSummary:
    workflow_id: str
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    per_agent_costs: Dict[str, float] = field(default_factory=dict)
    per_agent_tokens: Dict[str, int] = field(default_factory=dict)
    
    def add_llm_call(self, agent_name: str, input_tokens: int, output_tokens: int, cost: float) -> None:
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost_usd += cost
        self.per_agent_costs[agent_name] = self.per_agent_costs.get(agent_name, 0.0) + cost
        self.per_agent_tokens[agent_name] = self.per_agent_tokens.get(agent_name, 0) + input_tokens + output_tokens
        
        # Emit OTel metrics
        attrs = {"agent.name": agent_name, "workflow.id": self.workflow_id}
        total_tokens_counter.add(input_tokens + output_tokens, attrs)
        cost_counter.add(cost, attrs)
        agent_call_counter.add(1, attrs)
    
    def to_dict(self) -> dict:
        return {
            "workflow_id": self.workflow_id,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "per_agent_costs": {k: round(v, 6) for k, v in self.per_agent_costs.items()},
            "per_agent_tokens": self.per_agent_tokens,
        }
