export type WorkflowStatus = 'running' | 'completed' | 'failed' | 'idle';

export interface WorkflowRun {
  workflow_id: string;
  status: WorkflowStatus;
  scenario: string;
  result?: {
    monitor_output?: string;
    diagnosis_output?: string;
    fix_output?: string;
    report_output?: string;
    agent_timings?: Record<string, number>;
    cost_summary?: CostSummary;
    error?: string;
  };
}

export interface CostSummary {
  workflow_id: string;
  total_input_tokens: number;
  total_output_tokens: number;
  total_cost_usd: number;
  per_agent_costs: Record<string, number>;
  per_agent_tokens: Record<string, number>;
}

export interface ChaosState {
  active: boolean;
  modes: Record<string, number>;
  total_injected: number;
  last_injection: number | null;
}

export interface HealthStatus {
  status: string;
  timestamp: number;
  system: {
    cpu_percent: number;
    memory_percent: number;
    memory_used_gb: number;
  };
  chaos: ChaosState;
  service: {
    name: string;
    version: string;
    otlp_endpoint: string;
  };
}

export interface AgentInfo {
  name: string;
  label: string;
  color: string;
  bgColor: string;
  borderColor: string;
  description: string;
}

export const AGENTS: AgentInfo[] = [
  {
    name: 'monitor_agent',
    label: 'Monitor',
    color: '#60a5fa',
    bgColor: 'rgba(96, 165, 250, 0.1)',
    borderColor: 'rgba(96, 165, 250, 0.3)',
    description: 'Detects incidents from system metrics',
  },
  {
    name: 'diagnosis_agent',
    label: 'Diagnosis',
    color: '#a78bfa',
    bgColor: 'rgba(167, 139, 250, 0.1)',
    borderColor: 'rgba(167, 139, 250, 0.3)',
    description: 'Root cause analysis via log search',
  },
  {
    name: 'fix_agent',
    label: 'Fix',
    color: '#34d399',
    bgColor: 'rgba(52, 211, 153, 0.1)',
    borderColor: 'rgba(52, 211, 153, 0.3)',
    description: 'Generates remediation steps',
  },
  {
    name: 'report_agent',
    label: 'Report',
    color: '#fbbf24',
    bgColor: 'rgba(251, 191, 36, 0.1)',
    borderColor: 'rgba(251, 191, 36, 0.3)',
    description: 'Creates incident postmortem',
  },
];
