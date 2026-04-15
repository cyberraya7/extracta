import { useState, useEffect, useCallback, useRef } from 'react';
import { History, Trash2, ChevronRight, Users, GitGraph, FileText, Pencil, Check, X } from 'lucide-react';
import { getSessions, deleteSession as apiDeleteSession, renameSession as apiRenameSession } from '../services/api';
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
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');
  const editInputRef = useRef<HTMLInputElement>(null);

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

  useEffect(() => {
    if (editingId && editInputRef.current) {
      editInputRef.current.focus();
      editInputRef.current.select();
    }
  }, [editingId]);

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

  const startRename = useCallback((e: React.MouseEvent, session: AnalysisSession) => {
    e.stopPropagation();
    setEditingId(session.id);
    setEditName(session.name);
  }, []);

  const confirmRename = useCallback(async () => {
    if (!editingId || !editName.trim()) {
      setEditingId(null);
      return;
    }
    try {
      await apiRenameSession(editingId, editName.trim());
      setSessions((prev) =>
        prev.map((s) => (s.id === editingId ? { ...s, name: editName.trim() } : s))
      );
    } catch {
      /* ignore */
    }
    setEditingId(null);
  }, [editingId, editName]);

  const cancelRename = useCallback(() => {
    setEditingId(null);
  }, []);

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
            const isEditing = editingId === session.id;

            return (
              <div
                key={session.id}
                onClick={() => !isCurrent && !isEditing && onLoadSession(session.id)}
                className={`rounded-lg px-3 py-2.5 transition-colors group ${
                  isCurrent
                    ? 'bg-blue-600/20 border border-blue-500/30 cursor-default'
                    : 'bg-slate-800/50 hover:bg-slate-800 cursor-pointer border border-transparent'
                }`}
              >
                <div className="flex items-start gap-2">
                  <div className="flex-1 min-w-0">
                    {isEditing ? (
                      <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                        <input
                          ref={editInputRef}
                          type="text"
                          value={editName}
                          onChange={(e) => setEditName(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') confirmRename();
                            if (e.key === 'Escape') cancelRename();
                          }}
                          className="flex-1 bg-slate-700 border border-slate-600 rounded px-1.5 py-0.5 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500 min-w-0"
                        />
                        <button
                          onClick={confirmRename}
                          className="text-green-400 hover:text-green-300 shrink-0"
                        >
                          <Check className="w-3 h-3" />
                        </button>
                        <button
                          onClick={cancelRename}
                          className="text-slate-500 hover:text-slate-300 shrink-0"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </div>
                    ) : (
                      <p
                        className={`text-xs font-medium truncate ${
                          isCurrent ? 'text-blue-300' : 'text-slate-300'
                        }`}
                        title={session.name}
                      >
                        {session.name}
                      </p>
                    )}
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
                  {!isEditing && (
                    <div className="flex items-center gap-1 shrink-0 mt-0.5">
                      <button
                        onClick={(e) => startRename(e, session)}
                        className="opacity-0 group-hover:opacity-100 text-slate-500 hover:text-blue-400 transition-all"
                        title="Rename session"
                      >
                        <Pencil className="w-3 h-3" />
                      </button>
                      {!isCurrent && (
                        <button
                          onClick={(e) => handleDelete(e, session.id)}
                          className="opacity-0 group-hover:opacity-100 text-slate-500 hover:text-red-400 transition-all"
                          title="Delete session"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      )}
                    </div>
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
