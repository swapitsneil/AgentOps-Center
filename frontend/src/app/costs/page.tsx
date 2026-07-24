'use client';
import { useState, useEffect, useCallback } from 'react';
import Sidebar from '@/components/Sidebar';
import { api } from '@/lib/api';
import { WorkflowRun, AGENTS } from '@/lib/types';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line, Cell } from 'recharts';
import { DollarSign, Zap, TrendingUp } from 'lucide-react';

export default function CostsPage() {
  const [runs, setRuns] = useState<WorkflowRun[]>([]);
  const [mounted, setMounted] = useState(false);
  
  const fetch = useCallback(async () => {
    try { setRuns(await api.runs.list()); } catch {}
  }, []);
  
  useEffect(() => {
    setMounted(true);
    fetch();
    const i = setInterval(fetch, 5000);
    return () => clearInterval(i);
  }, [fetch]);
  
  const completedRuns = runs.filter(r => r.result?.cost_summary);
  const totalCost = completedRuns.reduce((s, r) => s + (r.result?.cost_summary?.total_cost_usd || 0), 0);
  const totalTokens = completedRuns.reduce((s, r) =>
    s + (r.result?.cost_summary?.total_input_tokens || 0) + (r.result?.cost_summary?.total_output_tokens || 0), 0);
  
  // Per-agent cost aggregation
  const agentCosts = AGENTS.map(agent => {
    const total = completedRuns.reduce((s, r) =>
      s + (r.result?.cost_summary?.per_agent_costs?.[agent.name] || 0), 0);
    const tokens = completedRuns.reduce((s, r) =>
      s + (r.result?.cost_summary?.per_agent_tokens?.[agent.name] || 0), 0);
    return { name: agent.label, cost: total, tokens, color: agent.color };
  }).filter(a => a.cost > 0);
  
  // Cost trend per run
  const costTrend = completedRuns.slice(-10).map((r, i) => ({
    run: `Run ${i + 1}`,
    cost: r.result?.cost_summary?.total_cost_usd || 0,
    tokens: (r.result?.cost_summary?.total_input_tokens || 0) + (r.result?.cost_summary?.total_output_tokens || 0),
  }));
  
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <div className="sticky top-0 z-10 bg-[#020817]/80 backdrop-blur-md border-b border-blue-500/10 px-6 py-4">
          <h1 className="text-xl font-bold gradient-text">Cost Intelligence</h1>
          <p className="text-xs text-slate-500">Real-time token usage and LLM cost analytics per agent</p>
        </div>
        
        <div className="p-6 space-y-6">
          {/* Summary stats */}
          <div className="grid grid-cols-3 gap-4">
            {[
              { label: 'Total Spend', value: `$${totalCost.toFixed(6)}`, icon: DollarSign, color: 'text-blue-400' },
              { label: 'Total Tokens', value: totalTokens.toLocaleString(), icon: Zap, color: 'text-violet-400' },
              { label: 'Avg per Run', value: completedRuns.length ? `$${(totalCost / completedRuns.length).toFixed(6)}` : '$0', icon: TrendingUp, color: 'text-emerald-400' },
            ].map(({ label, value, icon: Icon, color }) => (
              <div key={label} className="glass-card p-4">
                <div className="flex items-center gap-2 text-xs text-slate-400 mb-1">
                  <Icon size={13} className={color} />{label}
                </div>
                <div className={`text-2xl font-bold font-mono ${color}`}>{value}</div>
              </div>
            ))}
          </div>
          
          <div className="grid grid-cols-2 gap-6">
            {/* Per-agent cost bar chart */}
            <div className="glass-card p-5">
              <h3 className="text-sm font-semibold text-white mb-4">Cost by Agent</h3>
              {agentCosts.length > 0 && mounted ? (
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={agentCosts} margin={{ top: 5, right: 10, bottom: 5, left: 10 }}>
                    <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={v => `$${v.toFixed(5)}`} />
                    <Tooltip
                      contentStyle={{ background: '#0d1327', border: '1px solid rgba(59,130,246,0.2)', borderRadius: '8px', fontSize: '12px' }}
                      formatter={(v: number) => [`$${v.toFixed(6)}`, 'Cost']}
                    />
                    <Bar dataKey="cost" radius={[4, 4, 0, 0]}>
                      {agentCosts.map((e, i) => <Cell key={i} fill={e.color} fillOpacity={0.8} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-48 flex items-center justify-center text-slate-500 text-sm">No data yet. Run a workflow.</div>
              )}
            </div>
            
            {/* Cost trend */}
            <div className="glass-card p-5">
              <h3 className="text-sm font-semibold text-white mb-4">Cost Trend (Last 10 Runs)</h3>
              {costTrend.length > 0 && mounted ? (
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={costTrend} margin={{ top: 5, right: 10, bottom: 5, left: 10 }}>
                    <XAxis dataKey="run" tick={{ fill: '#94a3b8', fontSize: 10 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={v => `$${v.toFixed(5)}`} />
                    <Tooltip
                      contentStyle={{ background: '#0d1327', border: '1px solid rgba(59,130,246,0.2)', borderRadius: '8px', fontSize: '12px' }}
                      formatter={(v: number) => [`$${v.toFixed(6)}`, 'Cost']}
                    />
                    <Line type="monotone" dataKey="cost" stroke="#3b82f6" strokeWidth={2} dot={{ fill: '#3b82f6', r: 4 }} />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-48 flex items-center justify-center text-slate-500 text-sm">No data yet. Run a workflow.</div>
              )}
            </div>
          </div>
          
          {/* Detailed table */}
          {completedRuns.length > 0 && (
            <div className="glass-card p-5">
              <h3 className="text-sm font-semibold text-white mb-4">Run Cost Breakdown</h3>
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-slate-400 border-b border-white/5">
                    <th className="text-left pb-2">Workflow ID</th>
                    <th className="text-right pb-2">Input Tokens</th>
                    <th className="text-right pb-2">Output Tokens</th>
                    <th className="text-right pb-2">Total Cost</th>
                  </tr>
                </thead>
                <tbody>
                  {completedRuns.slice(-10).map(run => (
                    <tr key={run.workflow_id} className="border-b border-white/3 hover:bg-white/3">
                      <td className="py-2 font-mono text-blue-400">{run.workflow_id}</td>
                      <td className="py-2 text-right text-slate-300">{run.result?.cost_summary?.total_input_tokens?.toLocaleString()}</td>
                      <td className="py-2 text-right text-slate-300">{run.result?.cost_summary?.total_output_tokens?.toLocaleString()}</td>
                      <td className="py-2 text-right text-emerald-400 font-mono">${run.result?.cost_summary?.total_cost_usd.toFixed(6)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
