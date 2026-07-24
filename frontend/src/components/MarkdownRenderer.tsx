'use client';
import React from 'react';

interface MarkdownRendererProps {
  content: string;
}

export default function MarkdownRenderer({ content }: MarkdownRendererProps) {
  if (!content) return null;

  // Split into lines for structured rendering
  const lines = content.split('\n');

  return (
    <div className="space-y-2 font-sans text-xs leading-relaxed text-slate-300">
      {lines.map((line, idx) => {
        const trimmed = line.trim();

        if (!trimmed) {
          return <div key={idx} className="h-1.5" />;
        }

        // Headings: ### or ## or **Header:**
        if (trimmed.startsWith('### ') || trimmed.startsWith('## ') || trimmed.startsWith('# ')) {
          const title = trimmed.replace(/^#+\s*/, '').replace(/\*\*/g, '');
          return (
            <div key={idx} className="pt-2 pb-1 border-b border-blue-500/10 mb-1">
              <h3 className="text-sm font-bold text-blue-400 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-400 inline-block" />
                {title}
              </h3>
            </div>
          );
        }

        // Execution Chain Diagram Code Block
        if (trimmed.startsWith('```')) {
          return null; // Skip code block backticks
        }
        if (trimmed.includes('↓') || trimmed.includes('→')) {
          return (
            <div key={idx} className="bg-slate-900/80 border border-blue-500/20 rounded-lg p-2 font-mono text-[11px] text-blue-300 my-1 text-center shadow-inner">
              {trimmed}
            </div>
          );
        }

        // Bullet points with status badges
        if (trimmed.startsWith('- ') || trimmed.startsWith('* ') || trimmed.startsWith('✓') || trimmed.startsWith('✗') || trimmed.startsWith('⚠')) {
          const isCheck = trimmed.includes('✓') || trimmed.includes('Completed') || trimmed.includes('High');
          const isCross = trimmed.includes('✗') || trimmed.includes('Failed') || trimmed.includes('Error');
          const isWarn = trimmed.includes('⚠') || trimmed.includes('Unverified');

          let cleanText = trimmed.replace(/^[-*]\s*/, '').replace(/\*\*/g, '');

          return (
            <div key={idx} className="flex items-start gap-2 py-0.5 pl-1">
              {isCheck && <span className="text-emerald-400 font-bold flex-shrink-0">✓</span>}
              {isCross && <span className="text-rose-400 font-bold flex-shrink-0">✗</span>}
              {isWarn && <span className="text-amber-400 font-bold flex-shrink-0">⚠</span>}
              {!isCheck && !isCross && !isWarn && <span className="text-blue-400/60 text-[10px] flex-shrink-0 mt-0.5">•</span>}
              
              <div className="flex-1">
                {parseInlineFormatting(cleanText)}
              </div>
            </div>
          );
        }

        // Standard paragraph
        return (
          <p key={idx} className="text-slate-300 py-0.5">
            {parseInlineFormatting(trimmed)}
          </p>
        );
      })}
    </div>
  );
}

// Inline formatting helper for **bold** and `code`
function parseInlineFormatting(text: string): React.ReactNode {
  // Remove raw markdown symbols like ** and ##
  const clean = text.replace(/##+/g, '').trim();

  // Split by **
  const parts = clean.split(/(\*\*[^*]+\*\*)/g);

  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      const boldText = part.slice(2, -2);
      return (
        <strong key={i} className="font-semibold text-slate-100">
          {boldText}
        </strong>
      );
    }
    
    // Check for inline `code`
    const codeParts = part.split(/(`[^`]+`)/g);
    return codeParts.map((sub, j) => {
      if (sub.startsWith('`') && sub.endsWith('`')) {
        return (
          <code key={`${i}-${j}`} className="bg-slate-900 border border-blue-500/20 text-violet-300 px-1.5 py-0.5 rounded text-[11px] font-mono">
            {sub.slice(1, -1)}
          </code>
        );
      }
      return sub;
    });
  });
}
