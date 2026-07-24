import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'AgentOps Center — AI Operations Command Center',
  description: 'The AI Operations Center for Multi-Agent Systems. Observe, debug, and improve AI agents with OpenTelemetry and SigNoz.',
  keywords: ['AI agents', 'observability', 'OpenTelemetry', 'SigNoz', 'LangGraph', 'MLOps'],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />
      </head>
      <body className="bg-[#020817] text-slate-100 antialiased" suppressHydrationWarning>
        <div className="grid-bg min-h-screen">
          {children}
        </div>
      </body>
    </html>
  );
}
