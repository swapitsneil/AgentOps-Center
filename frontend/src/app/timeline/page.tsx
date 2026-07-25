'use client';
import { useState, useEffect, useCallback } from 'react';
import Sidebar from '@/components/Sidebar';
import { api } from '@/lib/api';
import { WorkflowRun, AGENTS } from '@/lib/types';
import { GitBranch, RefreshCw, ChevronDown, ChevronRight } from 'lucide-react';
import { clsx } from 'clsx';

function TimelineBar({ run }: { run: WorkflowRun }) {
  const [expanded, setExpanded] = useState(false);
  const timings = run.result?.agent_timings || {};
  const totalMs = Object.values(timings).reduce((s, v) => s + v, 0) || 1;
  const maxMs = Math.max(...Object.values(timings).map(Number), 0);
  const slowestAgent = maxMs > 0 ? Object.entries(timings).find(([_, v]) => v === maxMs)?.[0] : null;
  
  let offset = 0;
  
  return (
    <div className="glass-card p-4 glass-card-hover">
      <div
        className="flex items-center justify-between cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          {expanded ? <ChevronDown size={14} className="text-blue-400" /> : <ChevronRight size={14} className="text-slate-500" />}
          <div>
            <div className="text-sm font-medium text-slate-200 truncate max-w-md">{run.scenario}</div>
            <div className="font-mono text-xs text-slate-500 mt-0.5">{run.workflow_id}</div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className={clsx('text-xs px-2 py-0.5 rounded-full border',
            run.status === 'completed' ? 'text-blue-400 bg-blue-400/10 border-blue-400/30' :
            run.status === 'failed' ? 'text-rose-400 bg-rose-400/10 border-rose-400/30' :
            'text-emerald-400 bg-emerald-400/10 border-emerald-400/30'
          )}>{run.status}</div>
          <div className="text-xs text-slate-500 font-mono">{(totalMs / 1000).toFixed(1)}s total</div>
        </div>
      </div>
      
      {/* Gantt bars */}
      <div className="mt-4 space-y-2">
        {AGENTS.map(agent => {
          const ms = timings[agent.name];
          const widthPct = ms ? Math.max(5, (ms / totalMs) * 100) : 0;
          const leftPct = offset;
          if (ms) offset += (ms / totalMs) * 100;
          const isSlowest = agent.name === slowestAgent;
          
          return (
            <div key={agent.name} className="flex items-center gap-3">
              <div className="w-28 flex items-center justify-between text-xs font-medium" style={{ color: agent.color }}>
                <span>{agent.label}</span>
                {isSlowest && <span className="text-[9px] bg-amber-500/20 text-amber-300 border border-amber-500/40 px-1 rounded font-mono">🔥 Slowest</span>}
              </div>
              <div className="flex-1 h-6 bg-white/5 rounded-md overflow-hidden relative">
                {ms ? (
                  <div
                    className="absolute top-0 h-full rounded-md flex items-center justify-between px-2 text-xs font-mono text-white"
                    style={{
                      left: `${leftPct}%`,
                      width: `${widthPct}%`,
                      backgroundColor: isSlowest ? '#b45309' : agent.bgColor,
                      border: `1px solid ${isSlowest ? '#f59e0b' : agent.borderColor}`,
                      minWidth: '50px',
                    }}
                  >
                    <span>{ms}ms</span>
                    {isSlowest && <span className="text-[10px] text-amber-200">Critical Path</span>}
                  </div>
                ) : (
                  <div className="h-full flex items-center px-2">
                    <span className="text-xs text-rose-400 font-semibold">{run.status === 'failed' ? '🔴 Failed Node' : 'pending'}</span>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
      
      {/* Expanded detail */}
      {expanded && run.result && (
        <div className="mt-4 grid grid-cols-2 gap-3 pt-4 border-t border-white/5">
          {[
            { label: 'Monitor Output', val: run.result.monitor_output, color: '#60a5fa' },
            { label: 'Diagnosis Output', val: run.result.diagnosis_output, color: '#a78bfa' },
            { label: 'Fix Output', val: run.result.fix_output, color: '#34d399' },
            { label: 'Report Output', val: run.result.report_output, color: '#fbbf24' },
          ].map(({ label, val, color }) => val && (
            <div key={label} className="terminal p-3">
              <div className="text-xs font-semibold mb-1" style={{ color }}>{label}</div>
              <div className="text-xs text-slate-300 leading-relaxed">{val}</div>
            </div>
          ))}
          {run.result.error && (
            <div className="col-span-2 terminal p-3 border-rose-500/30">
              <div className="text-xs font-semibold text-rose-400 mb-1">Error</div>
              <div className="text-xs text-rose-300 font-mono">{run.result.error}</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function TimelinePage() {
  const [runs, setRuns] = useState<WorkflowRun[]>([]);
  const [loading, setLoading] = useState(true);
  
  const fetchRuns = useCallback(async () => {
    try {
      const data = await api.runs.list();
      setRuns(data);
    } finally {
      setLoading(false);
    }
  }, []);
  
  useEffect(() => {
    fetchRuns();
    const interval = setInterval(fetchRuns, 2000);
    return () => clearInterval(interval);
  }, [fetchRuns]);
  
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <div className="sticky top-0 z-10 bg-[#020817]/80 backdrop-blur-md border-b border-blue-500/10 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold gradient-text">Agent Timeline</h1>
              <p className="text-xs text-slate-500">Execution replay — click any run to inspect agent outputs and span data</p>
            </div>
            <button onClick={fetchRuns} className="text-slate-400 hover:text-blue-400 transition-colors">
              <RefreshCw size={16} />
            </button>
          </div>
        </div>
        <div className="p-6 space-y-4">
          {loading ? (
            <div className="text-center py-16 text-slate-500">
              <RefreshCw size={24} className="animate-spin mx-auto mb-3" />
              Loading runs...
            </div>
          ) : runs.length === 0 ? (
            <div className="text-center py-16 text-slate-500">
              <GitBranch size={32} className="mx-auto mb-3 text-slate-600" />
              <p className="text-sm">No workflow runs yet.</p>
              <p className="text-xs text-slate-600 mt-1">Go to Command Center and trigger a run.</p>
            </div>
          ) : (
            runs.map(run => <TimelineBar key={run.workflow_id} run={run} />)
          )}
        </div>
      </main>
    </div>
  );
}
