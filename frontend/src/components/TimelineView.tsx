import { useMemo } from 'react';
import { Calendar } from 'lucide-react';
import type { Entity } from '../types';

interface TimelineViewProps {
  entities: Entity[];
  onSelect: (id: string) => void;
}

export function TimelineView({ entities, onSelect }: TimelineViewProps) {
  const sorted = useMemo(() => {
    return [...entities].sort((a, b) => {
      const da = tryParseDate(a.text);
      const db = tryParseDate(b.text);
      if (!da && !db) return 0;
      if (!da) return 1;
      if (!db) return -1;
      return da.getTime() - db.getTime();
    });
  }, [entities]);

  if (entities.length === 0) return null;

  return (
    <div className="bg-slate-900 rounded-xl border border-slate-800 h-full flex flex-col overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-800 shrink-0 flex items-center gap-2">
        <Calendar className="w-4 h-4 text-amber-400" />
        <h3 className="font-semibold text-sm text-slate-300">Timeline</h3>
      </div>
      <div className="flex-1 overflow-x-auto overflow-y-hidden px-4 py-3">
        <div className="flex items-center gap-3 min-w-max h-full">
          <div className="h-px bg-slate-700 absolute left-0 right-0" />
          {sorted.map((ent) => (
            <button
              key={ent.id}
              onClick={() => onSelect(ent.id)}
              className="flex flex-col items-center gap-2 px-3 py-2 bg-slate-800 hover:bg-slate-700 rounded-xl transition-colors shrink-0 border border-slate-700/50"
            >
              <div className="w-3 h-3 rounded-full bg-amber-400" />
              <span className="text-xs font-medium text-slate-200 whitespace-nowrap">
                {ent.text}
              </span>
              <span className="text-xs text-slate-500">
                {ent.occurrences} mention{ent.occurrences > 1 ? 's' : ''}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function tryParseDate(text: string): Date | null {
  const d = new Date(text);
  return isNaN(d.getTime()) ? null : d;
}
