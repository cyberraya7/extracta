import { useState, useMemo } from 'react';
import { ChevronUp, ChevronDown } from 'lucide-react';
import type { Entity } from '../types';
import { ENTITY_COLORS } from '../types';

interface EntityTableProps {
  entities: Entity[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

type SortKey = 'text' | 'label' | 'score' | 'occurrences';
type SortDir = 'asc' | 'desc';

export function EntityTable({ entities, selectedId, onSelect }: EntityTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>('score');
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  const sorted = useMemo(() => {
    return [...entities].sort((a, b) => {
      let cmp: number;
      if (sortKey === 'text' || sortKey === 'label') {
        cmp = a[sortKey].localeCompare(b[sortKey]);
      } else {
        cmp = a[sortKey] - b[sortKey];
      }
      return sortDir === 'asc' ? cmp : -cmp;
    });
  }, [entities, sortKey, sortDir]);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const SortIcon = ({ col }: { col: SortKey }) => {
    if (sortKey !== col) return null;
    return sortDir === 'asc' ? (
      <ChevronUp className="w-3.5 h-3.5 inline" />
    ) : (
      <ChevronDown className="w-3.5 h-3.5 inline" />
    );
  };

  return (
    <div className="bg-slate-900 rounded-xl border border-slate-800 h-full flex flex-col overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-800 shrink-0">
        <h3 className="font-semibold text-sm text-slate-300">
          Entities ({entities.length})
        </h3>
      </div>
      <div className="overflow-auto flex-1">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-slate-900 z-10">
            <tr className="text-left text-xs text-slate-500 uppercase tracking-wider">
              {(['text', 'label', 'score', 'occurrences'] as SortKey[]).map(
                (col) => (
                  <th
                    key={col}
                    className="px-4 py-2.5 cursor-pointer hover:text-slate-300 transition-colors select-none"
                    onClick={() => toggleSort(col)}
                  >
                    {col === 'occurrences' ? 'Count' : col}
                    <SortIcon col={col} />
                  </th>
                )
              )}
            </tr>
          </thead>
          <tbody>
            {sorted.map((ent) => (
              <tr
                key={ent.id}
                onClick={() => onSelect(ent.id)}
                className={`cursor-pointer border-t border-slate-800/50 transition-colors ${
                  selectedId === ent.id
                    ? 'bg-blue-900/30'
                    : 'hover:bg-slate-800/50'
                }`}
              >
                <td className="px-4 py-2.5 font-medium">{ent.text}</td>
                <td className="px-4 py-2.5">
                  <span
                    className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium capitalize"
                    style={{
                      backgroundColor: `${ENTITY_COLORS[ent.label]}20`,
                      color: ENTITY_COLORS[ent.label],
                    }}
                  >
                    <span
                      className="w-1.5 h-1.5 rounded-full"
                      style={{ backgroundColor: ENTITY_COLORS[ent.label] }}
                    />
                    {ent.label}
                  </span>
                </td>
                <td className="px-4 py-2.5 tabular-nums">
                  {Math.round(ent.score * 100)}%
                </td>
                <td className="px-4 py-2.5 tabular-nums">{ent.occurrences}</td>
              </tr>
            ))}
            {sorted.length === 0 && (
              <tr>
                <td
                  colSpan={4}
                  className="px-4 py-8 text-center text-slate-500"
                >
                  No entities match the current filters
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
