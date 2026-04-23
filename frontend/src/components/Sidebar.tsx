import {
  SlidersHorizontal,
  Search,
  Download,
  RotateCcw,
} from 'lucide-react';
import { ENTITY_LABELS, ENTITY_COLORS, getEntityLabelDisplay } from '../types';
import { getExportUrl } from '../services/api';
import { HistoryPanel } from './HistoryPanel';

interface SidebarProps {
  confidenceThreshold: number;
  onConfidenceChange: (v: number) => void;
  /** Selected entity types to show; empty = all types. */
  typeFilters: string[];
  onTypeFiltersChange: (v: string[]) => void;
  searchQuery: string;
  onSearchChange: (v: string) => void;
  hasResults: boolean;
  onReprocess: () => void;
  onReset: () => void;
  currentSessionId: string | null;
  onLoadSession: (sessionId: string) => void;
  historyRefreshKey: number;
}

export function Sidebar({
  confidenceThreshold,
  onConfidenceChange,
  typeFilters,
  onTypeFiltersChange,
  searchQuery,
  onSearchChange,
  hasResults,
  onReprocess,
  onReset,
  currentSessionId,
  onLoadSession,
  historyRefreshKey,
}: SidebarProps) {
  const toggleTypeFilter = (label: string) => {
    if (typeFilters.includes(label)) {
      onTypeFiltersChange(typeFilters.filter((l) => l !== label));
    } else {
      onTypeFiltersChange([...typeFilters, label]);
    }
  };

  return (
    <div className="p-4 space-y-6 text-sm">
      <div>
        <div className="flex items-center gap-2 text-slate-400 mb-3 font-medium uppercase text-xs tracking-wider">
          <SlidersHorizontal className="w-3.5 h-3.5" />
          Confidence
        </div>
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={confidenceThreshold}
          onChange={(e) => onConfidenceChange(parseFloat(e.target.value))}
          className="w-full accent-blue-500"
        />
        <div className="flex justify-between text-xs text-slate-500 mt-1">
          <span>0%</span>
          <span className="text-blue-400 font-medium">
            {Math.round(confidenceThreshold * 100)}%
          </span>
          <span>100%</span>
        </div>
      </div>

      <div>
        <div className="flex items-center gap-2 text-slate-400 mb-3 font-medium uppercase text-xs tracking-wider">
          <Search className="w-3.5 h-3.5" />
          Filter
        </div>
        <input
          type="text"
          placeholder="Search entity text..."
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 placeholder:text-slate-600"
        />
        <div className="flex flex-wrap gap-1.5 mt-3">
          <button
            type="button"
            onClick={() => onTypeFiltersChange([])}
            className={`px-2.5 py-1 rounded-full text-xs transition-colors ${
              typeFilters.length === 0
                ? 'bg-blue-600 text-white'
                : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
            }`}
          >
            All
          </button>
          {ENTITY_LABELS.map((label) => {
            const active = typeFilters.includes(label);
            return (
              <button
                type="button"
                key={label}
                onClick={() => toggleTypeFilter(label)}
                className={`px-2.5 py-1 rounded-full text-xs transition-colors ${
                  active
                    ? 'text-white'
                    : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                }`}
                style={
                  active ? { backgroundColor: ENTITY_COLORS[label] } : undefined
                }
              >
                {getEntityLabelDisplay(label)}
              </button>
            );
          })}
        </div>
      </div>

      <button
        onClick={onReset}
        className="flex items-center justify-center gap-2 w-full px-3 py-2 bg-amber-900/25 hover:bg-amber-900/40 border border-amber-800/40 rounded-lg transition-colors text-amber-300"
      >
        <RotateCcw className="w-4 h-4" />
        Ingest New Session
      </button>

      {hasResults && (
        <div className="space-y-2 pt-2 border-t border-slate-800">
          <div className="flex items-center gap-2 text-slate-400 mb-3 font-medium uppercase text-xs tracking-wider">
            <Download className="w-3.5 h-3.5" />
            Export
          </div>
          <a
            href={getExportUrl('json')}
            download
            className="flex items-center gap-2 w-full px-3 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors text-slate-300"
          >
            <Download className="w-4 h-4" />
            Export JSON
          </a>
          <a
            href={getExportUrl('csv')}
            download
            className="flex items-center gap-2 w-full px-3 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors text-slate-300"
          >
            <Download className="w-4 h-4" />
            Export CSV
          </a>
          <button
            onClick={onReprocess}
            className="flex items-center gap-2 w-full px-3 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors text-slate-300"
          >
            <RotateCcw className="w-4 h-4" />
            Reprocess
          </button>
        </div>
      )}

      <HistoryPanel
        currentSessionId={currentSessionId}
        onLoadSession={onLoadSession}
        refreshKey={historyRefreshKey}
      />
    </div>
  );
}
