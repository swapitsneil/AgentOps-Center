'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard, GitBranch, DollarSign, MessageSquare,
  Zap, Activity, Settings, ChevronRight
} from 'lucide-react';
import { clsx } from 'clsx';

const NAV = [
  { href: '/', icon: LayoutDashboard, label: 'Command Center', sub: 'System overview' },
  { href: '/timeline', icon: GitBranch, label: 'Agent Timeline', sub: 'Execution replay' },
  { href: '/costs', icon: DollarSign, label: 'Cost Intelligence', sub: 'Token & cost analytics' },
  { href: '/copilot', icon: MessageSquare, label: 'Root Cause Copilot', sub: 'AI-powered RCA' },
  { href: '/chaos', icon: Zap, label: 'Chaos Engineering', sub: 'Failure injection' },
];

export default function Sidebar() {
  const pathname = usePathname();
  
  return (
    <aside className="w-64 bg-[#0a0f1e] border-r border-blue-500/10 flex flex-col h-screen sticky top-0">
      {/* Logo */}
      <div className="p-5 border-b border-blue-500/10">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center">
            <Activity size={16} className="text-white" />
          </div>
          <div>
            <div className="text-sm font-bold text-white">AgentOps Center</div>
            <div className="text-xs text-blue-400/60">AI Operations Platform</div>
          </div>
        </div>
      </div>
      
      {/* Nav */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {NAV.map(({ href, icon: Icon, label, sub }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={clsx(
                'group flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200',
                active
                  ? 'bg-blue-500/15 border border-blue-500/30 text-blue-300'
                  : 'text-slate-400 hover:bg-white/5 hover:text-slate-200 border border-transparent'
              )}
            >
              <Icon size={17} className={active ? 'text-blue-400' : 'text-slate-500 group-hover:text-slate-300'} />
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium truncate">{label}</div>
                <div className="text-xs text-slate-500 truncate">{sub}</div>
              </div>
              {active && <ChevronRight size={14} className="text-blue-400/60" />}
            </Link>
          );
        })}
      </nav>
      
      {/* Footer */}
      <div className="p-4 border-t border-blue-500/10">
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span>SigNoz Connected</span>
        </div>
        <div className="mt-1 text-xs text-slate-600">OTel → SigNoz → Insights</div>
      </div>
    </aside>
  );
}
