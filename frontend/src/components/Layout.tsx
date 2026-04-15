import type { ReactNode } from 'react';
import { Shield } from 'lucide-react';

interface LayoutProps {
  children: ReactNode;
  sidebar: ReactNode;
  evidence: ReactNode | null;
}

export function Layout({ children, sidebar, evidence }: LayoutProps) {
  return (
    <div className="h-screen flex flex-col bg-slate-950 text-slate-100 overflow-hidden">
      <header className="flex items-center gap-3 px-6 py-3 bg-slate-900 border-b border-slate-800 shrink-0">
        <Shield className="w-7 h-7 text-blue-400" />
        <h1 className="text-xl font-bold tracking-tight">
          EXTRACTA <span className="text-slate-400 font-normal text-sm ml-1">OSINT Intelligence Platform</span>
        </h1>
      </header>
      <div className="flex flex-1 min-h-0 overflow-hidden">
        <aside className="w-64 bg-slate-900 border-r border-slate-800 overflow-y-auto shrink-0">
          {sidebar}
        </aside>
        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
        {evidence && (
          <aside className="w-96 bg-slate-900 border-l border-slate-800 overflow-y-auto shrink-0">
            {evidence}
          </aside>
        )}
      </div>
    </div>
  );
}
