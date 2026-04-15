import { useState, useEffect, useCallback } from 'react';
import { History, Trash2, ChevronRight, Users, GitGraph, FileText } from 'lucide-react';
import { getSessions, deleteSession as apiDeleteSession } from '../services/api';
import type { AnalysisSession } from '../types';

interface HistoryPanelProps {
  currentSessionId: string | null;
  onLoadSession: (sessionId: string) => void;
  refreshKey: number;
}

export function HistoryPanel({
  currentSessionId,
  onLoadSession,
  refreshKey,
}: HistoryPanelProps) {
  const [sessions, setSessions] = useState<AnalysisSession[]>([]);
  const [expanded, setExpanded] = useState(true);

  const fetchSessions = useCallback(async () => {
    try {
      const data = await getSessions();
      setSessions(data);
    } catch {
      setSessions([]);
    }
  }, []);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions, refreshKey]);

  const handleDelete = useCallback(
    async (e: React.MouseEvent, sessionId: string) => {
      e.stopPropagation();
      try {
        await apiDeleteSession(sessionId);
        setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      } catch {
        /* ignore */
      }
    },
    []
  );

  if (sessions.length === 0) return null;

  const formatDate = (iso: string | null) => {
    if (!iso) return '';
    const d = new Date(iso);
    return d.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="border-t border-slate-800 pt-2">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 text-slate-400 mb-2 font-medium uppercase text-xs tracking-wider w-full hover:text-slate-300 transition-colors"
      >
        <History className="w-3.5 h-3.5" />
        History ({sessions.length})
        <ChevronRight
          className={`w-3 h-3 ml-auto transition-transform ${expanded ? 'rotate-90' : ''}`}
        />
      </button>

      {expanded && (
        <div className="space-y-1 max-h-64 overflow-y-auto">
          {sessions.map((session) => {
            const isCurrent = session.id === currentSessionId;
            return (
              <div
                key={session.id}
                onClick={() => !isCurrent && onLoadSession(session.id)}
                className={`rounded-lg px-3 py-2.5 transition-colors group ${
                  isCurrent
                    ? 'bg-blue-600/20 border border-blue-500/30 cursor-default'
                    : 'bg-slate-800/50 hover:bg-slate-800 cursor-pointer border border-transparent'
                }`}
              >
                <div className="flex items-start gap-2">
                  <div className="flex-1 min-w-0">
                    <p
                      className={`text-xs font-medium truncate ${
                        isCurrent ? 'text-blue-300' : 'text-slate-300'
                      }`}
                      title={session.name}
                    >
                      {session.name}
                    </p>
                    <div className="flex items-center gap-3 mt-1 text-slate-500">
                      <span className="flex items-center gap-1 text-[10px]">
                        <FileText className="w-2.5 h-2.5" />
                        {session.document_count}
                      </span>
                      <span className="flex items-center gap-1 text-[10px]">
                        <Users className="w-2.5 h-2.5" />
                        {session.entity_count}
                      </span>
                      <span className="flex items-center gap-1 text-[10px]">
                        <GitGraph className="w-2.5 h-2.5" />
                        {session.edge_count}
                      </span>
                    </div>
                    {session.created_at && (
                      <p className="text-[10px] text-slate-600 mt-0.5">
                        {formatDate(session.created_at)}
                      </p>
                    )}
                  </div>
                  {!isCurrent && (
                    <button
                      onClick={(e) => handleDelete(e, session.id)}
                      className="opacity-0 group-hover:opacity-100 text-slate-500 hover:text-red-400 transition-all shrink-0 mt-0.5"
                      title="Delete session"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
