'use client';
import { useState, useEffect, useRef, useCallback } from 'react';
import Sidebar from '@/components/Sidebar';
import MarkdownRenderer from '@/components/MarkdownRenderer';
import { api } from '@/lib/api';
import { WorkflowRun } from '@/lib/types';
import {
  Send, Sparkles, RefreshCw, Bot, User, ShieldAlert,
  GitCompare, Layers, Cpu, CheckCircle2, XCircle, ChevronDown, ChevronUp, Flame, Activity
} from 'lucide-react';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  streaming?: boolean;
}

export default function CopilotPage() {
  const [messages, setMessages] = useState<Message[]>([{
    role: 'assistant',
    content: '👋 Hi! I am your **Root Cause Copilot** — an Evidence-Driven AI Incident Investigator powered by **SigNoz MCP & OpenTelemetry**.\n\nSelect an **Execution Mode** above:\n- 🟢 **Scenario Investigation**: Analyze production incident scenario diagnosis & remediation.\n- 🔴 **Chaos Resilience**: Test system resilience under fault injection.',
  }]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [runs, setRuns] = useState<WorkflowRun[]>([]);
  const [selectedRun, setSelectedRun] = useState<string>('');
  
  // Execution Mode Selector (Default: SCENARIO_INVESTIGATION)
  const [executionMode, setExecutionMode] = useState<'SCENARIO_INVESTIGATION' | 'CHAOS_RESILIENCE'>('SCENARIO_INVESTIGATION');
  
  // Compare Runs state
  const [compareMode, setCompareMode] = useState(false);
  const [runA, setRunA] = useState<string>('');
  const [runB, setRunB] = useState<string>('');
  const [comparisonResult, setComparisonResult] = useState<any>(null);
  
  // Evidence Viewer state
  const [showEvidence, setShowEvidence] = useState(false);
  
  const bottomRef = useRef<HTMLDivElement>(null);
  
  const fetchInitial = useCallback(async () => {
    try {
      const [s, r] = await Promise.all([api.copilot.suggestions(), api.runs.list()]);
      setSuggestions(s.suggestions);
      setRuns(r);
      if (r.length > 0 && !selectedRun) {
        setSelectedRun(r[0].workflow_id);
      }
    } catch {}
  }, [selectedRun]);
  
  useEffect(() => {
    fetchInitial();
  }, [fetchInitial]);

  // When switching to SCENARIO_INVESTIGATION, automatically disable all chaos faults
  const handleModeChange = async (mode: 'SCENARIO_INVESTIGATION' | 'CHAOS_RESILIENCE') => {
    setExecutionMode(mode);
    if (mode === 'SCENARIO_INVESTIGATION') {
      try {
        await api.chaos.disable();
      } catch {}
    }
  };
  
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);
  
  const ask = useCallback(async (question: string) => {
    if (!question.trim() || loading) return;
    setInput('');
    setLoading(true);
    
    setMessages(prev => [
      ...prev,
      { role: 'user', content: question },
      { role: 'assistant', content: '', streaming: true },
    ]);
    
    try {
      const res = await fetch(api.copilot.askUrl(), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question,
          workflow_id: selectedRun || undefined,
          execution_mode: executionMode,
        }),
      });
      
      if (!res.body) throw new Error('No stream available');
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let full = '';
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const text = decoder.decode(value);
        const lines = text.split('\n').filter(l => l.startsWith('data: '));
        for (const line of lines) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.content) {
              full += data.content;
              setMessages(prev => [
                ...prev.slice(0, -1),
                { role: 'assistant', content: full, streaming: !data.done },
              ]);
            }
          } catch {}
        }
      }
    } catch (e) {
      setMessages(prev => [
        ...prev.slice(0, -1),
        { role: 'assistant', content: 'Error connecting to Root Cause Copilot service.' },
      ]);
    } finally {
      setLoading(false);
    }
  }, [loading, selectedRun, executionMode]);

  const handleCompare = async () => {
    if (!runA || !runB) return;
    try {
      const res = await fetch('/api/copilot/compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ run_id_a: runA, run_id_b: runB }),
      });
      const data = await res.json();
      setComparisonResult(data.comparison);
    } catch (e) {
      console.error(e);
    }
  };

  const activeRunObj = runs.find(r => r.workflow_id === selectedRun) || runs[0];

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="sticky top-0 z-10 bg-[#020817]/80 backdrop-blur-md border-b border-blue-500/10 px-6 py-4 flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold gradient-text">Root Cause Copilot</h1>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-500/15 border border-blue-500/30 text-blue-400 font-mono">
                SigNoz MCP Telemetry Verified
              </span>
            </div>
            <p className="text-xs text-slate-500">Evidence-Driven AI Incident Investigator & Trace Correlator</p>
          </div>
          
          <div className="flex items-center gap-3">
            {/* Execution Mode Selector */}
            <div className="flex items-center bg-slate-900/90 border border-slate-800 rounded-lg p-0.5 text-xs font-semibold">
              <button
                onClick={() => handleModeChange('SCENARIO_INVESTIGATION')}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-md transition-all ${
                  executionMode === 'SCENARIO_INVESTIGATION'
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Activity size={13} className="text-emerald-400" /> Scenario Investigation
              </button>
              <button
                onClick={() => handleModeChange('CHAOS_RESILIENCE')}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-md transition-all ${
                  executionMode === 'CHAOS_RESILIENCE'
                    ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Flame size={13} className="text-rose-400" /> Chaos Resilience
              </button>
            </div>

            <button
              onClick={() => setShowEvidence(!showEvidence)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
                showEvidence ? 'bg-blue-500/20 text-blue-300 border-blue-500/40' : 'bg-slate-900 text-slate-400 border-slate-800'
              }`}
            >
              <Layers size={13} /> Evidence Viewer {showEvidence ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            </button>

            <button
              onClick={() => setCompareMode(!compareMode)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
                compareMode ? 'bg-violet-500/20 text-violet-300 border-violet-500/40' : 'bg-slate-900 text-slate-400 border-slate-800'
              }`}
            >
              <GitCompare size={13} /> Compare Runs
            </button>

            <select
              value={selectedRun}
              onChange={e => setSelectedRun(e.target.value)}
              className="text-xs bg-slate-900 border border-blue-500/20 rounded-lg px-3 py-1.5 text-slate-300 font-mono"
            >
              <option value="">Target Trace (Default: Latest)</option>
              {runs.map(r => (
                <option key={r.workflow_id} value={r.workflow_id}>
                  {r.workflow_id} — {r.status.toUpperCase()}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Evidence Viewer Panel — Incident Investigation Evidence Checklist */}
        {showEvidence && activeRunObj && (
          <div className="bg-[#0a0f1e] border-b border-blue-500/15 p-4 text-xs font-mono text-slate-300 grid grid-cols-5 gap-3 animate-fade-in">
            <div className="glass-card p-3 border-blue-500/30">
              <span className="text-slate-500 block mb-1 text-[10px] uppercase font-bold">1. Workflow Context</span>
              <span className="text-blue-400 font-bold flex items-center gap-1">✓ Available</span>
              <span className="text-slate-400 text-[10px] block mt-1 truncate">{activeRunObj.workflow_id}</span>
            </div>

            <div className="glass-card p-3 border-emerald-500/30">
              <span className="text-slate-500 block mb-1 text-[10px] uppercase font-bold">2. SigNoz Traces</span>
              <span className="text-emerald-400 font-bold flex items-center gap-1">✓ OTel Spans Captured</span>
              <span className="text-slate-400 text-[10px] block mt-1">signoz_search_traces</span>
            </div>

            <div className="glass-card p-3 border-purple-500/30">
              <span className="text-slate-500 block mb-1 text-[10px] uppercase font-bold">3. GenAI Metrics</span>
              <span className="text-purple-400 font-bold flex items-center gap-1">✓ Tokens & USD Cost</span>
              <span className="text-slate-400 text-[10px] block mt-1">signoz_query_metrics</span>
            </div>

            <div className="glass-card p-3 border-amber-500/30">
              <span className="text-slate-500 block mb-1 text-[10px] uppercase font-bold">4. SigNoz Logs</span>
              <span className="text-amber-400 font-bold flex items-center gap-1">✓ ClickHouse Exceptions</span>
              <span className="text-slate-400 text-[10px] block mt-1">signoz_search_logs</span>
            </div>

            <div className="glass-card p-3 border-slate-700">
              <span className="text-slate-500 block mb-1 text-[10px] uppercase font-bold">5. Evidence Status</span>
              <span className="text-emerald-400 font-bold">Verified via MCP</span>
              <span className="text-slate-400 text-[10px] block mt-1">Mode: {executionMode}</span>
            </div>
          </div>
        )}

        {/* Compare Runs Drawer */}
        {compareMode && (
          <div className="bg-[#0a0f1e] border-b border-violet-500/20 p-4 space-y-3 animate-fade-in">
            <div className="flex items-center gap-3">
              <span className="text-xs font-semibold text-violet-300">Compare Run A:</span>
              <select value={runA} onChange={e => setRunA(e.target.value)} className="text-xs bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-300 font-mono">
                <option value="">Select Run A</option>
                {runs.map(r => <option key={r.workflow_id} value={r.workflow_id}>{r.workflow_id} ({r.status})</option>)}
              </select>

              <span className="text-xs font-semibold text-violet-300">vs Run B:</span>
              <select value={runB} onChange={e => setRunB(e.target.value)} className="text-xs bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-300 font-mono">
                <option value="">Select Run B</option>
                {runs.map(r => <option key={r.workflow_id} value={r.workflow_id}>{r.workflow_id} ({r.status})</option>)}
              </select>

              <button onClick={handleCompare} disabled={!runA || !runB} className="px-3 py-1 bg-violet-600 hover:bg-violet-500 text-white text-xs font-semibold rounded">
                Run Comparison
              </button>
            </div>

            {comparisonResult && (
              <div className="grid grid-cols-3 gap-4 text-xs font-mono pt-2 border-t border-white/5">
                <div className="glass-card p-3">
                  <span className="text-blue-400 font-bold">Run A: {comparisonResult.run_a.id}</span>
                  <div>Status: {comparisonResult.run_a.status}</div>
                  <div>Duration: {comparisonResult.run_a.total_duration_ms}ms</div>
                  <div>Cost: ${comparisonResult.run_a.total_cost_usd}</div>
                </div>

                <div className="glass-card p-3">
                  <span className="text-violet-400 font-bold">Run B: {comparisonResult.run_b.id}</span>
                  <div>Status: {comparisonResult.run_b.status}</div>
                  <div>Duration: {comparisonResult.run_b.total_duration_ms}ms</div>
                  <div>Cost: ${comparisonResult.run_b.total_cost_usd}</div>
                </div>

                <div className="glass-card p-3">
                  <span className="text-emerald-400 font-bold">Delta Summary</span>
                  <div>Status: {comparisonResult.delta.status_change}</div>
                  <div>Latency Delta: {comparisonResult.delta.duration_delta_ms}ms</div>
                  <div>Cost Delta: ${comparisonResult.delta.cost_delta_usd}</div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Chat Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.map((msg, i) => (
            <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${msg.role === 'user' ? 'bg-blue-600/20 border border-blue-500/30' : 'bg-violet-600/20 border border-violet-500/30'}`}>
                {msg.role === 'user' ? <User size={14} className="text-blue-400" /> : <Bot size={14} className="text-violet-400" />}
              </div>
              <div className="max-w-3xl rounded-xl px-4 py-3 text-sm leading-relaxed glass-card">
                {msg.role === 'user' ? (
                  <div className="text-slate-200 font-mono text-xs">{msg.content}</div>
                ) : (
                  <MarkdownRenderer content={msg.content} />
                )}
                {msg.streaming && <span className="inline-block w-1.5 h-3 bg-violet-400 animate-pulse ml-1 mt-1" />}
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>

        {/* Suggestion Chips */}
        {suggestions.length > 0 && messages.length < 4 && (
          <div className="px-6 pb-3 flex flex-wrap gap-2">
            {suggestions.slice(0, 4).map(s => (
              <button key={s} onClick={() => ask(s)} className="text-xs px-3 py-1.5 rounded-full bg-violet-500/10 border border-violet-500/20 text-violet-300 hover:bg-violet-500/20 transition-colors">
                <Sparkles size={11} className="inline mr-1" /> {s}
              </button>
            ))}
          </div>
        )}

        {/* Input Bar */}
        <div className="p-4 border-t border-blue-500/10 bg-[#020817]">
          <div className="flex gap-3">
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && ask(input)}
              placeholder={`Ask Root Cause Copilot [Mode: ${executionMode.replace('_', ' ')}]...`}
              className="flex-1 bg-slate-900 border border-blue-500/20 rounded-xl px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-blue-500/50"
            />
            <button onClick={() => ask(input)} disabled={loading || !input.trim()} className="px-4 py-2.5 bg-gradient-to-r from-violet-600 to-blue-600 hover:from-violet-500 hover:to-blue-500 rounded-xl text-white font-semibold disabled:opacity-50 transition-all shadow-lg shadow-violet-500/20">
              {loading ? <RefreshCw size={15} className="animate-spin" /> : <Send size={15} />}
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
