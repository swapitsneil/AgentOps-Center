'use client';
import { useState, useEffect, useCallback } from 'react';
import Sidebar from '@/components/Sidebar';
import { api } from '@/lib/api';
import { WorkflowRun, HealthStatus, AGENTS } from '@/lib/types';
import {
  Play, AlertTriangle, Activity, DollarSign,
  GitBranch, Zap, RefreshCw, ChevronRight,
  CheckCircle2, XCircle, Clock, Cpu, MemoryStick
} from 'lucide-react';
import { clsx } from 'clsx';

function StatCard({ label, value, sub, icon: Icon, color }: {
  label: string; value: string | number; sub: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  color: 'blue' | 'violet' | 'emerald' | 'rose' | 'amber';
}) {
  const colors = {
    blue: 'from-blue-500/20 to-blue-600/5 border-blue-500/20 text-blue-400',
    violet: 'from-violet-500/20 to-violet-600/5 border-violet-500/20 text-violet-400',
    emerald: 'from-emerald-500/20 to-emerald-600/5 border-emerald-500/20 text-emerald-400',
    rose: 'from-rose-500/20 to-rose-600/5 border-rose-500/20 text-rose-400',
    amber: 'from-amber-500/20 to-amber-600/5 border-amber-500/20 text-amber-400',
  };
  return (
    <div className={`glass-card bg-gradient-to-br ${colors[color]} p-5`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">{label}</p>
          <p className="text-3xl font-bold text-white mt-1">{value}</p>
          <p className="text-xs text-slate-500 mt-1">{sub}</p>
        </div>
        <div className={`p-2 rounded-lg bg-gradient-to-br ${colors[color]}`}>
          <Icon size={20} className={colors[color].split(' ').pop()} />
        </div>
      </div>
    </div>
  );
}

function RunStatusBadge({ status }: { status: string }) {
  const cfg = {
    running: { cls: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/30', icon: <RefreshCw size={10} className="animate-spin" />, label: 'Running' },
    completed: { cls: 'text-blue-400 bg-blue-400/10 border-blue-400/30', icon: <CheckCircle2 size={10} />, label: 'Completed' },
    failed: { cls: 'text-rose-400 bg-rose-400/10 border-rose-400/30', icon: <XCircle size={10} />, label: 'Failed' },
    idle: { cls: 'text-slate-400 bg-slate-400/10 border-slate-400/30', icon: <Clock size={10} />, label: 'Idle' },
  }[status] || { cls: 'text-slate-400 bg-slate-400/10 border-slate-400/30', icon: <Clock size={10} />, label: status };
  
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-xs font-medium ${cfg.cls}`}>
      {cfg.icon} {cfg.label}
    </span>
  );
}

export default function CommandCenter() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [runs, setRuns] = useState<WorkflowRun[]>([]);
  const [triggering, setTriggering] = useState(false);
  const [lastTriggered, setLastTriggered] = useState<string | null>(null);
  const [time, setTime] = useState<Date>(new Date());
  const [mounted, setMounted] = useState(false);
  
  const fetchData = useCallback(async () => {
    try {
      const [h, r] = await Promise.all([api.health(), api.runs.list()]);
      setHealth(h);
      setRuns(r);
    } catch { /* backend not ready */ }
  }, []);
  
  useEffect(() => {
    setMounted(true);
    setTime(new Date());
    fetchData();
    const interval = setInterval(fetchData, 3000);
    const clock = setInterval(() => setTime(new Date()), 1000);
    return () => { clearInterval(interval); clearInterval(clock); };
  }, [fetchData]);
  
  const triggerRun = async () => {
    setTriggering(true);
    try {
      const { workflow_id } = await api.runs.trigger();
      setLastTriggered(workflow_id);
      await fetchData();
    } catch (e) {
      console.error(e);
    } finally {
      setTriggering(false);
    }
  };
  
  const activeRuns = runs.filter(r => r.status === 'running').length;
  const totalCost = runs.reduce((sum, r) => sum + (r.result?.cost_summary?.total_cost_usd || 0), 0);
  const chaosActive = health?.chaos?.active ?? false;
  const completedRuns = runs.filter(r => r.status === 'completed').length;
  
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      
      <main className="flex-1 overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 z-10 bg-[#020817]/80 backdrop-blur-md border-b border-blue-500/10 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold gradient-text">Command Center</h1>
              <p className="text-xs text-slate-500">AI Operations Platform — Real-time Agent Observability</p>
            </div>
            <div className="flex items-center gap-4">
              {health && (
                <div className="flex items-center gap-3 text-xs">
                  <div className="flex items-center gap-1.5 text-slate-400">
                    <Cpu size={12} />
                    <span>{health.system.cpu_percent.toFixed(1)}% CPU</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-slate-400">
                    <MemoryStick size={12} />
                    <span>{health.system.memory_percent.toFixed(0)}% RAM</span>
                  </div>
                </div>
              )}
              <div className="font-mono text-sm text-blue-400 font-semibold">
                {mounted ? time.toLocaleTimeString() : ''}
              </div>
              {chaosActive && (
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-rose-500/15 border border-rose-500/30 text-rose-400 text-xs animate-pulse">
                  <AlertTriangle size={11} />
                  CHAOS ACTIVE
                </div>
              )}
            </div>
          </div>
        </div>
        
        <div className="p-6 space-y-6">
          {/* Stat Cards */}
          <div className="grid grid-cols-4 gap-4">
            <StatCard label="Active Runs" value={activeRuns} sub="Agent workflows running" icon={Activity} color="emerald" />
            <StatCard label="Total Cost" value={`$${totalCost.toFixed(4)}`} sub="LLM spend today" icon={DollarSign} color="blue" />
            <StatCard label="Chaos Mode" value={chaosActive ? 'ON 🔥' : 'OFF'} sub={chaosActive ? 'Failures being injected' : 'System stable'} icon={Zap} color={chaosActive ? 'rose' : 'violet'} />
            <StatCard label="Completed" value={completedRuns} sub="Successful workflows" icon={CheckCircle2} color="amber" />
          </div>
          
          {/* Trigger Section */}
          <div className="glass-card p-5">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-base font-semibold text-white">Incident Response Workflow</h2>
                <p className="text-xs text-slate-500 mt-0.5">Trigger a 4-agent DevOps incident response: Monitor → Diagnosis → Fix → Report</p>
              </div>
              <button
                onClick={triggerRun}
                disabled={triggering}
                className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-blue-600 to-violet-600 hover:from-blue-500 hover:to-violet-500 text-white text-sm font-semibold rounded-lg transition-all duration-200 disabled:opacity-60 disabled:cursor-not-allowed shadow-lg shadow-blue-500/20"
              >
                {triggering ? <RefreshCw size={15} className="animate-spin" /> : <Play size={15} />}
                {triggering ? 'Triggering...' : 'Trigger Incident Response'}
              </button>
            </div>
            
            {lastTriggered && (
              <div className="text-xs text-emerald-400 flex items-center gap-1.5">
                <CheckCircle2 size={12} />
                Workflow triggered: <span className="font-mono">{lastTriggered}</span>
                <a href={`/timeline`} className="text-blue-400 hover:text-blue-300 flex items-center gap-0.5 ml-1">
                  View Timeline <ChevronRight size={11} />
                </a>
              </div>
            )}
          </div>
          
          <div className="grid grid-cols-3 gap-6">
            {/* Recent Runs */}
            <div className="col-span-2 glass-card p-5">
              <h2 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                <GitBranch size={15} className="text-blue-400" />
                Recent Workflow Runs
              </h2>
              {runs.length === 0 ? (
                <div className="text-center py-8 text-slate-500 text-sm">
                  <Activity size={32} className="mx-auto mb-2 text-slate-600" />
                  No runs yet. Trigger your first incident response.
                </div>
              ) : (
                <div className="space-y-2">
                  {runs.slice(0, 8).map(run => (
                    <div key={run.workflow_id} className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-white/3 border border-white/5 hover:bg-white/5 transition-colors">
                      <RunStatusBadge status={run.status} />
                      <div className="flex-1 min-w-0">
                        <div className="text-xs text-slate-300 truncate">{run.scenario}</div>
                        <div className="font-mono text-xs text-slate-500">{run.workflow_id}</div>
                      </div>
                      {run.result?.cost_summary && (
                        <div className="text-xs text-blue-400/70 font-mono">
                          ${run.result.cost_summary.total_cost_usd.toFixed(5)}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
            
            {/* Agent Fleet */}
            <div className="glass-card p-5">
              <h2 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                <Zap size={15} className="text-violet-400" />
                Agent Fleet
              </h2>
              <div className="space-y-3">
                {AGENTS.map(agent => {
                  const agentRuns = runs.filter(r =>
                    r.result?.agent_timings?.[agent.name] !== undefined
                  );
                  const avgMs = agentRuns.length > 0
                    ? agentRuns.reduce((sum, r) => sum + (r.result?.agent_timings?.[agent.name] || 0), 0) / agentRuns.length
                    : 0;
                  
                  return (
                    <div key={agent.name} className="flex items-center gap-3">
                      <div
                        className="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold"
                        style={{ backgroundColor: agent.bgColor, border: `1px solid ${agent.borderColor}`, color: agent.color }}
                      >
                        {agent.label[0]}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-xs font-medium text-slate-300">{agent.label} Agent</div>
                        <div className="text-xs text-slate-500">{agent.description}</div>
                      </div>
                      {avgMs > 0 && (
                        <div className="text-xs text-slate-400 font-mono">{avgMs.toFixed(0)}ms</div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
