const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  });
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  return res.json();
}

export const api = {
  health: () => fetchAPI<import('./types').HealthStatus>('/health'),
  
  runs: {
    trigger: (scenario?: string, model?: string) =>
      fetchAPI<{ workflow_id: string; status: string; scenario: string }>('/api/runs/trigger', {
        method: 'POST',
        body: JSON.stringify({ scenario, model }),
      }),
    get: (id: string) => fetchAPI<import('./types').WorkflowRun>(`/api/runs/${id}`),
    list: () => fetchAPI<import('./types').WorkflowRun[]>('/api/runs/'),
    scenarios: () => fetchAPI<{ scenarios: string[] }>('/api/runs/scenarios/list'),
    streamUrl: (id: string) => `${API_BASE}/api/runs/${id}/stream`,
  },
  
  chaos: {
    state: () => fetchAPI<import('./types').ChaosState>('/api/chaos/state'),
    modes: () => fetchAPI<{ modes: Array<{ id: string; label: string; description: string }> }>('/api/chaos/modes'),
    enable: (mode: string, intensity: number) =>
      fetchAPI('/api/chaos/enable', {
        method: 'POST',
        body: JSON.stringify({ mode, intensity }),
      }),
    disable: (mode?: string) =>
      fetchAPI('/api/chaos/disable', {
        method: 'POST',
        body: JSON.stringify(mode ? { mode } : {}),
      }),
  },
  
  copilot: {
    suggestions: () => fetchAPI<{ suggestions: string[] }>('/api/copilot/suggestions'),
    askUrl: () => `${API_BASE}/api/copilot/ask`,
  },
};
