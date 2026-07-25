'use client';
import { useState, useEffect, useCallback } from 'react';
import Sidebar from '@/components/Sidebar';
import { api } from '@/lib/api';
import { ChaosState } from '@/lib/types';
import { Zap, AlertTriangle, Shield, ShieldOff, Clock, Bug, Skull } from 'lucide-react';

interface ChaosModeInfo {
  id: string;
  label: string;
  description: string;
}

const MODE_ICONS: Record<string, any> = {
  llm_timeout: Clock,
  llm_error: AlertTriangle,
  tool_failure: Bug,
  slow_response: Zap,
  invalid_output: ShieldOff,
  agent_crash: Skull,
};

export default function ChaosPage() {
  const [modes, setModes] = useState<ChaosModeInfo[]>([]);
  const [chaosState, setChaosState] = useState<ChaosState | null>(null);
  const [intensities, setIntensities] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [m, s] = await Promise.all([api.chaos.modes(), api.chaos.state()]);
      setModes(m.modes);
      setChaosState(s);
    } catch (e) {
      console.error(e);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const toggleMode = async (modeId: string) => {
    setLoading(true);
    try {
      const isActive = !!chaosState?.modes?.[modeId];
      if (isActive) {
        await api.chaos.disable(modeId);
      } else {
        const intensity = intensities[modeId] ?? 0.7;
        await api.chaos.enable(modeId, intensity);
      }
      await fetchData();
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const disableAll = async () => {
    setLoading(true);
    try {
      await api.chaos.disable();
      await fetchData();
    } finally {
      setLoading(false);
    }
  };

  const activeCount = chaosState?.modes ? Object.keys(chaosState.modes).length : 0;

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 z-10 bg-[#020817]/80 backdrop-blur-md border-b border-blue-500/10 px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold gradient-text">Chaos Engineering Engine</h1>
            <p className="text-xs text-slate-500">Inject Runtime Faults → Verify SigNoz Observability & Alerts</p>
          </div>
          {activeCount > 0 && (
            <button
              onClick={disableAll}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/40 text-xs font-semibold rounded-lg transition-all"
            >
              <Shield size={14} /> Restore All Systems ({activeCount} Active)
            </button>
          )}
        </div>

        <div className="p-6 space-y-6">
          {/* Status Bar */}
          <div className={`glass-card p-4 flex items-center justify-between border ${activeCount > 0 ? 'border-rose-500/30 bg-rose-500/5' : 'border-emerald-500/20'}`}>
            <div className="flex items-center gap-3">
              <div className={`w-3 h-3 rounded-full ${activeCount > 0 ? 'bg-rose-500 animate-ping' : 'bg-emerald-400'}`} />
              <div>
                <div className="text-sm font-semibold text-white">
                  {activeCount > 0 ? `Chaos Injection ACTIVE — ${activeCount} Fault Rules Engaged` : 'System Operational — 0 Active Injections'}
                </div>
                <div className="text-xs text-slate-500">
                  Total Injections Recorded: {chaosState?.total_injected || 0}
                </div>
              </div>
            </div>
          </div>

          {/* Chaos Verification Pipeline Flow */}
          <div className="glass-card p-3.5 flex items-center justify-between border border-blue-500/20 text-xs">
            <div className="flex items-center gap-2 text-slate-400 overflow-x-auto">
              <span className="font-semibold text-white">Chaos Verification Loop:</span>
              <span className="px-2.5 py-1 rounded bg-blue-500/10 text-blue-300 border border-blue-500/30 whitespace-nowrap">1. Normal Execution</span>
              <span>➔</span>
              <span className="px-2.5 py-1 rounded bg-rose-500/10 text-rose-300 border border-rose-500/30 whitespace-nowrap">2. Fault Injected</span>
              <span>➔</span>
              <span className="px-2.5 py-1 rounded bg-purple-500/10 text-purple-300 border border-purple-500/30 whitespace-nowrap">3. SigNoz OTel Traces Captured</span>
              <span>➔</span>
              <span className="px-2.5 py-1 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 whitespace-nowrap">4. Copilot MCP Diagnosis</span>
            </div>
          </div>

          {/* Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {modes.map(mode => {
              const isActive = !!chaosState?.modes?.[mode.id];
              const intensity = intensities[mode.id] ?? 0.7;
              const Icon = MODE_ICONS[mode.id] || Zap;

              return (
                <div
                  key={mode.id}
                  className={`glass-card p-5 flex flex-col justify-between transition-all ${
                    isActive ? 'border-rose-500/40 bg-gradient-to-br from-rose-500/10 to-transparent shadow-lg shadow-rose-500/10' : 'hover:border-blue-500/30'
                  }`}
                >
                  <div>
                    <div className="flex justify-between items-start mb-3">
                      <div className="flex items-center gap-2.5">
                        <div className={`p-2 rounded-lg ${isActive ? 'bg-rose-500/20 text-rose-400' : 'bg-slate-800 text-slate-400'}`}>
                          <Icon size={18} />
                        </div>
                        <div>
                          <h3 className="text-sm font-bold text-white">{mode.label}</h3>
                          <span className="font-mono text-[10px] text-slate-500">{mode.id}</span>
                        </div>
                      </div>
                      <button
                        onClick={() => toggleMode(mode.id)}
                        disabled={loading}
                        className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                          isActive
                            ? 'bg-rose-500 text-white shadow-lg shadow-rose-500/30'
                            : 'bg-slate-800 text-slate-300 border border-slate-700 hover:bg-slate-700'
                        }`}
                      >
                        {isActive ? '🔥 Active' : 'Enable'}
                      </button>
                    </div>
                    <p className="text-xs text-slate-400 leading-relaxed mb-4">{mode.description}</p>
                  </div>

                  <div className="pt-3 border-t border-white/5 flex items-center gap-3">
                    <span className="text-[11px] text-slate-500 font-medium">Failure Rate:</span>
                    <input
                      type="range"
                      min="0.1"
                      max="1.0"
                      step="0.1"
                      value={intensity}
                      onChange={e => setIntensities({ ...intensities, [mode.id]: parseFloat(e.target.value) })}
                      disabled={isActive}
                      className="flex-1 h-1 bg-slate-800 rounded-lg accent-rose-500 cursor-pointer disabled:opacity-50"
                    />
                    <span className="text-xs font-mono font-bold text-rose-400">{Math.round(intensity * 100)}%</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </main>
    </div>
  );
}
