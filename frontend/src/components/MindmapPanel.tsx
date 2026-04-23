import { useMemo, useState } from 'react';
import { Network, ChevronRight } from 'lucide-react';
import type { Entity } from '../types';
import { ENTITY_COLORS, getEntityLabelDisplay } from '../types';

interface MindmapPanelProps {
  entities: Entity[];
  onSelectEntity: (entityId: string) => void;
}

export function MindmapPanel({ entities, onSelectEntity }: MindmapPanelProps) {
  if (entities.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 text-slate-500">
        <Network className="w-12 h-12" />
        <p className="text-sm text-center px-4 max-w-md leading-relaxed">
          No entities in this session for mindmap view. Upload and process documents, or relax sidebar filters.
        </p>
      </div>
    );
  }

  const grouped = useMemo(
    () =>
      entities.reduce<Record<string, Entity[]>>((acc, ent) => {
        if (!acc[ent.label]) acc[ent.label] = [];
        acc[ent.label].push(ent);
        return acc;
      }, {}),
    [entities]
  );

  const labelEntries = useMemo(
    () => Object.entries(grouped).sort((a, b) => b[1].length - a[1].length),
    [grouped]
  );
  const [expandedLabels, setExpandedLabels] = useState<Record<string, boolean>>({});

  return (
    <div className="bg-slate-900 rounded-xl border border-slate-800 h-full flex flex-col overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-800 shrink-0 flex items-center gap-2">
        <Network className="w-4 h-4 text-indigo-400" />
        <h3 className="font-semibold text-sm text-slate-300">
          Session Mindmap ({entities.length} values)
        </h3>
      </div>
      <div className="flex-1 overflow-auto p-5">
        <div className="min-w-[900px] space-y-6">
          <div className="flex items-center gap-6">
            <div className="px-4 py-2 rounded-lg bg-blue-500/20 border border-blue-400/30 text-blue-200 font-medium text-sm">
              Current Session
            </div>
            <div className="h-px flex-1 bg-slate-800" />
          </div>

          {labelEntries.map(([label, values]) => (
            <section key={label} className="grid grid-cols-[280px_1fr] gap-8 items-start">
              <div className="relative">
                <div className="absolute right-[-32px] top-1/2 -translate-y-1/2 w-8 h-px bg-slate-700" />
                <button
                  type="button"
                  onClick={() =>
                    setExpandedLabels((prev) => ({ ...prev, [label]: !prev[label] }))
                  }
                  className="w-full flex items-center gap-2 px-3 py-2 rounded-lg border text-sm font-medium shadow-sm text-left"
                  style={{
                    borderColor: `${ENTITY_COLORS[label] || '#64748b'}66`,
                    backgroundColor: `${ENTITY_COLORS[label] || '#64748b'}1f`,
                    color: ENTITY_COLORS[label] || '#64748b',
                  }}
                >
                  <ChevronRight
                    className={`w-4 h-4 transition-transform ${expandedLabels[label] ? 'rotate-90' : ''}`}
                  />
                  {getEntityLabelDisplay(label)} ({values.length})
                </button>
              </div>

              <div className="space-y-2">
                {!expandedLabels[label] ? (
                  <div className="pl-8 text-xs text-slate-500 pt-1">
                    Click label to expand values
                  </div>
                ) : (
                  <>
                    {values
                      .sort((a, b) => b.occurrences - a.occurrences)
                      .slice(0, 40)
                      .map((ent) => (
                        <div key={ent.id} className="relative pl-8">
                          <div className="absolute left-0 top-1/2 -translate-y-1/2 w-6 h-px bg-slate-700" />
                          <button
                            type="button"
                            onClick={() => onSelectEntity(ent.id)}
                            className="w-full max-w-2xl text-left px-3 py-2 rounded-lg bg-emerald-500/15 border border-emerald-400/30 hover:bg-emerald-500/25 transition-colors"
                          >
                            <div className="text-sm text-emerald-100 truncate">{ent.text}</div>
                            <div className="text-[11px] text-emerald-200/75 mt-0.5">
                              score {Math.round(ent.score * 100)}% · occurrences {ent.occurrences}
                            </div>
                          </button>
                        </div>
                      ))}
                    {values.length > 40 && (
                      <div className="pl-8 text-xs text-slate-500">
                        +{values.length - 40} more values (refine filters to narrow view)
                      </div>
                    )}
                  </>
                )}
              </div>
            </section>
          ))}
        </div>
      </div>
    </div>
  );
}
